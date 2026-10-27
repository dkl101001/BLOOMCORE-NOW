# SPDX-License-Identifier: Apache-2.0
"""Owner-granted collaboration peer. Grants live only in memory and bind exact drafts."""
import time
from nacl.signing import SigningKey
from .protocol import *
from .owner import LocalState, seal, decrypt, put, get


class Peer(LocalState):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.state:
            self.state={'identity':new_identity(),'invitation':None,'consent':[],'queue':[],'events':{},'pending':{},
                        'cursor':0,'sequence':0,'previous':None,'epoch':0,'last_clock':0,'quarantined':0}
            self.save()
        self.status='Private / paused'
        self._replies={};self._active=set();self._grants={};self._batches={}
        self._drain_pending()
    def public_request(self):return public_identity(self.state['identity'])
    def preview_invite(self,packet):
        doc=decrypt(self.state['identity']['enc_secret'],packet);body=doc['body']
        verify(doc,body['authority'],'invitation')
        exact(body,'schema room authority owner_encryption owner_route endpoint token epoch expires member mailbox')
        if body['schema']!='invitation/1' or body['member']!=self.public_request() or body['expires']<=int(time.time()):raise Rejected('invitation binding/expiry')
        return {'room':body['room'],'authority_fingerprint':hashlib.sha256(un64(body['authority'])).hexdigest(),
                'endpoint':body['endpoint'],'alias':body['member']['alias']}
    def accept_invite(self,packet,*,fingerprint_confirmed=False):
        self.preview_invite(packet)
        if fingerprint_confirmed is not True:raise Rejected('verify invitation delivery and fingerprint first')
        if self.state['invitation']:raise Rejected('use a separate room workspace')
        self.state['invitation']=decrypt(self.state['identity']['enc_secret'],packet)['body'];self.save()
    def consent(self,categories,*,confirmed=False):
        if confirmed is not True or not categories or not set(categories)<={'question','comment','action','summary'}:raise Rejected('explicit room and scope consent required')
        if not self.state['invitation']:raise Rejected('room invitation required')
        self.state['consent']=sorted(set(categories));self.save()
    def pause(self):self.state['consent']=[];self.save()
    def queue(self,card,object_id=None,parents=None):
        card=projection(card)
        if card['category'] not in self.state['consent']:raise Rejected('not consented')
        if len(self.state['queue'])>=64:raise Rejected('outbox capacity')
        object_id=object_id or uid();ident(object_id);parents=list(parents or [])
        if len(parents)>8 or len(set(parents))!=len(parents):raise Rejected('parent limit')
        if any(p not in self.state['events'] or self.state['events'][p]['object_id']!=object_id for p in parents):raise Rejected('unknown/cross-object parent')
        self.state['queue'].append({'object_id':object_id,'payload':card,'parents':parents,'draft':None});self.save();return object_id
    def heads(self,object_id):
        events=self.state['events'];parents={p for e in events.values() for p in e['parent_event_ids']}
        return [e for k,e in events.items() if e['object_id']==object_id and k not in parents]
    def poll(self,transport,limit=16):
        inv=self.state['invitation']
        for _ in range(min(limit,64)):
            row=get(transport,inv['room'],inv['mailbox'],self.state['cursor'])
            if row['packet'] is None:return
            self.state['cursor']=row['cursor']
            try:
                doc=decrypt(self.state['identity']['enc_secret'],row['packet']);exact(doc,'kind value')
                if doc['kind']=='owner-response':
                    body=verify(doc['value'],inv['authority'],'owner-response');exact(body,'schema room nonce result')
                    if body['schema']!='owner-response/1' or body['room']!=inv['room']:raise Rejected('response binding')
                    if body['nonce'] in self._active:self._replies[body['nonce']]=doc['value']
                elif doc['kind']=='event':self.receive(doc['value'])
                else:raise Rejected('packet type')
            except Exception:self.state['quarantined']+=1
            self.save()
    def ask(self,transport,action,data,*,owner_pump=None,deadline=30):
        now_mono=time.monotonic()
        self._grants={k:v for k,v in self._grants.items() if 0<=now_mono-v[1]<30}
        if len(self._grants)>=64:raise Rejected('live grant budget')
        inv=self.state['invitation'];identity=self.state['identity'];nonce=uid();started=time.monotonic();wall=int(time.time())
        if wall<self.state['last_clock']-5:raise Rejected('clock rollback; sync suspended')
        self.state['last_clock']=max(wall,self.state['last_clock']);self.save()
        body={'schema':'owner-request/1','room':inv['room'],'author':identity['sign_public'],'nonce':nonce,'issued':wall,'action':action,'data':data}
        request=signed(body,SigningKey(un64(identity['sign_secret'])),'owner-request')
        self._active.add(nonce)
        try:
            put(transport,inv['room'],inv['owner_route'],seal(inv['owner_encryption'],request))
            while time.monotonic()-started<min(deadline,30):
                if owner_pump:owner_pump()
                self.poll(transport)
                response=self._replies.pop(nonce,None)
                if response:
                    if time.monotonic()-started>=min(deadline,30):break
                    if action=='grant':
                        self._grants[nonce]=(canonical(body),started,canonical(response))
                    return response,started,body
                time.sleep(.02)
            self.status='Room owner offline: saved locally, sync queued'
            raise ConnectionError(self.status)
        finally:self._active.discard(nonce);self._replies.pop(nonce,None)
    def join(self,transport,**kwargs):
        result,_,_=self.ask(transport,'join',{'token':self.state['invitation']['token']},**kwargs)
        value=result['body']['result']
        if value.get('joined') is not True:raise Rejected('join refused')
        self.state['epoch']=value['epoch'];self.save()
    def validate_grant(self,response,request,draft,started,*,in_batch=False):
        registry=self._batches if in_batch else self._grants
        binding=registry.get(request['nonce'])
        if binding!=(canonical(request),started,canonical(response)):
            raise Rejected('grant not live in this session or already consumed')
        inv=self.state['invitation'];body=verify(response,inv['authority'],'owner-response')
        exact(body,'schema room nonce result');grant=body['result']
        exact(grant,'schema room sender challenge event_digest expected_epoch epoch roster issued max_validity_seconds')
        if body['schema']!='owner-response/1' or body['room']!=inv['room'] or body['nonce']!=request['nonce']:raise Rejected('grant response binding')
        if grant['schema']!='grant/1' or grant['room']!=inv['room'] or grant['sender']!=self.state['identity']['sign_public'] or grant['challenge']!=request['nonce'] or grant['event_digest']!=digest(draft) or grant['expected_epoch']!=request['data']['expected_epoch']:raise Rejected('grant exact binding')
        if type(grant['epoch'])is not int or grant['epoch']<self.state['epoch'] or type(grant['max_validity_seconds'])is not int or not 0<grant['max_validity_seconds']<=30:raise Rejected('grant epoch/lifetime')
        if time.monotonic()-started>=grant['max_validity_seconds'] or int(time.time())<self.state['last_clock']-5:raise Rejected('grant expired/clock rollback')
        if not isinstance(grant['roster'],list) or not 1<=len(grant['roster'])<=MAX_MEMBERS:raise Rejected('roster size')
        keys=set()
        for m in grant['roster']:
            exact(m,'sign_public enc_public alias mailbox');member({k:m[k] for k in ('sign_public','enc_public','alias')});exact(m['mailbox'],'route write')
            ident(m['mailbox']['route']);ident(m['mailbox']['write'])
            if m['sign_public'] in keys:raise Rejected('duplicate member')
            keys.add(m['sign_public'])
        if self.state['identity']['sign_public'] not in keys:raise Rejected('removed')
        return grant
    def begin_batch(self,response,request,draft,started):
        grant=self.validate_grant(response,request,draft,started)
        nonce=request['nonce'];self._batches[nonce]=self._grants.pop(nonce)
        return grant
    def _validate_outbox(self):
        if not isinstance(self.state['queue'],list) or len(self.state['queue'])>64:raise Rejected('outbox capacity/type')
        for item in self.state['queue']:
            exact(item,'object_id payload parents draft');projection(item['payload']);ident(item['object_id'])
            if not isinstance(item['parents'],list) or len(item['parents'])>8 or len(set(item['parents']))!=len(item['parents']):raise Rejected('outbox parents')
            for parent in item['parents']:
                ident(parent)
                if parent not in self.state['events'] or self.state['events'][parent]['object_id']!=item['object_id']:raise Rejected('outbox parent binding')
            if item['payload']['category'] not in self.state['consent']:raise Rejected('scope removed')
            if item['draft'] is None:continue
            draft=item['draft']
            exact(draft,'schema_version room_id event_id author_room_key author_sequence previous_author_event parent_event_ids object_id operation payload')
            projection(draft['payload']);ident(draft['event_id'])
            if draft['previous_author_event'] is not None:ident(draft['previous_author_event'])
            if type(draft['author_sequence']) is not int:raise Rejected('outbox sequence')
            if (draft['payload']!=item['payload'] or draft['object_id']!=item['object_id'] or draft['parent_event_ids']!=item['parents']
                or draft['schema_version']!='draft/1' or draft['room_id']!=self.state['invitation']['room']
                or draft['author_room_key']!=self.state['identity']['sign_public'] or draft['operation']!='revision'
                or draft['author_sequence']!=self.state['sequence']+1 or draft['previous_author_event']!=self.state['previous']):
                raise Rejected('outbox draft binding')
    def sync(self,transport,*,owner_pump=None,deadline=30):
        if not self.state['consent']:self.status='Paused — explicit room sharing consent required';return
        self._validate_outbox()
        self.poll(transport,64)
        for item in list(self.state['queue'])[:8]:
            self._validate_outbox()
            if item['draft'] is None:
                item['draft']={'schema_version':'draft/1','room_id':self.state['invitation']['room'],'event_id':uid(),
                  'author_room_key':self.state['identity']['sign_public'],'author_sequence':self.state['sequence']+1,
                  'previous_author_event':self.state['previous'],'parent_event_ids':item['parents'],'object_id':item['object_id'],
                  'operation':'revision','payload':item['payload']};self.save()
            self._validate_outbox()
            draft=item['draft']
            response,started,request=self.ask(transport,'grant',{'event_digest':digest(draft),'expected_epoch':self.state['epoch']},owner_pump=owner_pump,deadline=deadline)
            grant=self.begin_batch(response,request,draft,started)
            try:
                self.state['epoch']=grant['epoch'];self.save()
                content={'schema_version':'delivery/1','draft':draft,'membership_epoch':grant['epoch'],
                         'recipient_set_digest':digest(grant['roster']),'grant':response}
                event=signed(content,SigningKey(un64(self.state['identity']['sign_secret'])),'delivery')
                # Persist exact ciphertext + consumption atomically before the first POST.
                # This journal is evidence/retry state, never authority after process restart.
                attempt={'nonce':request['nonce'],'event_id':draft['event_id'],'epoch':grant['epoch'],
                         'consumed':True,'deliveries':[{'mailbox':r['mailbox'],'packet_id':uid(),
                           'packet':seal(r['enc_public'],{'kind':'event','value':event}),'acknowledged':False}
                           for r in grant['roster']]}
                self.state['attempt']=attempt;self.save()
                for delivery in attempt['deliveries']:
                    if self.state['epoch']!=grant['epoch']:raise Rejected('epoch changed')
                    for retry in range(2):
                        self.validate_grant(response,request,draft,started,in_batch=True)
                        if self.state['epoch']!=grant['epoch']:raise Rejected('epoch changed')
                        try:
                            put(transport,grant['room'],delivery['mailbox'],delivery['packet'],delivery['packet_id'])
                            break
                        except ConnectionError:
                            if retry:raise
                    delivery['acknowledged']=True;self.save()
                self.receive(event)
                self.state['sequence']=draft['author_sequence'];self.state['previous']=draft['event_id'];self.state['queue'].remove(item)
                self.state.pop('attempt',None);self.save()
            finally:
                self._batches.pop(request['nonce'],None)
        self.status='Synced while owner reachable — pseudonymous, not guaranteed anonymous'
    def receive(self,document):
        self._drain_pending()
        content=document['body'];draft=content['draft'];inv=self.state['invitation']
        verify(document,draft['author_room_key'],'delivery');exact(content,'schema_version draft membership_epoch recipient_set_digest grant')
        exact(draft,'schema_version room_id event_id author_room_key author_sequence previous_author_event parent_event_ids object_id operation payload')
        if content['schema_version']!='delivery/1' or draft['schema_version']!='draft/1' or draft['room_id']!=inv['room']:raise Rejected('wrong room/schema')
        grant_response=verify(content['grant'],inv['authority'],'owner-response');grant=grant_response['result']
        exact(grant,'schema room sender challenge event_digest expected_epoch epoch roster issued max_validity_seconds')
        if grant_response['room']!=inv['room'] or grant_response['nonce']!=grant['challenge'] or grant['schema']!='grant/1' or grant['room']!=inv['room'] or grant['sender']!=draft['author_room_key'] or grant['event_digest']!=digest(draft) or grant['epoch']!=content['membership_epoch'] or digest(grant['roster'])!=content['recipient_set_digest']:raise Rejected('grant binding')
        keys={m['sign_public'] for m in grant['roster']}
        if self.state['identity']['sign_public'] not in keys or draft['author_room_key'] not in keys:raise Rejected('not recipient/member')
        ident(draft['event_id']);ident(draft['object_id']);projection(draft['payload'])
        if type(draft['author_sequence'])is not int or draft['author_sequence']<1 or draft['operation']!='revision':raise Rejected('sequence/operation')
        parents=draft['parent_event_ids']
        if not isinstance(parents,list) or len(parents)>8 or len(set(parents))!=len(parents):raise Rejected('parents')
        for p in parents:ident(p)
        if draft['previous_author_event'] is not None:ident(draft['previous_author_event'])
        ready=self._pending_ready(draft)
        events,pending=self.state['events'],self.state['pending'];eid=draft['event_id']
        old=events.get(eid) or pending.get(eid)
        if old:
            if old!=draft:raise Rejected('event collision')
            return
        for e in list(events.values())+list(pending.values()):
            if e['author_room_key']==draft['author_room_key'] and e['author_sequence']==draft['author_sequence']:raise Rejected('sequence equivocation')
        if len(events)>=MAX_EVENTS or (not ready and len(pending)>=32):raise Rejected('event/buffer capacity')
        if ready:events[eid]=draft
        else:pending[eid]=draft
        self._drain_pending()
        self.save()
    def _pending_ready(self,e):
        exact(e,'schema_version room_id event_id author_room_key author_sequence previous_author_event parent_event_ids object_id operation payload')
        ident(e['event_id']);ident(e['object_id']);projection(e['payload'])
        if e['schema_version']!='draft/1' or e['operation']!='revision' or not self.state['invitation'] or e['room_id']!=self.state['invitation']['room']:raise Rejected('pending schema/room')
        if type(e['author_sequence']) is not int or e['author_sequence']<1:raise Rejected('chain sequence')
        parents=e['parent_event_ids'];previous=e['previous_author_event'];events=self.state['events']
        if not isinstance(parents,list) or len(parents)>8:raise Rejected('pending parents')
        for p in parents:ident(p)
        if len(set(parents))!=len(parents):raise Rejected('pending duplicate parents')
        if previous is not None:ident(previous)
        if (e['author_sequence']==1)!=(previous is None):raise Rejected('chain predecessor required')
        if e['event_id'] in parents or previous==e['event_id']:raise Rejected('self dependency')
        if previous in events:
            prior=events[previous]
            if prior['author_room_key']!=e['author_room_key'] or prior['author_sequence']!=e['author_sequence']-1:raise Rejected('chain binding')
        if any(p in events and events[p]['object_id']!=e['object_id'] for p in parents):raise Rejected('parent object')
        return all(p in events for p in parents) and (previous is None or previous in events)
    def _drain_pending(self):
        events,pending=self.state['events'],self.state['pending'];changed=False
        while True:
            progressed=False
            for k,e in list(pending.items()):
                try:
                    if k!=e['event_id']:raise Rejected('pending identity')
                    ready=self._pending_ready(e)
                except (Rejected,KeyError,TypeError,ValueError):
                    del pending[k];self.state['quarantined']+=1;changed=True;progressed=True
                    continue
                if ready and len(events)<MAX_EVENTS:
                    events[k]=pending.pop(k);progressed=True;changed=True
            if not progressed:break
        if changed:self.save()
    def leave(self,transport,**kwargs):
        response,_,_=self.ask(transport,'leave',{},**kwargs)
        if response['body']['result'].get('left') is not True:raise Rejected('leave not acknowledged')
        self.pause();self.status='Left room; prior recipients may retain history'
