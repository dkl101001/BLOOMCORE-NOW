# SPDX-License-Identifier: Apache-2.0
"""Three explicit local/shared/council paths; no startup networking."""
import json
import hashlib
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from cryptography.fernet import Fernet
from .ledger import private_write
from .document_variants import VariantStore
EXPERIMENTAL_NOTICE='EXPERIMENTAL: independent security review is incomplete; live Tor/network privacy is unvalidated. Use synthetic or nonsensitive data while review is pending. No guaranteed anonymity.'


class PrivateNotebook:
    def __init__(self, directory, key_path, create=False):
        self.directory=Path(directory);key_path=Path(key_path)
        if key_path.resolve().is_relative_to(self.directory.resolve()):raise ValueError('Keep the key outside the notebook folder')
        if create:
            if self.directory.exists() or key_path.exists():raise ValueError('Choose new notebook and key paths')
            self.directory.mkdir(parents=True);private_write(key_path,Fernet.generate_key())
        self.cipher=Fernet(key_path.read_bytes())
    def revisions(self):return sorted(self.directory.glob('revision-*.enc'))
    def read(self):
        files=self.revisions()
        return json.loads(self.cipher.decrypt(files[-1].read_bytes())) if files else {'title':'','text':'','revision':0}
    def save(self,title,text):
        if not title.strip() or len(title)>200 or not text.strip() or len(text)>100000:raise ValueError('Enter a title and bounded note')
        files=self.revisions();revision=len(files)+1
        value={'title':title,'text':text,'revision':revision}
        private_write(self.directory/f'revision-{revision:08d}.enc',self.cipher.encrypt(json.dumps(value).encode()))
        return revision


