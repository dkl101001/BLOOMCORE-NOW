# SPDX-License-Identifier: Apache-2.0
import datetime as dt
import hashlib
import ipaddress
import json
import re
import sqlite3
import time
from urllib.parse import urlsplit
import requests

MAX_BYTES = 512 * 1024
STATES = {'planned', 'purchased', 'installed', 'operating', 'unknown'}

class ResearchError(ValueError): pass

def public_url(url):
    if not isinstance(url,str) or len(url)>2048: raise ResearchError('URL limit')
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.fragment or p.query:
        raise ResearchError('Only public HTTPS static URLs without queries are supported')
    host=(p.hostname or '').lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,63}',host) or host.endswith(('.local','.localhost','.internal','.onion','.test','.invalid')):
        raise ResearchError('Public hostname required; literals and local names prohibited')
    try: ipaddress.ip_address(host); raise ResearchError('IP literals prohibited')
    except ValueError as exc:
        if isinstance(exc,ResearchError):raise
    if '..' in host or any(x.startswith('xn--') for x in host.split('.')):raise ResearchError('Ambiguous hostname')
    return url

class PublicTransport:
    """Proxy resolves approved public hostnames; no local DNS or direct fallback."""
    def __init__(self,proxy='socks5h://127.0.0.1:9050'):
        if not re.fullmatch(r'socks5h://127\.0\.0\.1:[0-9]{1,5}',proxy):raise ResearchError('Local SOCKS5h required')
        self.proxy=proxy
    def fetch(self,url):
        public_url(url)
        with requests.Session() as s:
            s.trust_env=False;s.headers.clear()
            try:
                with s.get(url,proxies={'https':self.proxy,'http':self.proxy},allow_redirects=False,
                           timeout=(3,10),stream=True,headers={'Accept':'text/plain,text/html,application/json,application/xml','User-Agent':'FLOCK-OFF-Public-Research/0.1'}) as r:
                    if r.status_code!=200:raise ResearchError('Source unavailable; no redirect or access-control bypass')
                    kind=r.headers.get('Content-Type','').split(';')[0].lower()
                    if kind not in {'text/plain','text/html','application/json','application/xml','text/xml'}:raise ResearchError('Static text only')
                    if r.headers.get('Content-Encoding','identity') not in ('identity',''):raise ResearchError('Compressed sources not supported')
                    data=bytearray()
                    for chunk in r.iter_content(4096):
                        data.extend(chunk)
                        if len(data)>MAX_BYTES:raise ResearchError('Source size limit')
                    return bytes(data).decode('utf-8',errors='strict')
            except requests.RequestException:raise ResearchError('Tor unavailable or source failed; no fallback attempted') from None

class ResearchStore:
    """Public documents and scoped source-bound conductance memory only."""
    def __init__(self,path,scope='public-default'):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,url TEXT,digest TEXT,record TEXT,UNIQUE(url,digest))')
        self.db.execute("CREATE TRIGGER IF NOT EXISTS immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable public source revision'); END")
        self.db.execute("CREATE TRIGGER IF NOT EXISTS immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable public source revision'); END")
        if self.db.execute('SELECT count(*) FROM revisions').fetchone()[0]:
            self.db.close()
            raise ResearchError('Legacy research store requires explicit migration; preserve original')
        from .memory import PublicMemory
        self.memory=PublicMemory(self.db,scope)
    def record(self,url,text,*,publication_date=None,document_date=None,category='other',claim_state='unknown',excerpt='',boundaries='',contradictions=None,questions=None):
        public_url(url)
        if not isinstance(text,str) or len(text.encode())>MAX_BYTES:raise ResearchError('Document limit')
        if claim_state not in STATES:raise ResearchError('Claim state must be explicit')
        if excerpt and excerpt not in text:raise ResearchError('Excerpt must be exact source text')
        if len(excerpt)>4000 or len(boundaries)>2000:raise ResearchError('Annotation limit')
        for date in (publication_date,document_date):
            if date is not None:dt.date.fromisoformat(date)
        for entries in (contradictions or [],questions or []):
            if len(entries)>16 or any(not isinstance(x,str) or len(x)>1000 for x in entries):raise ResearchError('Annotation limit')
        digest=hashlib.sha256(text.encode()).hexdigest()
        record={'source_url':url,'sha256':digest,'publication_date':publication_date,'document_date':document_date,
                'encountered_at':dt.datetime.now(dt.UTC).isoformat(),'source_text':text,'exact_excerpt':excerpt,
                'category':category,'claim_state':claim_state,'evidence_basis':'PUBLIC_RECORD_PRIOR_NOT_LOCAL_MEASUREMENT',
                'claim_boundaries':boundaries,'contradictions':contradictions or [],'unresolved_questions':questions or []}
        return self.memory.ingest(record)
    def history(self,url):
        return [r for r in self.memory.records() if r['source_url']==url]
    def close(self):self.db.close()

class ResearchAgent:
    def __init__(self,store,transport=None,clock=time.monotonic):
        self.store=store;self.transport=transport or PublicTransport();self.clock=clock
        self.enabled=False;self.watchlist=[];self.last_attempt={};self.last_global=None
        self.memory_status='PUBLIC_SOURCE_BOUND_CONDUCTANCE_MEMORY_V1'
    def enable(self,urls,*,confirmed=False,public_scope='',access_rules_reviewed=False):
        if confirmed is not True or access_rules_reviewed is not True or not public_scope.strip():raise ResearchError('Explicit public scope and access-rule review required')
        if not 1<=len(urls)<=20 or len(set(urls))!=len(urls):raise ResearchError('Watchlist limit')
        validated=[public_url(u) for u in urls]
        from .memory import PublicMemory
        self.store.memory=PublicMemory(self.store.db,public_scope)
        self.watchlist=validated;self.enabled=True
    def disable(self):self.enabled=False
    def tick(self,*,app_active=True):
        if not self.enabled or not app_active:return None
        now=self.clock()
        if self.last_global is not None and now-self.last_global<60:return None
        for url in self.watchlist:
            if url in self.last_attempt and now-self.last_attempt[url]<3600:continue
            self.last_attempt[url]=now;self.last_global=now
            text=self.transport.fetch(url)
            return self.store.record(url,text,boundaries='Fetched public source only; deployment status and truth require human assessment.',questions=['Does this source establish planned, purchased, installed or operating equipment?'])
        return None
