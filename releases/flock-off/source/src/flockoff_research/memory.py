# SPDX-License-Identifier: AGPL-3.0-only
"""FLOCK public-evidence adapter to the pinned TI-AGI83+ conductance core."""
import hashlib
import json
import numpy as np
from . import _geometry as geometry

CATEGORIES = ('contract', 'council', 'permit', 'inventory', 'map', 'other')
STATUSES = ('planned', 'purchased', 'installed', 'operating', 'unknown')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def cue(category, status):
    """Version 1: category row, deployment-status column; no inferred semantics."""
    a = np.zeros((8, 8), dtype=np.float32)
    a[CATEGORIES.index(category), STATUSES.index(status)] = 1
    return a

def validate_record(r):
    from .agent import public_url, MAX_BYTES
    fields={'source_url','sha256','publication_date','document_date','encountered_at','source_text',
            'exact_excerpt','category','claim_state','evidence_basis','claim_boundaries','contradictions','unresolved_questions'}
    if not isinstance(r,dict) or set(r)!=fields: raise ValueError('Public evidence fields only')
    public_url(r['source_url']); cue(r['category'],r['claim_state'])
    if not isinstance(r['source_text'],str) or len(r['source_text'].encode())>MAX_BYTES or hashlib.sha256(r['source_text'].encode()).hexdigest()!=r['sha256']:
        raise ValueError('Public evidence digest mismatch')
    if r['evidence_basis']!='PUBLIC_RECORD_PRIOR_NOT_LOCAL_MEASUREMENT': raise ValueError('Public prior only')
    if not isinstance(r['exact_excerpt'],str) or len(r['exact_excerpt'])>4000 or r['exact_excerpt'] not in r['source_text']:
        raise ValueError('Exact public excerpt required')
    if not isinstance(r['claim_boundaries'],str) or len(r['claim_boundaries'])>2000: raise ValueError('Boundary limit')
    import datetime as dt
    dt.datetime.fromisoformat(r['encountered_at'])
    for key in ('publication_date','document_date'):
        if r[key] is not None: dt.date.fromisoformat(r[key])
    for key in ('contradictions','unresolved_questions'):
        if not isinstance(r[key],list) or len(r[key])>16 or any(not isinstance(x,str) or len(x)>1000 for x in r[key]):
            raise ValueError('Annotation limit')