class WorkspacePaths(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.title('Private records / Shared room / Council packet');self.geometry('900x760')
        self.experimental_notice=ttk.Label(self,text=EXPERIMENTAL_NOTICE,wraplength=850)
        self.experimental_notice.pack(fill='x',padx=12,pady=8)
        self.notebook=None;self.variant_store=None;self.preview=None;self.peer_paths=None
        self.owner_console=None;self.edit_object=None;self.edit_parents=None
        self.busy=False;self.closed=False;self.auto=False;self.results=queue.Queue();self.controls=[]
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.status=tk.StringVar(value='Private by default. No startup sync or uploads.')
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True,padx=12,pady=12)
        private=ttk.Frame(tabs,padding=12);shared_host=ttk.Frame(tabs);council=ttk.Frame(tabs,padding=12)
        canvas=tk.Canvas(shared_host,highlightthickness=0);scroll=ttk.Scrollbar(shared_host,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        shared=ttk.Frame(canvas,padding=12);shared_window=canvas.create_window((0,0),window=shared,anchor='nw')
        shared.bind('<Configure>',lambda _:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(shared_window,width=event.width))
        for frame,label in [(private,'Private records'),(shared_host,'Shared room'),(council,'Council packet')]:tabs.add(frame,text=label)
        self.button(private,'New private notebook',lambda:self.open_notebook(True));self.button(private,'Open private notebook',lambda:self.open_notebook(False))
        self.note_title=self.entry(private,'Note title (no agency or meeting required)');self.note=self.text(private,'Private note')
        self.button(private,'Save new private revision',self.save_note)
        ttk.Label(private,text='Explicit saves only. Earlier revisions remain encrypted. Back up the folder and external key separately.',wraplength=800).pack(anchor='w')
        self.button(shared,'New room workspace',lambda:self.open_peer(True));self.button(shared,'Open room workspace',lambda:self.open_peer(False))
        self.button(shared,'Owner administration',self.open_owner);self.button(shared,'Received cards / branches',self.received)
        self.button(shared,'Save public join request',self.public_request);self.button(shared,'Import and preview invitation',self.import_invite)
        ttk.Label(shared,text='Share only deliberately composed cards. Do not paste private names, locations, routes, identifiers or vault content.\nTor and the room owner must be reachable. Pseudonyms are not a guarantee of anonymity.',wraplength=800).pack(anchor='w',pady=8)
        self.category=ttk.Combobox(shared,values=['question','comment','action','summary'],state='readonly');self.category.set('question');self.category.pack(anchor='w')
        self.card_title=self.entry(shared,'Shared card title');self.card=self.text(shared,'Shared card text',height=5)
        self.scopes={}
        for name in ['question','comment','action','summary']:
            var=tk.BooleanVar(value=False);self.scopes[name]=var;w=ttk.Checkbutton(shared,text='Allow automatic '+name+' sharing in this room',variable=var);w.pack(anchor='w');self.controls.append((w,'normal'))
        self.button(shared,'Enable selected scopes and automatic sync',self.enable_sync)
        self.button(shared,'Queue this selected card',self.queue_card);self.button(shared,'Sync now',self.sync);self.button(shared,'Pause sharing',self.pause);self.button(shared,'Leave room',self.leave)
        self.button(council,'Open private variant custody folder and key',self.open_variants)
        self.document_category=ttk.Combobox(council,values=['meeting','request','personal'],state='readonly');self.document_category.set('meeting');self.document_category.pack(anchor='w')
        self.source_reference=self.entry(council,'Private source reference (never included in output)')
        self.selected_text=self.text(council,'Deliberately selected document text',height=6)
        self.unbranded=tk.BooleanVar(value=True);ttk.Checkbutton(council,text='Unbranded output',variable=self.unbranded).pack(anchor='w')
        self.presenter=self.entry(council,'Presenter name (optional)');self.disclose=tk.BooleanVar(value=False)
        ttk.Checkbutton(council,text='Include this presenter identity in the preview',variable=self.disclose).pack(anchor='w')
        self.button(council,'Generate new variant and preview exact bytes',self.generate_preview)
        ttk.Label(self,textvariable=self.status,wraplength=850).pack(fill='x',padx=12,pady=8)
        self.timer=self.after(100,self.poll);self.sync_timer=self.after(5000,self.tick)
    def button(self,parent,label,action):
        w=ttk.Button(parent,text=label,command=lambda:self.safe(action));w.pack(anchor='w',pady=2);self.controls.append((w,'normal'));return w
    def entry(self,parent,label):
        ttk.Label(parent,text=label).pack(anchor='w');w=ttk.Entry(parent,width=85);w.pack(fill='x');self.controls.append((w,'normal'));return w
    def text(self,parent,label,height=10):
        ttk.Label(parent,text=label).pack(anchor='w');w=tk.Text(parent,height=height,wrap='word');w.pack(fill='both',expand=True);self.controls.append((w,'normal'));return w
    def safe(self,action):
        if self.busy:return
        try:action()
        except Exception as exc:messagebox.showerror('Could not complete',str(exc),parent=self)
    def choose_paths(self,create):
        path=filedialog.asksaveasfilename(parent=self,title='New workspace file') if create else filedialog.askopenfilename(parent=self,title='Open workspace file')
        if not path:return None
        key=filedialog.asksaveasfilename(parent=self,title='New separate key file') if create else filedialog.askopenfilename(parent=self,title='Select existing external key')
        return (path,key) if key else None
    def open_notebook(self,create):
        parent=filedialog.askdirectory(parent=self,title='Choose notebook parent' if create else 'Open notebook folder')
        if not parent:return
        key=filedialog.asksaveasfilename(parent=self,title='New external key') if create else filedialog.askopenfilename(parent=self,title='Existing external key')
        if not key:return
        directory=Path(parent)/('notebook-'+__import__('secrets').token_hex(6)) if create else Path(parent)
        self.notebook=PrivateNotebook(directory,key,create);value=self.notebook.read()
        self.note_title.delete(0,'end');self.note_title.insert(0,value['title']);self.note.delete('1.0','end');self.note.insert('1.0',value['text'])
        self.status.set('Private notebook open — nothing shared')
    def save_note(self):
        if not self.notebook:raise ValueError('Open a private notebook first')
        rev=self.notebook.save(self.note_title.get(),self.note.get('1.0','end-1c'));self.status.set(f'Private revision {rev} saved')
    def open_peer(self,create):
        from flockoff_collaboration.peer import Peer
        paths=self.choose_paths(create)
        if paths:
            if self.owner_console and self.owner_console.paths and Path(paths[0]).resolve()==Path(self.owner_console.paths[0]).resolve():raise ValueError('Separate participant and owner workspaces required')
            p=Peer(*paths,create=create);p.close();self.peer_paths=paths;self.auto=False;self.status.set('Room workspace open; sharing paused')
    def with_peer(self,action):
        from flockoff_collaboration.peer import Peer
        if not self.peer_paths:raise ValueError('Open a room workspace first')
        p=Peer(*self.peer_paths)
        try:return action(p)
        finally:p.close()
    def public_request(self):
        value=self.with_peer(lambda p:p.public_request());path=filedialog.asksaveasfilename(parent=self,title='Save public join request',defaultextension='.json')
        if path:private_write(path,json.dumps(value).encode());self.status.set('Public join request saved locally; deliver through a trusted channel')
    def import_invite(self):
        path=filedialog.askopenfilename(parent=self,title='Select invitation file')
        if not path:return
        from flockoff_collaboration.protocol import parse
        with open(path,'rb') as stream:packet=parse(stream.read(262145))
        preview=self.with_peer(lambda p:p.preview_invite(packet))
        if not messagebox.askyesno('Verify invitation',f"Room: {preview['room']}\nOwner fingerprint: {preview['authority_fingerprint']}\nEndpoint: {preview['endpoint']}\nAlias: {preview['alias']}\n\nHave you verified this fingerprint and delivery channel?",parent=self):return
        self.with_peer(lambda p:p.accept_invite(packet,fingerprint_confirmed=True));self.run_peer('join')
    def run_peer(self,operation):
        if self.busy:return
        if not self.peer_paths:raise ValueError('Open room workspace first')
        self.busy=True
        for widget,_ in self.controls:widget.configure(state='disabled')
        paths=self.peer_paths
        def worker():
            from flockoff_collaboration.peer import Peer
            from flockoff_collaboration.transport import Transport
            p=None
            try:
                p=Peer(*paths);inv=p.state['invitation']
                if not inv:raise ValueError('Import an invitation first')
                transport=Transport(inv['endpoint'])
                getattr(p,operation)(transport)
                self.results.put((True,p.status))
            except ConnectionError:self.results.put((False,'Room owner offline: saved locally, sync queued'))
            except Exception:self.results.put((False,'Sync suspended: verification or configuration failed; queued work retained'))
            finally:
                if p:p.close()
        threading.Thread(target=worker,daemon=True).start()
    def enable_sync(self):
        categories=[k for k,v in self.scopes.items() if v.get()]
        if not categories:raise ValueError('Select at least one bounded sharing scope')
        if not messagebox.askyesno('Enable room sharing','Automatically sync only queued cards in the selected categories while this window is open? Review text for private information first.',parent=self):return
        self.with_peer(lambda p:p.consent(categories,confirmed=True));self.auto=True;self.status.set('Automatic bounded room sync enabled while this window is open')
    def queue_card(self):
        card={'category':self.category.get(),'title':self.card_title.get(),'text':self.card.get('1.0','end-1c')}
        self.with_peer(lambda p:p.queue(card,object_id=self.edit_object,parents=self.edit_parents));self.edit_object=None;self.edit_parents=None;self.status.set('Selected card queued; private notebook not included')
    def open_owner(self):
        if self.owner_console and self.owner_console.winfo_exists():self.owner_console.lift();return
        self.owner_console=OwnerConsole(self)
    def received(self):
        events=self.with_peer(lambda p:[e for obj in {e['object_id'] for e in p.state['events'].values()} for e in p.heads(obj)])
        window=tk.Toplevel(self);window.title('Received current revisions — select branches explicitly');window.geometry('800x600')
        tree=ttk.Treeview(window,columns=('title','category','branch'),show='headings',selectmode='extended')
        for name in ('title','category','branch'):tree.heading(name,text=name.title())
        for e in events:tree.insert('', 'end',iid=e['event_id'],values=(e['payload']['title'],e['payload']['category'],e['event_id'][:12]))
        tree.pack(fill='both',expand=True)
        preview=tk.Text(window,height=12,wrap='word');preview.pack(fill='both',expand=True)
        def show(_=None):
            preview.configure(state='normal');preview.delete('1.0','end')
            for e in events:
                if e['event_id'] in tree.selection():preview.insert('end',e['payload']['title']+'\n'+e['payload']['text']+'\n\n')
            preview.configure(state='disabled')
        tree.bind('<<TreeviewSelect>>',show)
        def select(merge):
            chosen=select_branches(events,tree.selection(),merge)
            self.edit_object=chosen[0]['object_id'];self.edit_parents=[e['event_id'] for e in chosen]
            self.category.set(chosen[0]['payload']['category']);self.card_title.delete(0,'end');self.card_title.insert(0,chosen[0]['payload']['title'])
            self.card.delete('1.0','end')
            if not merge:self.card.insert('1.0',chosen[0]['payload']['text'])
            self.status.set('Compose and queue an explicit merge of selected branches' if merge else 'Editing selected branch; other branches remain separate')
            window.destroy()
        ttk.Button(window,text='Revise selected branch',command=lambda:self.safe(lambda:select(False))).pack()
        ttk.Button(window,text='Compose merge of selected branches',command=lambda:self.safe(lambda:select(True))).pack()
        ttk.Button(window,text='Close',command=window.destroy).pack()
    def sync(self):self.run_peer('sync')
    def pause(self):self.auto=False;self.with_peer(lambda p:p.pause());self.status.set('Sharing paused')
    def leave(self):
        if messagebox.askyesno('Leave room','Leave this room? Previously shared material cannot be recalled.',parent=self):self.auto=False;self.run_peer('leave')
    def poll(self):
        if self.closed:return
        try:
            _,status=self.results.get_nowait();self.busy=False;self.status.set(status)
            for w,state in self.controls:w.configure(state=state)
        except queue.Empty:pass
        self.timer=self.after(100,self.poll)
    def tick(self):
        if self.closed:return
        if self.auto and not self.busy:self.safe(self.sync)
        self.sync_timer=self.after(5000,self.tick)
    def open_variants(self):
        directory=filedialog.askdirectory(parent=self,title='Private variant custody directory')
        if not directory:return
        key=filedialog.askopenfilename(parent=self,title='Existing external Fernet key')
        if key:self.variant_store=VariantStore(directory,Path(key).read_bytes())
    def generate_preview(self):
        if not self.variant_store:raise ValueError('Open variant custody folder and key first')
        presenter=self.presenter.get().strip() if self.disclose.get() else None
        p=self.variant_store.create(self.document_category.get(),self.selected_text.get('1.0','end-1c'),self.source_reference.get(),unbranded=self.unbranded.get(),presenter=presenter,disclose_presenter=self.disclose.get())
        self.preview=p;window=tk.Toplevel(self);window.title('Exact bytes preview — review before approval');window.geometry('800x650')
        text=tk.Text(window,wrap='word');text.pack(fill='both',expand=True);text.insert('1.0',p.data.decode());text.configure(state='disabled')
        ttk.Label(window,text='SHA-256: '+p.sha256,wraplength=760).pack()
        reviewer=ttk.Entry(window);reviewer.pack();ttk.Label(window,text='Reviewer name (private approval record)').pack()
        consent=tk.BooleanVar(value=False);ttk.Checkbutton(window,text='I reviewed these exact bytes, disclosures and consent to local export',variable=consent).pack()
        def approve():
            self.variant_store.approve(p.reference,p.sha256,reviewer=reviewer.get(),consent=consent.get())
            self.status.set('Exact variant approved. Export copies these unchanged bytes.')
        def export():
            path=filedialog.asksaveasfilename(parent=window,title='Export unchanged approved variant',defaultextension='.txt')
            if path:self.variant_store.export(p.reference,p.sha256,path);self.status.set('Approved bytes exported locally; nothing sent')
        ttk.Button(window,text='Approve exact variant',command=lambda:self.safe(approve)).pack()
        ttk.Button(window,text='Export / reprint approved bytes',command=lambda:self.safe(export)).pack()
        ttk.Button(window,text='Close preview',command=window.destroy).pack()
    def close(self):
        self.auto=False
        if self.owner_console and self.owner_console.winfo_exists():
            self.owner_console.auto=False
            if self.owner_console.busy:self.after(100,self.close);return
            self.owner_console.close()
        if self.busy:self.status.set('Stopping: waiting for bounded sync to finish safely');self.after(100,self.close);return
        self.closed=True;self.after_cancel(self.timer);self.after_cancel(self.sync_timer);self.destroy()

def launch_workspace_paths(root):return WorkspacePaths(root)


def select_branches(events, selected, merge=False):
    chosen=[e for e in events if e['event_id'] in selected]
    if len(chosen)!=len(set(selected)) or (len(chosen)<2 if merge else len(chosen)!=1):
        raise ValueError('Select at least two branches to merge, or one branch to revise')
    if len({e['object_id'] for e in chosen})!=1:raise ValueError('Select branches of the same card')
    return chosen


class OwnerConsole(tk.Toplevel):
    """Separate local signer worker; never shares a SQLite connection with Tk."""
    def __init__(self,parent):
        super().__init__(parent);self.title('Room owner — local signing authority');self.geometry('800x650')
        self.experimental_notice=ttk.Label(self,text=EXPERIMENTAL_NOTICE,wraplength=760)
        self.experimental_notice.pack(fill='x',padx=10,pady=8)
        self.paths=None;self.busy=False;self.auto=False;self.closed=False;self.results=queue.Queue();self.controls=[]
        self.status=tk.StringVar(value='Owner service stopped. No startup network. Signing keys stay in this local vault.')
        self.endpoint=ttk.Entry(self,width=90);self.endpoint.pack(fill='x');ttk.Label(self,text='Provisioned Tor v3 onion relay endpoint (no direct fallback)').pack()
        for label,action in [('New owner vault',lambda:self.open(True)),('Open owner vault',lambda:self.open(False)),('Initialize from relay provision file',self.initialize),('Preview public request and issue invitation',self.invite),('Refresh members',lambda:self.run('list')),('Remove selected member',self.remove),('Start owner service while open',self.start),('Stop owner service',self.stop)]:
            b=ttk.Button(self,text=label,command=lambda a=action:self.safe(a));b.pack(anchor='w',padx=10,pady=2);self.controls.append(b)
        self.members=ttk.Treeview(self,columns=('alias','fingerprint'),show='headings',selectmode='browse')
        self.members.heading('alias',text='Room alias');self.members.heading('fingerprint',text='Signing fingerprint');self.members.pack(fill='both',expand=True)
        ttk.Label(self,textvariable=self.status,wraplength=760).pack(fill='x')
        ttk.Label(self,text='Removal blocks new grants, not copied history or an already authorized in-flight batch. Invitations expire in five minutes; membership changes invalidate pending invites.',wraplength=760).pack()
        self.protocol('WM_DELETE_WINDOW',self.close);self.timer=self.after(100,self.poll);self.tick_timer=self.after(2000,self.tick)
    def safe(self,fn):
        if self.busy:return
        try:fn()
        except Exception:messagebox.showerror('Owner action unavailable','Check selected files, endpoint and local configuration. No secret details are displayed.',parent=self)
    def open(self,create):
        path=(filedialog.asksaveasfilename if create else filedialog.askopenfilename)(parent=self,title='Owner vault file')
        if not path:return
        key=(filedialog.asksaveasfilename if create else filedialog.askopenfilename)(parent=self,title='Separate owner key file')
        if not key:return
        if getattr(self.master,'peer_paths',None) and Path(path).resolve()==Path(self.master.peer_paths[0]).resolve():raise ValueError('Separate owner vault required')
        self.paths=(path,key);self.auto=False;self.run('open',create=create)
    def read_file(self,title):
        from flockoff_collaboration.protocol import parse,MAX_BYTES
        path=filedialog.askopenfilename(parent=self,title=title)
        if not path:return None
        with open(path,'rb') as f:raw=f.read(MAX_BYTES+1)
        return parse(raw)
    def initialize(self):
        from flockoff_collaboration.transport import endpoint
        url=endpoint(self.endpoint.get().strip());provision=self.read_file('Select private relay provision file')
        if provision is not None:self.run('initialize',provision=provision,url=url)
    def invite(self):
        from flockoff_collaboration.protocol import member
        public=self.read_file('Select public join request')
        if public is None:return
        member(public);fp=hashlib.sha256(public['sign_public'].encode()).hexdigest()
        if not messagebox.askyesno('Verify requesting participant',f"Room alias: {public['alias']}\nSigning fingerprint: {fp}\nVerify the request delivery channel before inviting.",parent=self):return
        target=filedialog.asksaveasfilename(parent=self,title='Save sealed invitation',defaultextension='.json')
        if target:self.run('invite',public=public,target=target)
    def remove(self):
        selected=self.members.selection()
        if not selected:raise ValueError('Select a member')
        if messagebox.askyesno('Remove member','Block new grants to this member and invalidate pending invites? Already shared history cannot be recalled.',parent=self):self.run('remove',member=selected[0])
    def start(self):
        if not self.paths:raise ValueError('Open owner vault first')
        if messagebox.askyesno('Run local owner service','Poll the configured onion relay and authorize current member requests while this window is open?',parent=self):self.auto=True;self.run('pump')
    def stop(self):self.auto=False;self.status.set('Owner service stopped; peers will keep new sends queued locally')
    def run(self,action,**kwargs):
        if self.busy:return
        if not self.paths:raise ValueError('Open owner vault first')
        self.busy=True
        for b in self.controls:b.configure(state='disabled')
        self.endpoint.configure(state='disabled');paths=self.paths
        def worker():
            from flockoff_collaboration.owner import RoomOwner
            from flockoff_collaboration.transport import Transport
            owner=None
            try:
                owner=RoomOwner(*paths,create=kwargs.get('create',False))
                if action=='initialize':owner.initialize(kwargs['provision'],Transport(kwargs['url']),kwargs['url'])
                elif action=='invite':
                    packet=owner.make_invite(kwargs['public'],Transport(owner.state['endpoint']))
                    private_write(kwargs['target'],json.dumps(packet).encode())
                elif action=='pump':owner.pump(Transport(owner.state['endpoint']),limit=4)
                elif action=='remove':owner.remove(kwargs['member'])
                rows=[(m['sign_public'],m['alias'],hashlib.sha256(m['sign_public'].encode()).hexdigest()) for m in owner.roster()] if owner.state else []
                fp=hashlib.sha256(owner.state['identity']['sign_public'].encode()).hexdigest() if owner.state else 'Initialize this new vault using an existing relay provision file'
                self.results.put((True,rows,'Owner fingerprint: '+fp))
            except ConnectionError:self.results.put((False,[], 'Owner relay unavailable: local state retained; no direct fallback'))
            except Exception:self.results.put((False,[], 'Owner action failed: verify local setup and files; no secret details displayed'))
            finally:
                if owner:owner.close()
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        if self.closed:return
        try:
            ok,rows,status=self.results.get_nowait();self.busy=False;self.status.set(status)
            if ok:
                self.members.delete(*self.members.get_children())
                for key,alias,fp in rows:self.members.insert('', 'end',iid=key,values=(alias,fp))
            for b in self.controls:b.configure(state='normal')
            self.endpoint.configure(state='normal')
        except queue.Empty:pass
        self.timer=self.after(100,self.poll)
    def tick(self):
        if self.closed:return
        if self.auto and not self.busy:self.run('pump')
        self.tick_timer=self.after(2000,self.tick)
    def close(self):
        self.auto=False
        if self.busy:self.after(100,self.close);return
        self.closed=True;self.after_cancel(self.timer);self.after_cancel(self.tick_timer);self.destroy()
