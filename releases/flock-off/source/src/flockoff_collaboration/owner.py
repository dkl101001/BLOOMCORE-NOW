# SPDX-License-Identifier: Apache-2.0
"""Room owner endpoint: signing secrets stay LOCAL, never provisioned to relay."""
import json
import sqlite3
import time
from pathlib import Path
from cryptography.fernet import Fernet
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey
from flockoff_red_tape.ledger import private_write
from .protocol import *


class LocalState:
    def __init__(self,path,key_path,create=False):
        path,key_path=Path(path),Path(key_path)
        if path.resolve()==key_path.resolve():raise Rejected('separate key required')
        if create:
            if path.exists() or key_path.exists():raise Rejected('new paths required')
            private_write(key_path,Fernet.generate_key());private_write(path,b'')
        self.cipher=Fernet(key_path.read_bytes())
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY,ciphertext BLOB)')
        row=self.db.execute('SELECT ciphertext FROM state WHERE id=1').fetchone()
        self.state=json.loads(self.cipher.decrypt(row[0])) if row else {}
    def save(self):
        raw=json.dumps(self.state,sort_keys=True,separators=(',',':')).encode()
        if len(raw)>32*1024*1024:raise Rejected('storage limit')
        with self.db:self.db.execute('INSERT OR REPLACE INTO state VALUES(1,?)',(self.cipher.encrypt(raw),))
    def close(self):self.db.close()


def put(transport,room,box,packet,packet_id=None):
    packet_id=packet_id or uid()
    result=transport.rpc({'room':room,'action':'put','data':{'route':box['route'],'token':box['write'],'id':packet_id,'packet':packet}})
    if result!={'accepted':packet_id}:raise Rejected('relay acknowledgement mismatch')
    return packet_id


def get(transport,room,box,cursor):
    response=transport.rpc({'room':room,'action':'get','data':{'route':box['route'],'token':box['read'],'cursor':cursor}})
    exact(response,'cursor id packet')
    if type(response['cursor']) is not int or response['cursor']<cursor:raise Rejected('cursor rollback')
    return response


def seal(public,document):return b64(SealedBox(PublicKey(un64(public))).encrypt(canonical(document)))
def decrypt(secret,packet):return parse(SealedBox(PrivateKey(un64(secret))).decrypt(un64(packet)))
def routing(box):return {'route':box['route'],'write':box['write']}