class PublicMemory:
    def __init__(self, db, scope):
        if not isinstance(scope, str) or not 1 <= len(scope) <= 128:
            raise ValueError('Public scope required (1..128 characters)')
        self.db, self.scope = db, scope
        db.executescript('''
        CREATE TABLE IF NOT EXISTS public_evidence(scope TEXT,url TEXT,digest TEXT,record TEXT,seq INTEGER,
          PRIMARY KEY(scope,url,digest),UNIQUE(scope,seq));
        CREATE TABLE IF NOT EXISTS public_geometry(scope TEXT PRIMARY KEY,state TEXT,checksum TEXT,cursor INTEGER);
        CREATE TABLE IF NOT EXISTS public_encounters(scope TEXT,digest TEXT,PRIMARY KEY(scope,digest));
        ''')
        self.state()

    def state(self):
        row = self.db.execute('SELECT state,checksum,cursor FROM public_geometry WHERE scope=?',(self.scope,)).fetchone()
        if row is None:
            if self.db.execute('SELECT 1 FROM public_evidence WHERE scope=?',(self.scope,)).fetchone():
                raise ValueError('Missing public geometry checkpoint')
            return geometry.initial(), 0
        state = json.loads(row[0]); geometry.validate(state)
        if digest(state) != row[1] or type(row[2]) is not int or row[2] < 0:
            raise ValueError('Corrupt public geometry checkpoint')
        count = self.db.execute('SELECT count(*) FROM public_evidence WHERE scope=?',(self.scope,)).fetchone()[0]
        trained = self.db.execute('SELECT count(*) FROM public_encounters WHERE scope=?',(self.scope,)).fetchone()[0]
        if count != row[2] or trained != state['tick']:
            raise ValueError('Public evidence/geometry cursor mismatch')
        return state, row[2]

    def ingest(self, record, fault=None):
        validate_record(record)
        field = cue(record['category'], record['claim_state'])
        # BEGIN IMMEDIATE also serializes competing receivers; acknowledgement follows commit.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            state, cursor = self.state()
            old = self.db.execute('SELECT record FROM public_evidence WHERE scope=? AND url=? AND digest=?',
                (self.scope,record['source_url'],record['sha256'])).fetchone()
            if old: return json.loads(old[0])
            if cursor >= 1000: raise ValueError('Public memory capacity reached')
            self.db.execute('INSERT INTO public_evidence VALUES(?,?,?,?,?)',
                (self.scope,record['source_url'],record['sha256'],canonical(record),cursor+1))
            if fault: fault('evidence')
            learned = self.db.execute('INSERT OR IGNORE INTO public_encounters VALUES(?,?)',
                (self.scope,record['sha256'])).rowcount
            if learned: state = geometry.encounter(state,field,backend='numpy')
            if fault: fault('encounter')
            self.db.execute('INSERT OR REPLACE INTO public_geometry VALUES(?,?,?,?)',
                (self.scope,canonical(state),digest(state),cursor+1))
            if fault: fault('checkpoint')
        return record

    def records(self):
        self.state()
        records = [json.loads(r[0]) for r in self.db.execute(
            'SELECT record FROM public_evidence WHERE scope=? ORDER BY seq',(self.scope,))]
        for record in records: validate_record(record)
        return records

    def query(self, category, status):
        state, cursor = self.state(); q = cue(category,status)
        learned = geometry.response(state,q); flat = geometry.response(state,q,flat=True)
        hits=[]
        for record in self.records():
            c=cue(record['category'],record['claim_state'])
            hits.append({'record':record,'distance':float(np.linalg.norm(learned-geometry.response(state,c))),
                         'flat_distance':float(np.linalg.norm(flat-geometry.response(state,c,flat=True))),
                         'eligible':True})
        hits.sort(key=lambda h:(h['distance'],h['record']['source_url'],h['record']['sha256']))
        return {'hits':hits,'cursor':cursor,'response_delta':float(np.linalg.norm(learned-flat)),
                'interpretation':'Typed advisory similarity, not truth or confidence; all revisions remain eligible.'}

    def checkpoint(self):
        state,cursor=self.state()
        body={'schema':'FLOCK.PUBLIC_MEMORY.v1','cue_version':1,'scope':self.scope,
              'state':state,'cursor':cursor,'records':self.records()}
        return {'body':body,'sha256':digest(body)}

    def restore(self, checkpoint):
        # Restore into an empty scope only; verify by deterministic replay before any writes.
        if len(canonical(checkpoint).encode()) > 8*1024*1024:
            raise ValueError('Checkpoint size limit')
        body=checkpoint['body']
        if set(checkpoint)!={'body','sha256'} or digest(body)!=checkpoint['sha256']:
            raise ValueError('Checkpoint integrity failure')
        if set(body)!={'schema','cue_version','scope','state','cursor','records'} or body['schema']!='FLOCK.PUBLIC_MEMORY.v1' or body['cue_version']!=1 or body['scope']!=self.scope:
            raise ValueError('Checkpoint schema/scope mismatch')
        if not isinstance(body['records'],list) or len(body['records'])>1000 or body['cursor']!=len(body['records']):
            raise ValueError('Checkpoint cursor mismatch')
        rebuilt=geometry.initial(); seen=set(); identities=set()
        for r in body['records']:
            validate_record(r)
            identity=(r['source_url'],r['sha256'])
            if identity in identities: raise ValueError('Duplicate checkpoint evidence')
            identities.add(identity)
            c=cue(r['category'],r['claim_state'])
            if r['sha256'] not in seen: rebuilt=geometry.encounter(rebuilt,c); seen.add(r['sha256'])
        geometry.validate(body['state'])
        if digest(rebuilt)!=digest(body['state']): raise ValueError('Checkpoint geometry does not match evidence')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.state()[1]: raise ValueError('Restore requires an empty scope')
            for i,r in enumerate(body['records'],1):
                self.db.execute('INSERT INTO public_evidence VALUES(?,?,?,?,?)',(self.scope,r['source_url'],r['sha256'],canonical(r),i))
            for d in seen: self.db.execute('INSERT INTO public_encounters VALUES(?,?)',(self.scope,d))
            self.db.execute('INSERT OR REPLACE INTO public_geometry VALUES(?,?,?,?)',
                (self.scope,canonical(rebuilt),digest(rebuilt),body['cursor']))
