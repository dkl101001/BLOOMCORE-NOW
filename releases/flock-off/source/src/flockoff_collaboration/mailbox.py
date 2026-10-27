# SPDX-License-Identifier: Apache-2.0
"""Opaque bounded relay. No member identities, room rosters or signing keys."""
import hashlib
import hmac
import sqlite3
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from flockoff_red_tape.ledger import private_write
from .protocol import exact, ident, uid, un64, parse, canonical, Rejected, MAX_BYTES

def token_hash(value):return hashlib.sha256(value.encode()).hexdigest()

class MailboxRelay:
    def __init__(self,path):
        self.path=Path(path)
        if not self.path.exists():private_write(self.path,b'')
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS spaces(id TEXT PRIMARY KEY,admin TEXT);
          CREATE TABLE IF NOT EXISTS boxes(room TEXT,id TEXT PRIMARY KEY,r TEXT,w TEXT);
          CREATE TABLE IF NOT EXISTS packets(seq INTEGER PRIMARY KEY AUTOINCREMENT,box TEXT,id TEXT,body TEXT,UNIQUE(box,id));''')
        self.lock=threading.RLock()
    def create_space(self):
        with self.lock,self.db:
            if self.db.execute('SELECT count(*) FROM spaces').fetchone()[0]>=8:raise Rejected('capacity')
            room,admin=uid(),uid();self.db.execute('INSERT INTO spaces VALUES(?,?)',(room,token_hash(admin)))
            return {'room':room,'admin':admin}
    def rpc(self,body):
        exact(body,'room action data');ident(body['room']);data=body['data'];action=body['action']
        with self.lock,self.db:
            if action=='mailbox':
                exact(data,'admin');row=self.db.execute('SELECT admin FROM spaces WHERE id=?',(body['room'],)).fetchone()
                if not row or not hmac.compare_digest(row[0],token_hash(data['admin'])):raise Rejected('unauthorized')
                if self.db.execute('SELECT count(*) FROM boxes WHERE room=?',(body['room'],)).fetchone()[0]>=16:raise Rejected('capacity')
                route,read,write=uid(),uid(),uid();self.db.execute('INSERT INTO boxes VALUES(?,?,?,?)',(body['room'],route,token_hash(read),token_hash(write)))
                return {'route':route,'read':read,'write':write}
            if action not in ('put','get'):raise Rejected('action')
            exact(data,'route token id packet' if action=='put' else 'route token cursor')
            row=self.db.execute('SELECT r,w FROM boxes WHERE room=? AND id=?',(body['room'],data['route'])).fetchone()
            if not row or not hmac.compare_digest(row[1 if action=='put' else 0],token_hash(data['token'])):raise Rejected('unauthorized')
            if action=='put':
                ident(data['id'])
                if not 48<=len(un64(data['packet']))<=24000:raise Rejected('packet limit')
                old=self.db.execute('SELECT body FROM packets WHERE box=? AND id=?',(data['route'],data['id'])).fetchone()
                if old:
                    if old[0]!=data['packet']:raise Rejected('packet collision')
                else:
                    if self.db.execute('SELECT count(*) FROM packets WHERE box=?',(data['route'],)).fetchone()[0]>=2000:raise Rejected('capacity')
                    self.db.execute('INSERT INTO packets(box,id,body) VALUES(?,?,?)',(data['route'],data['id'],data['packet']))
                return {'accepted':data['id']}
            if type(data['cursor'])is not int or data['cursor']<0:raise Rejected('cursor')
            row=self.db.execute('SELECT seq,id,body FROM packets WHERE box=? AND seq>? ORDER BY seq LIMIT 1',(data['route'],data['cursor'])).fetchone()
            return {'cursor':row[0] if row else data['cursor'],'id':row[1] if row else None,'packet':row[2] if row else None}
    def close(self):self.db.close()

def server(relay,port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            self.connection.settimeout(5)
            if self.path!='/rpc':self.send_error(404);return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=MAX_BYTES:raise Rejected('body limit')
                raw=canonical(relay.rpc(parse(self.rfile.read(n))));status=200
            except Exception:raw=b'{"error":"request rejected"}';status=400
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
    return HTTPServer(('127.0.0.1',port),Handler)