class RoomOwner(LocalState):
    def initialize(self,provision,transport,endpoint):
        if self.state:raise Rejected('owner already initialized')
        exact(provision,'room admin');ident(provision['room'])
        identity=new_identity()
        box=transport.rpc({'room':provision['room'],'action':'mailbox','data':{'admin':provision['admin']}})
        self.state={'room':provision['room'],'admin':provision['admin'],'endpoint':endpoint,'identity':identity,
                    'box':box,'epoch':1,'members':{},'invites':{},'cursor':0,'used':{},'last_clock':0,'quarantined':0}
        self.save()

    def make_invite(self,public,transport):
        member(public)
        if len(self.state['members'])+len(self.state['invites'])>=MAX_MEMBERS:raise Rejected('room capacity')
        box=transport.rpc({'room':self.state['room'],'action':'mailbox','data':{'admin':self.state['admin']}})
        token=uid();record={'public':public,'box':box,'epoch':self.state['epoch'],'expires':int(time.time())+300}
        self.state['invites'][token]=record;self.save()
        body={'schema':'invitation/1','room':self.state['room'],'authority':self.state['identity']['sign_public'],
              'owner_encryption':self.state['identity']['enc_public'],'owner_route':routing(self.state['box']),
              'endpoint':self.state['endpoint'],'token':token,'epoch':record['epoch'],'expires':record['expires'],
              'member':public,'mailbox':box}
        return seal(public['enc_public'],signed(body,SigningKey(un64(self.state['identity']['sign_secret'])),'invitation'))

    def remove(self,public_key):
        if public_key not in self.state['members']:raise Rejected('unknown member')
        del self.state['members'][public_key];self.state['epoch']+=1;self.state['invites']={};self.save()

    def roster(self):
        return sorted([{**m['public'],'mailbox':routing(m['box'])} for m in self.state['members'].values()],key=lambda m:m['sign_public'])

    def pump(self,transport,limit=16):
        # A saved response can be retried byte-for-byte after an uncertain relay ACK.
        # The sender's independent live challenge deadline still limits its use.
        now=int(time.time())
        if now<self.state['last_clock']-5:raise Rejected('owner clock rollback')
        responses=self.state.setdefault('responses',{})
        for nonce,row in list(responses.items()):
            if row['expires']<=now:
                del responses[nonce];continue
            if not row['sent']:
                put(transport,self.state['room'],row['box'],row['packet'],row['packet_id'])
                row['sent']=True;self.save()
        for _ in range(min(limit,16)):
            item=get(transport,self.state['room'],self.state['box'],self.state['cursor'])
            if item['packet'] is None:return
            self.state['cursor']=item['cursor']
            try:
                request=decrypt(self.state['identity']['enc_secret'],item['packet'])
                body=request['body'];verify(request,body['author'],'owner-request')
                exact(body,'schema room author nonce issued action data')
                now=int(time.time())
                if now<self.state['last_clock']-5:raise Rejected('owner clock rollback')
                self.state['last_clock']=max(now,self.state['last_clock'])
                if body['schema']!='owner-request/1' or body['room']!=self.state['room'] or type(body['issued'])is not int or abs(now-body['issued'])>30:raise Rejected('request binding or expiry')
                ident(body['nonce'])
                prior=responses.get(body['nonce'])
                if prior:
                    if prior['request_digest']!=digest(request):raise Rejected('nonce binding collision')
                    if prior['expires']<=now:raise Rejected('expired response')
                    prior['sent']=False;self.save()
                    put(transport,self.state['room'],prior['box'],prior['packet'],prior['packet_id'])
                    prior['sent']=True;self.save();continue
                self.state['used']={k:v for k,v in self.state['used'].items() if v>now-60}
                if body['nonce'] in self.state['used'] or len(self.state['used'])>=1024:raise Rejected('request replay/budget')
                self.state['used'][body['nonce']]=now
                action,data=body['action'],body['data']
                if action=='join':
                    exact(data,'token');inv=self.state['invites'].get(data['token'])
                    if not inv or inv['epoch']!=self.state['epoch'] or inv['expires']<=now or inv['public']['sign_public']!=body['author']:raise Rejected('invalid invitation')
                    self.state['members'][body['author']]=inv;self.state['epoch']+=1;self.state['invites']={}
                    result={'joined':True,'epoch':self.state['epoch']};target=inv
                else:
                    target=self.state['members'].get(body['author'])
                    if not target:raise Rejected('inactive member')
                    if action=='grant':
                        exact(data,'event_digest expected_epoch')
                        if not isinstance(data['event_digest'],str) or not re.fullmatch('[a-f0-9]{64}',data['event_digest']):raise Rejected('digest')
                        if type(data['expected_epoch'])is not int or data['expected_epoch']>self.state['epoch']:raise Rejected('unknown epoch')
                        result={'schema':'grant/1','room':self.state['room'],'sender':body['author'],'challenge':body['nonce'],
                                'event_digest':data['event_digest'],'expected_epoch':data['expected_epoch'],'epoch':self.state['epoch'],
                                'roster':self.roster(),'issued':now,'max_validity_seconds':30}
                    elif action=='leave':
                        exact(data,'');del self.state['members'][body['author']]
                        self.state['epoch']+=1;self.state['invites']={};result={'left':True,'epoch':self.state['epoch']}
                    else:raise Rejected('action')
                response=signed({'schema':'owner-response/1','room':self.state['room'],'nonce':body['nonce'],'result':result},SigningKey(un64(self.state['identity']['sign_secret'])),'owner-response')
                row={'request_digest':digest(request),'expires':now+30,'box':target['box'],'packet_id':uid(),
                     'packet':seal(target['public']['enc_public'],{'kind':'owner-response','value':response}),'sent':False}
                responses[body['nonce']]=row
                # Membership, consumed challenge, response bytes and cursor commit together.
                self.save()
                put(transport,self.state['room'],row['box'],row['packet'],row['packet_id'])
                row['sent']=True
            except ConnectionError:
                self.save();raise
            except Exception:
                self.state['quarantined']+=1
            self.save()
