# SPDX-License-Identifier: Apache-2.0
"""Explicit public-source research window. No private-vault imports or startup fetches."""
import json
import queue
import secrets
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .ledger import private_write


class ResearchWorker:
    """A single persistent agent preserves rate limits and owns its SQLite connection."""
    def __init__(self,path,scope,store_factory=None,agent_factory=None):
        self.path=path;self.scope=scope;self.inbox=queue.Queue(maxsize=1);self.results=queue.Queue()
        self.stopping=threading.Event()
        self.thread=threading.Thread(target=self.run,args=(store_factory,agent_factory),daemon=True);self.thread.start()
    def submit(self,action,**kwargs):
        if not self.thread.is_alive() or self.stopping.is_set():raise ValueError('Research worker is closed')
        self.inbox.put_nowait((action,kwargs))
    def run(self,store_factory,agent_factory):
        from flockoff_research.agent import ResearchStore,ResearchAgent
        store=None
        try:
            store=(store_factory or ResearchStore)(self.path,self.scope)
            agent=(agent_factory or ResearchAgent)(store)
            self.results.put((True,'Public research store open; watchlist disabled',store.memory.records()))
            while not self.stopping.is_set():
                action,kwargs=self.inbox.get()
                if action=='close':break
                try:
                    if action=='enable':agent.enable(**kwargs);message='Public watchlist enabled while this window is open'
                    elif action=='disable':agent.disable();message='Public watchlist disabled'
                    elif action=='tick':agent.tick(app_active=True);message='Public watchlist checked within rate limits'
                    elif action=='history':message='Public source history loaded'
                    else:raise ValueError('Unsupported action')
                    self.results.put((True,message,store.memory.records()))
                except Exception:self.results.put((False,'Research action unavailable; check public scope, access rules and Tor. No fallback attempted.',None))
            agent.disable()
        except Exception:self.results.put((False,'Public store could not be opened; preserve it and verify setup.',None))
        finally:
            if store:store.close()
    def close(self):
        self.stopping.set()
        try:self.inbox.put_nowait(('close',{}))
        except queue.Full:pass


def create_workspace(parent,scope):
    if not isinstance(scope,str) or not 1<=len(scope.strip())<=128:raise ValueError('Public scope must contain 1–128 characters')
    folder=Path(parent)/('public-research-'+secrets.token_hex(12));folder.mkdir(mode=0o700)
    private_write(folder/'workspace.json',json.dumps({'schema':'public-research-ui/1','scope':scope.strip()}).encode())
    private_write(folder/'public-research.sqlite3',b'')
    return folder/'public-research.sqlite3',scope.strip()


def open_workspace(folder):
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('Select a dedicated research workspace')
    marker=folder/'workspace.json';db=folder/'public-research.sqlite3'
    if marker.is_symlink() or db.is_symlink():raise ValueError('Research workspace links are not supported')
    with marker.open('rb') as f:value=json.loads(f.read(4097))
    if set(value)!={'schema','scope'} or value['schema']!='public-research-ui/1' or not isinstance(value['scope'],str) or not 1<=len(value['scope'])<=128 or not db.is_file():raise ValueError('Not a public research workspace')
    # Reject unrelated SQLite schemas without reading their content or mutating them.
    if db.stat().st_size:
        import sqlite3
        connection=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            names={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not names<= {'revisions','public_evidence','public_geometry','public_encounters'}:raise ValueError('Not a dedicated public research database')
        finally:connection.close()
    return db,value['scope']


class ResearchWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.title('Public-source research — deliberate watchlist');self.geometry('900x800')
        self.experimental_notice=ttk.Label(self,text='EXPERIMENTAL: independent security review is incomplete; live Tor/network privacy is unvalidated. Use synthetic or nonsensitive data while review is pending. No guaranteed anonymity.',wraplength=850)
        self.experimental_notice.pack(fill='x',padx=10,pady=8)
        self.worker=None;self.busy=False;self.enabled=False;self.closing=False;self.records=[]
        self.status=tk.StringVar(value='Disabled. No startup fetch. Public sources only; do not enter private names, case or room identifiers.')
        ttk.Label(self,textvariable=self.status,wraplength=850).pack(fill='x',padx=10,pady=8)
        ttk.Label(self,text='Public research scope (public topic only, no private queries)').pack(anchor='w')
        self.scope=ttk.Entry(self,width=90);self.scope.pack(fill='x',padx=10)
        self.buttons=[]
        self.button('Create separate public research workspace',self.create)
        self.button('Open public research workspace',self.open)
        ttk.Label(self,text='Approved static public HTTPS URLs, one per line (maximum 20; no queries or credentials)').pack(anchor='w')
        self.urls=tk.Text(self,height=5);self.urls.pack(fill='x',padx=10)
        self.consent=tk.BooleanVar(value=False);self.rules=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text='Enable only this public watchlist while this window is open',variable=self.consent).pack(anchor='w')
        ttk.Checkbutton(self,text='I reviewed these sources’ access rules and authorize bounded fetching',variable=self.rules).pack(anchor='w')
        self.button('Apply explicit watchlist consent',self.enable)
        self.button('Disable watchlist',self.disable)
        self.button('Refresh local history',lambda:self.submit('history'))
        self.history=ttk.Treeview(self,columns=('source','state','date'),show='headings',height=5)
        for name in ('source','state','date'):self.history.heading(name,text=name.title())
        self.history.pack(fill='x');self.history.bind('<<TreeviewSelect>>',self.show)
        self.content=tk.Text(self,height=12,wrap='word',state='disabled');self.content.pack(fill='both',expand=True)
        ttk.Label(self,text='Sources are untrusted public-record priors, not local measurements. Text is displayed without HTML rendering, clickable links or automatic sharing.',wraplength=850).pack()
        self.protocol('WM_DELETE_WINDOW',self.close);self.timer=self.after(100,self.poll);self.tick_timer=self.after(1000,self.tick)
    def button(self,label,fn):
        b=ttk.Button(self,text=label,command=lambda:self.safe(fn));b.pack(anchor='w',padx=10,pady=2);self.buttons.append(b)
    def safe(self,fn):
        if self.busy or self.closing:return
        try:fn()
        except Exception:messagebox.showerror('Research action unavailable','Choose a dedicated public workspace and review the scope, URLs and consent. No private store is imported.',parent=self)
    def attach(self,path,scope):
        if self.worker:raise ValueError('Close this window before switching workspaces')
        self.scope.delete(0,'end');self.scope.insert(0,scope);self.scope.configure(state='disabled')
        self.worker=ResearchWorker(path,scope);self.busy=True
    def create(self):
        if self.worker:raise ValueError('Workspace already open')
        parent=filedialog.askdirectory(parent=self,title='Parent directory for a new separate public workspace')
        if parent:self.attach(*create_workspace(parent,self.scope.get()))
    def open(self):
        if self.worker:raise ValueError('Workspace already open')
        folder=filedialog.askdirectory(parent=self,title='Existing dedicated public research workspace')
        if folder:self.attach(*open_workspace(folder))
    def submit(self,action,**kwargs):
        if not self.worker or self.busy:raise ValueError('Open public workspace and wait for current work')
        self.worker.submit(action,**kwargs);self.busy=True
        for button in self.buttons:button.configure(state='disabled')
    def enable(self):
        if not self.consent.get() or not self.rules.get():raise ValueError('Both explicit consent checks are required')
        urls=[v.strip() for v in self.urls.get('1.0','end-1c').splitlines() if v.strip()]
        from flockoff_research.agent import public_url
        if not 1<=len(urls)<=20 or len(set(urls))!=len(urls):raise ValueError('Select 1–20 distinct URLs')
        for url in urls:public_url(url)
        self.submit('enable',urls=urls,confirmed=True,public_scope=self.scope.get(),access_rules_reviewed=True);self.enabled=True
    def disable(self):
        self.enabled=False;self.consent.set(False);self.submit('disable')
    def tick(self):
        if self.closing:return
        if self.enabled and self.worker and not self.busy:self.submit('tick')
        self.tick_timer=self.after(1000,self.tick)
    def poll(self):
        if self.closing:return
        if self.worker:
            try:
                ok,status,records=self.worker.results.get_nowait();self.busy=False;self.status.set(status)
                for button in self.buttons:button.configure(state='normal')
                if not ok:self.enabled=False
                if records is not None:
                    self.records=records;self.history.delete(*self.history.get_children())
                    for i,r in enumerate(records):self.history.insert('', 'end',iid=str(i),values=(r['source_url'],r['claim_state'],r['encountered_at']))
            except queue.Empty:pass
        self.timer=self.after(100,self.poll)
    def show(self,_=None):
        selected=self.history.selection()
        if not selected:return
        r=self.records[int(selected[0])]
        fields=['source_url','publication_date','document_date','encountered_at','sha256','category','claim_state','evidence_basis','claim_boundaries','contradictions','unresolved_questions','exact_excerpt','source_text']
        self.content.configure(state='normal');self.content.delete('1.0','end')
        for field in fields:self.content.insert('end',field.replace('_',' ').title()+': '+str(r.get(field,''))+'\n\n')
        self.content.configure(state='disabled')
    def close(self):
        self.enabled=False
        if not self.closing:
            self.closing=True;self.after_cancel(self.timer);self.after_cancel(self.tick_timer)
            if self.worker:self.worker.close()
        if self.worker and self.worker.thread.is_alive():self.after(100,self.close);return
        self.destroy()


def launch_research(root):return ResearchWindow(root)
