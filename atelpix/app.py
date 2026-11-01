from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import shutil, time, os, sys
from .store import LocalStore, APP_DIR, LOGO_PATH
from .security import SecurityError
from .lan_server import LANReadOnlyServer

BG='#171d31'; PANEL='#222b43'; PANEL2='#2b3651'; TEXT='#e9efff'; MUTED='#9ba8c3'; ORANGE='#20d5d4'; GREEN='#51e3c2'; RED='#ff9da5'
FIELDS=[('name','Client / Company Name'),('country','Country'),('city','City'),('timezone','Time Zone (IANA)'),('email','Email Address'),('whatsapp','WhatsApp Number'),('phone','Phone Number'),('website','Website'),('notes','Notes'),('status','Client Status')]

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Atelpix Secure Client Dashboard'); self.geometry('1180x760'); self.minsize(960,620); self.configure(bg=BG)
        self.store=LocalStore(); self.lan_server=None; self.unlocked=False; self.last_activity=time.monotonic(); self.time_format='24h'; self.logo_img=None
        self.style=ttk.Style(self); self.style.theme_use('clam'); self._style(); self.protocol('WM_DELETE_WINDOW', self.close_app)
        self.bind_all('<KeyPress>',self._activity); self.bind_all('<Button>',self._activity)
        self.show_setup_or_login()

    def _style(self):
        self.style.configure('Treeview',background=PANEL,foreground=TEXT,fieldbackground=PANEL,rowheight=30,borderwidth=0)
        self.style.configure('Treeview.Heading',background=PANEL2,foreground=TEXT,font=('Segoe UI',9,'bold'))
        self.style.map('Treeview',background=[('selected',ORANGE)],foreground=[('selected','#ffffff')])
        self.style.configure('TCombobox',fieldbackground=PANEL2,background=PANEL2,foreground=TEXT)

    def _activity(self,event=None): self.last_activity=time.monotonic()
    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def panel(self,parent,**kw): return tk.Frame(parent,bg=PANEL,highlightthickness=1,highlightbackground='#2a303a',**kw)
    def label(self,parent,text,size=10,color=TEXT,bold=False,**kw): return tk.Label(parent,text=text,bg=kw.pop('bg',PANEL),fg=color,font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)
    def entry(self,parent,show=None):
        e=tk.Entry(parent,bg=PANEL2,fg=TEXT,insertbackground=TEXT,relief='flat',font=('Segoe UI',10),show=show); e.configure(highlightthickness=1,highlightbackground='#343b47',highlightcolor=ORANGE); return e
    def btn(self,parent,text,cmd,primary=False):
        return tk.Button(parent,text=text,command=cmd,bg=ORANGE if primary else PANEL2,fg='white',activebackground='#ef7a16',activeforeground='white',relief='flat',bd=0,padx=14,pady=9,cursor='hand2',font=('Segoe UI',9,'bold'))

    def show_setup_or_login(self):
        # Start directly at password login; do not show an informational popup.
        if self.store.initialized:
            self.show_login()
        else:
            self.show_setup()

    def auth_shell(self,title,subtitle):
        self.clear(); wrap=tk.Frame(self,bg=BG); wrap.place(relx=.5,rely=.5,anchor='center')
        self.label(wrap,'ATELPIX',24,ORANGE,True,bg=BG).pack(pady=(0,8))
        self.label(wrap,title,18,TEXT,True,bg=BG).pack()
        self.label(wrap,subtitle,9,MUTED,bg=BG).pack(pady=(5,20))
        card=self.panel(wrap,padx=28,pady=25); card.pack(fill='x'); return card

    def show_setup(self):
        c=self.auth_shell('Create Owner Account','First-time setup · This PC only · Offline')
        self.label(c,'Owner password (minimum 12 characters)',9,MUTED).pack(anchor='w')
        p=self.entry(c,show='●'); p.pack(fill='x',pady=(5,14),ipady=8)
        self.label(c,'Confirm password',9,MUTED).pack(anchor='w')
        p2=self.entry(c,show='●'); p2.pack(fill='x',pady=(5,14),ipady=8)
        self.label(c,'Security email (for your records only; no email is sent)',9,MUTED).pack(anchor='w')
        em=self.entry(c); em.insert(0,'kamruzzaman.upk@gmail.com'); em.pack(fill='x',pady=(5,18),ipady=8)
        def create():
            if p.get()!=p2.get(): messagebox.showerror('Setup','Passwords do not match.'); return
            try:
                self.store.setup(p.get())
                self.store.set_meta('security_email',em.get().strip())
                messagebox.showinfo('Setup complete','Owner account created. Sign in using your Owner password.')
                self.store.close(); self.show_login()
            except Exception as e: messagebox.showerror('Setup failed',str(e))
        self.btn(c,'CREATE OWNER ACCOUNT',create,True).pack(fill='x')
        self.label(c,'No network connection or online account is used.',8,MUTED).pack(pady=(15,0))

    def show_login(self):
        c=self.auth_shell('Owner Login','Encrypted local database · Password protected')
        self.label(c,'Owner password',9,MUTED).pack(anchor='w'); p=self.entry(c,show='●'); p.pack(fill='x',pady=(5,15),ipady=8)
        def proceed():
            try: self.store.unlock(p.get())
            except Exception as e: messagebox.showerror('Login failed',str(e)); return
            self.unlocked=True; self.time_format=self.store.meta('time_format') or '24h'; self.show_main(); self.check_backup_due(); self.tick()
        self.btn(c,'UNLOCK DASHBOARD',proceed,True).pack(fill='x')
        self.label(c,'Enter your Owner password to open your dashboard.',8,MUTED,wraplength=330).pack(pady=(14,0))

    def show_main(self):
        self.clear(); self.configure(bg=BG)
        self.sidebar=tk.Frame(self,bg='#192238',width=185,highlightthickness=1,highlightbackground='#3a4661')
        self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        logo_area=tk.Frame(self.sidebar,bg='#192238'); logo_area.pack(fill='x',padx=16,pady=(22,28))
        self.logo_label=tk.Label(logo_area,text='✦  ATELPIX',fg=ORANGE,bg='#192238',font=('Segoe UI',16,'bold')); self.logo_label.pack(anchor='w')
        self.label(logo_area,'SECURE CLIENT DASHBOARD',7,MUTED,bg='#192238').pack(anchor='w',padx=4,pady=(5,0))
        if LOGO_PATH.exists(): self.load_logo()
        self.nav_buttons=[]
        for name,fn in [('Overview',self.dashboard),('Client Management',self.clients_page),('World Clocks',self.clocks_page),('Activity Log',self.activity_page),('Backup & Restore',self.backup_page),('Settings',self.settings_page)]:
            b=tk.Button(self.sidebar,text='  '+name,command=lambda f=fn,n=name:self.navigate(f,n),anchor='w',bg='#192238',fg='#aeb9d0',activebackground='#35415b',activeforeground='white',relief='flat',bd=0,padx=13,pady=12,font=('Segoe UI',9))
            b.pack(fill='x',padx=8,pady=2); self.nav_buttons.append((name,b))
        tk.Frame(self.sidebar,bg='#3a4661',height=1).pack(fill='x',pady=15)
        self.label(self.sidebar,'ATELPIX SECURE DASHBOARD\\nOwner Workspace\\nVersion 1.1.0',8,MUTED,bg='#192238',justify='left').pack(side='bottom',anchor='w',padx=14,pady=(0,14))
        self.btn(self.sidebar,'LOCK SESSION',self.lock).pack(side='bottom',fill='x',padx=12,pady=12)
        shell=tk.Frame(self,bg=BG); shell.pack(side='left',fill='both',expand=True)
        top=tk.Frame(shell,bg=BG,height=55,highlightthickness=1,highlightbackground='#3a4661'); top.pack(fill='x'); top.pack_propagate(False)
        self.top_search=self.entry(top); self.top_search.pack(side='left',fill='x',expand=True,padx=22,pady=11)
        self.top_search.insert(0,'Search clients, pages...')
        self.label(top,'OWNER WORKSPACE',9,ORANGE,True,bg=BG).pack(side='right',padx=22)
        self.main=tk.Frame(shell,bg=BG); self.main.pack(side='left',fill='both',expand=True,padx=25,pady=22)
        self.navigate(self.dashboard,'Overview')

    def navigate(self,fn,name):
        for n,b in self.nav_buttons:
            b.configure(bg='#35415b' if n==name else '#192238',fg='white' if n==name else '#aeb9d0')
        fn()

    def page_head(self,title,sub):
        self.clock_labels=[]; self.clock_tree=None
        for w in self.main.winfo_children(): w.destroy()
        self.label(self.main,title,22,TEXT,True,bg=BG).pack(anchor='w')
        self.label(self.main,sub,9,MUTED,bg=BG).pack(anchor='w',pady=(4,18))

    def metric(self,parent,title,value):
        c=self.panel(parent,padx=18,pady=15); self.label(c,title.upper(),8,MUTED,bg=PANEL, bold=True).pack(anchor='w'); self.label(c,str(value),25,TEXT,True,bg=PANEL).pack(anchor='w',pady=(7,0)); return c

    def dashboard(self):
        self.page_head('Client Management','Manage your clients and track your global business activity.')
        clients=self.store.conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
        active=self.store.conn.execute("SELECT COUNT(*) FROM clients WHERE status='Active'").fetchone()[0]
        prospects=self.store.conn.execute("SELECT COUNT(*) FROM clients WHERE status='Prospect'").fetchone()[0]
        inactive=self.store.conn.execute("SELECT COUNT(*) FROM clients WHERE status='Inactive'").fetchone()[0]
        projects=0
        top=tk.Frame(self.main,bg=BG); top.pack(fill='x',pady=(0,18))
        recent=self.panel(top,padx=12,pady=10); recent.pack(side='left',fill='both',expand=True,padx=(0,10))
        self.label(recent,'RECENT CLIENT RECORDS',9,ORANGE,True).pack(anchor='w',pady=(0,8))
        tree=ttk.Treeview(recent,columns=('name','country','email','status'),show='headings',height=5)
        for c,w in [('name',155),('country',95),('email',180),('status',85)]: tree.heading(c,text=c.upper()); tree.column(c,width=w,anchor='w')
        for r in self.store.list_clients()[:6]: tree.insert('','end',values=(r[1],r[2],r[5],r[10]))
        tree.pack(fill='both',expand=True)
        cards=tk.Frame(top,bg=BG); cards.pack(side='left',fill='y')
        for title,value,desc in [('Active Clients',active,'Currently active customers'),('All Clients',clients,'Saved client records')]:
            c=self.panel(cards,padx=15,pady=13); c.pack(fill='x',pady=(0,9))
            self.label(c,title,10,TEXT,True,bg=PANEL).pack(anchor='w')
            self.label(c,str(value),24,TEXT,True,bg=PANEL).pack(anchor='w',pady=4)
            self.label(c,desc,8,MUTED,bg=PANEL).pack(anchor='w')
            self.btn(c,'VIEW CLIENTS',self.clients_page,True).pack(anchor='w',pady=(8,0))
        middle=tk.Frame(self.main,bg=BG); middle.pack(fill='x',pady=(0,18))
        left=tk.Frame(middle,bg=BG); left.pack(side='left',fill='both',expand=True,padx=(0,10))
        self.label(left,'CLIENT OVERVIEW',12,TEXT,True,bg=BG).pack(anchor='w',pady=(0,10))
        metrics=tk.Frame(left,bg=BG); metrics.pack(fill='x')
        for title,value,desc in [('Total Client Records',clients,'Client database overview'),('Potential Clients',prospects,'Leads and prospects'),('World Clock Locations',len(self.store.clocks()),'Configured time zones'),('Workspace Status','Ready','Owner workspace')]:
            c=self.panel(metrics,padx=12,pady=12); c.pack(side='left',fill='both',expand=True,padx=4,pady=4)
            self.label(c,title,8,MUTED,bg=PANEL).pack(anchor='w')
            self.label(c,str(value),19,TEXT,True,bg=PANEL).pack(anchor='w',pady=7)
            self.label(c,desc,7,MUTED,bg=PANEL).pack(anchor='w')
        insight=self.panel(left,padx=14,pady=12); insight.pack(fill='x',pady=(10,0))
        self.label(insight,'CLIENT STATUS OVERVIEW',9,ORANGE,True).pack(anchor='w')
        bar=tk.Frame(insight,bg='#35415d',height=13); bar.pack(fill='x',pady=12); bar.pack_propagate(False)
        total=max(clients,1)
        for val,col in [(active,ORANGE),(prospects,'#6f8cff'),(inactive,'#e98d9c')]:
            tk.Frame(bar,bg=col,width=max(1,int(600*val/total))).pack(side='left',fill='y')
        self.label(insight,f'Active: {active}     Potential: {prospects}     Inactive: {inactive}',8,MUTED).pack(anchor='w')
        right=self.panel(middle,padx=15,pady=14); right.pack(side='left',fill='both',expand=True)
        self.label(right,'WORLD CLOCKS',12,TEXT,True).pack(anchor='w',pady=(0,10))
        self.clock_labels=[]
        for cid,city,country,tz in self.store.clocks()[:5]:
            line=tk.Frame(right,bg=PANEL); line.pack(fill='x',pady=6)
            self.label(line,f'{city}, {country}',9,TEXT,bg=PANEL).pack(side='left')
            v=self.label(line,'--:--:--',10,ORANGE,True,bg=PANEL); v.pack(side='right'); self.clock_labels.append((v,tz))
        foot=self.panel(self.main,padx=14,pady=12); foot.pack(fill='x')
        self.label(foot,'SECURITY & BACKUP',9,ORANGE,True).pack(anchor='w')
        self.label(foot,'Encrypted local database  •  Owner password login  •  Data stored on this PC',8,MUTED).pack(anchor='w',pady=6)
        row=tk.Frame(foot,bg=PANEL); row.pack(fill='x')
        self.btn(row,'ADD CLIENT',lambda:self.client_form(),True).pack(side='left')
        self.btn(row,'BACKUP NOW',self.backup_now).pack(side='left',padx=8)
    def backup_page(self):
        self.page_head('Backup & Restore','Create encrypted backups and safely restore your Atelpix database')
        box=self.panel(self.main,padx=20,pady=18); box.pack(fill='x',pady=8)
        self.label(box,'ENCRYPTED DATABASE BACKUP',12,ORANGE,True).pack(anchor='w')
        self.label(box,'Your existing client records remain encrypted. Backups are saved in the local Atelpix Backups folder.',9,MUTED,bg=PANEL,wraplength=700).pack(anchor='w',pady=10)
        self.btn(box,'CREATE BACKUP NOW',self.backup_now,True).pack(anchor='w',pady=5)
        box2=self.panel(self.main,padx=20,pady=18); box2.pack(fill='x',pady=8)
        self.label(box2,'RESTORE FROM BACKUP',12,ORANGE,True).pack(anchor='w')
        self.label(box2,'Restore replaces current data. Make a fresh backup first and check the selected backup carefully.',9,MUTED,bg=PANEL).pack(anchor='w',pady=10)
        self.btn(box2,'RESTORE ENCRYPTED BACKUP',self.restore_backup).pack(anchor='w')
        box3=self.panel(self.main,padx=20,pady=18); box3.pack(fill='x',pady=8)
        self.label(box3,'BACKUP LOCATION',10,TEXT,True).pack(anchor='w')
        self.label(box3,str(APP_DIR/'Backups'),8,MUTED,bg=PANEL).pack(anchor='w',pady=8)
        self.btn(box3,'OPEN DATA FOLDER',lambda:os.startfile(APP_DIR) if os.name=='nt' else messagebox.showinfo('Data folder',str(APP_DIR))).pack(anchor='w')


    # --- Missing application workflows restored in the final desktop build ---
    def close_app(self):
        try:
            if self.lan_server:
                self.lan_server.stop()
                self.lan_server = None
            if self.store.conn is not None:
                self.store.close()
        except Exception as exc:
            messagebox.showerror('Close failed', str(exc))
        self.destroy()

    def lock(self):
        if self.lan_server:
            try: self.lan_server.stop()
            except Exception: pass
            self.lan_server = None
        try:
            if self.store.conn is not None: self.store.close()
        finally:
            self.unlocked = False
            self.show_login()

    def check_backup_due(self):
        # No startup popup: the Backup page always shows the current backup location.
        return self.store.backup_due()

    def tick(self):
        if not self.winfo_exists() or not self.unlocked: return
        if time.monotonic() - self.last_activity > 15 * 60:
            messagebox.showinfo('Session locked', 'Your dashboard was locked after 15 minutes of inactivity.')
            self.lock()
            return
        for widget, tz in getattr(self, 'clock_labels', []):
            try: widget.configure(text=datetime.now(ZoneInfo(tz)).strftime('%H:%M:%S'))
            except Exception: widget.configure(text='--:--:--')
        self.after(1000, self.tick)

    def load_logo(self):
        try:
            from PIL import Image, ImageTk
            image = Image.open(LOGO_PATH).convert('RGBA')
            image.thumbnail((145, 58))
            self.logo_img = ImageTk.PhotoImage(image)
            self.logo_label.configure(image=self.logo_img, text='')
        except Exception:
            # A missing or invalid optional logo must never prevent startup.
            self.logo_img = None

    def clients_page(self):
        self.page_head('Client Management', 'Add, search, update and organize your client records.')
        toolbar = tk.Frame(self.main, bg=BG); toolbar.pack(fill='x', pady=(0, 12))
        search = self.entry(toolbar); search.pack(side='left', fill='x', expand=True, padx=(0, 8))
        search.insert(0, 'Search name, country, city, email or phone')
        status = ttk.Combobox(toolbar, values=['All','Active','Prospect','Inactive'], state='readonly', width=13)
        status.set('All'); status.pack(side='left', padx=5)
        body = self.panel(self.main, padx=10, pady=10); body.pack(fill='both', expand=True)
        cols = ('id','name','country','city','email','phone','status')
        tree = ttk.Treeview(body, columns=cols, show='headings')
        widths = {'id':45,'name':180,'country':110,'city':110,'email':190,'phone':120,'status':90}
        for col in cols:
            tree.heading(col, text=col.upper()); tree.column(col, width=widths[col], anchor='w')
        tree.pack(fill='both', expand=True)
        def refresh(*_):
            tree.delete(*tree.get_children())
            for row in self.store.list_clients(search.get() if not search.get().startswith('Search name') else '', status.get()):
                tree.insert('', 'end', iid=str(row[0]), values=(row[0],row[1],row[2],row[3],row[5],row[7],row[10]))
        def selected_id():
            chosen = tree.selection()
            if not chosen:
                messagebox.showwarning('Select client','Please select a client record first.')
                return None
            return int(chosen[0])
        def edit():
            cid=selected_id()
            if cid is not None: self.client_form(cid, refresh)
        def delete():
            cid=selected_id()
            if cid is None: return
            if messagebox.askyesno('Delete client','Delete the selected client record? This cannot be undone.'):
                self.store.delete_client(cid); refresh()
        actions=tk.Frame(self.main,bg=BG); actions.pack(fill='x',pady=(10,0))
        self.btn(actions,'ADD CLIENT',lambda:self.client_form(None,refresh),True).pack(side='left')
        self.btn(actions,'EDIT SELECTED',edit).pack(side='left',padx=7)
        self.btn(actions,'DELETE SELECTED',delete).pack(side='left')
        self.btn(actions,'REFRESH',refresh).pack(side='right')
        search.bind('<KeyRelease>', refresh); status.bind('<<ComboboxSelected>>', refresh)
        tree.bind('<Double-1>', lambda _e: edit())
        refresh()

    def client_form(self, client_id=None, on_saved=None):
        existing = None
        if client_id is not None:
            existing = self.store.conn.execute('SELECT * FROM clients WHERE id=?',(client_id,)).fetchone()
            if not existing: messagebox.showerror('Client','Selected client no longer exists.'); return
        win=tk.Toplevel(self); win.title('Edit Client' if existing else 'Add Client'); win.configure(bg=BG)
        win.transient(self); win.grab_set(); win.geometry('560x680')
        outer=tk.Frame(win,bg=BG,padx=22,pady=18); outer.pack(fill='both',expand=True)
        self.label(outer,'Edit Client Record' if existing else 'New Client Record',17,TEXT,True,bg=BG).pack(anchor='w',pady=(0,12))
        values = {}
        for key, caption in FIELDS:
            self.label(outer,caption,9,MUTED,bg=BG).pack(anchor='w',pady=(6,2))
            if key == 'status':
                widget=ttk.Combobox(outer,values=['Active','Prospect','Inactive'],state='readonly')
                widget.set((existing[10] if existing else 'Active') or 'Active')
            elif key == 'notes':
                widget=tk.Text(outer,height=3,bg=PANEL2,fg=TEXT,insertbackground=TEXT,relief='flat')
                if existing and existing[9]: widget.insert('1.0',existing[9])
            else:
                widget=self.entry(outer)
                index={'name':1,'country':2,'city':3,'timezone':4,'email':5,'whatsapp':6,'phone':7,'website':8}[key]
                if existing and existing[index]: widget.insert(0,existing[index])
                elif key=='timezone': widget.insert(0,'UTC')
            widget.pack(fill='x',ipady=5 if key!='notes' else 0)
            values[key]=widget
        def save():
            data={}
            for key, widget in values.items():
                data[key]=widget.get('1.0','end-1c').strip() if key=='notes' else widget.get().strip()
            try:
                self.store.save_client(data,client_id)
                if on_saved: on_saved()
                win.destroy()
            except Exception as exc: messagebox.showerror('Save client',str(exc),parent=win)
        self.btn(outer,'SAVE CLIENT',save,True).pack(fill='x',pady=15)

    def clocks_page(self):
        self.page_head('World Clocks','Manage the time zones shown in your workspace.')
        box=self.panel(self.main,padx=14,pady=14); box.pack(fill='x')
        tree=ttk.Treeview(box,columns=('city','country','timezone'),show='headings',height=10)
        for c,w in [('city',180),('country',180),('timezone',260)]:
            tree.heading(c,text=c.upper()); tree.column(c,width=w,anchor='w')
        tree.pack(fill='x')
        def refresh():
            tree.delete(*tree.get_children())
            for row in self.store.clocks(): tree.insert('','end',iid=str(row[0]),values=row[1:])
        def add():
            city=simpledialog.askstring('Add clock','City name:',parent=self)
            if not city: return
            country=simpledialog.askstring('Add clock','Country:',parent=self) or ''
            tz=simpledialog.askstring('Add clock','IANA time zone (e.g. Europe/Paris):',parent=self)
            if not tz: return
            try: self.store.add_clock(city,country,tz); refresh()
            except Exception as exc: messagebox.showerror('Add clock',str(exc))
        def remove():
            chosen=tree.selection()
            if not chosen: messagebox.showwarning('Remove clock','Select a clock first.'); return
            self.store.delete_clock(int(chosen[0])); refresh()
        actions=tk.Frame(self.main,bg=BG); actions.pack(fill='x',pady=10)
        self.btn(actions,'ADD TIME ZONE',add,True).pack(side='left')
        self.btn(actions,'REMOVE SELECTED',remove).pack(side='left',padx=8)
        refresh()

    def activity_page(self):
        self.page_head('Activity Log','Recent actions recorded in your encrypted local database.')
        box=self.panel(self.main,padx=10,pady=10); box.pack(fill='both',expand=True)
        tree=ttk.Treeview(box,columns=('time','event','detail'),show='headings')
        for c,w in [('time',210),('event',190),('detail',430)]:
            tree.heading(c,text=c.upper()); tree.column(c,width=w,anchor='w')
        tree.pack(fill='both',expand=True)
        for at,event,detail in self.store.audit_events(250):
            tree.insert('','end',values=(at.replace('T',' ')[:19],event,detail))

    def settings_page(self):
        self.page_head('Settings','Owner security, local storage and optional team access.')
        account=self.panel(self.main,padx=16,pady=14); account.pack(fill='x',pady=(0,12))
        self.label(account,'OWNER PASSWORD',11,ORANGE,True).pack(anchor='w')
        self.label(account,'Change the password used to unlock this encrypted database.',9,MUTED).pack(anchor='w',pady=7)
        def change_password():
            old=simpledialog.askstring('Change password','Current Owner password:',show='●',parent=self)
            if old is None: return
            new=simpledialog.askstring('Change password','New password (minimum 12 characters):',show='●',parent=self)
            if new is None: return
            confirm=simpledialog.askstring('Change password','Confirm new password:',show='●',parent=self)
            if confirm is None: return
            if new!=confirm: messagebox.showerror('Password','New passwords do not match.'); return
            try: self.store.change_password(old,new); messagebox.showinfo('Password','Owner password updated.')
            except Exception as exc: messagebox.showerror('Password',str(exc))
        self.btn(account,'CHANGE OWNER PASSWORD',change_password,True).pack(anchor='w',pady=5)
        lan=self.panel(self.main,padx=16,pady=14); lan.pack(fill='x',pady=(0,12))
        self.label(lan,'OPTIONAL TEAM READ-ONLY ACCESS',11,ORANGE,True).pack(anchor='w')
        self.label(lan,'Only use on a trusted private Wi-Fi/LAN. Team access exposes client details to connected viewers.',9,MUTED,bg=PANEL,wraplength=720).pack(anchor='w',pady=8)
        def start_lan():
            try:
                if not self.lan_server: self.lan_server=LANReadOnlyServer(self.store)
                info=self.lan_server.start()
                messagebox.showinfo('Team LAN Access',f"URL: {info['url']}\n\nAccess token:\n{info['token']}\n\nCertificate SHA-256:\n{info['fingerprint']}\n\nShare only with authorized team members over a trusted channel.")
            except Exception as exc: messagebox.showerror('Team LAN Access',str(exc))
        def stop_lan():
            if self.lan_server:
                self.lan_server.stop(); self.lan_server=None
                messagebox.showinfo('Team LAN Access','Team access stopped. The previous token is no longer valid.')
        self.btn(lan,'START / VIEW TEAM LAN ACCESS',start_lan,True).pack(anchor='w',pady=5)
        self.btn(lan,'STOP TEAM LAN ACCESS',stop_lan).pack(anchor='w',pady=5)
        storage=self.panel(self.main,padx=16,pady=14); storage.pack(fill='x')
        self.label(storage,'LOCAL DATA FILE',10,TEXT,True).pack(anchor='w')
        self.label(storage,str(APP_DIR/'clients.atdb'),8,MUTED,bg=PANEL).pack(anchor='w',pady=7)
        self.btn(storage,'OPEN DATA FOLDER',lambda:os.startfile(APP_DIR) if os.name=='nt' else messagebox.showinfo('Data folder',str(APP_DIR))).pack(anchor='w')

    def backup_now(self):
        try:
            folder=APP_DIR/'Backups'; folder.mkdir(parents=True,exist_ok=True)
            path=folder/f"Atelpix-Backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.atbak"
            self.store.backup(path)
            messagebox.showinfo('Backup complete',f'Encrypted backup saved to:\n{path}')
        except Exception as exc: messagebox.showerror('Backup failed',str(exc))

    def restore_backup(self):
        source=filedialog.askopenfilename(parent=self,title='Select Atelpix encrypted backup',filetypes=[('Atelpix backup','*.atbak'),('All files','*.*')])
        if not source: return
        backup_password=simpledialog.askstring('Restore backup','Password used when this backup was created:',show='●',parent=self)
        if backup_password is None: return
        current_password=simpledialog.askstring('Restore backup','Current Owner password:',show='●',parent=self)
        if current_password is None: return
        if not messagebox.askyesno('Confirm restore','This replaces the current client data. Continue?',parent=self): return
        try:
            self.store.restore(Path(source),backup_password,current_password)
            messagebox.showinfo('Restore complete','Backup restored successfully. The dashboard will refresh.')
            self.dashboard()
        except Exception as exc: messagebox.showerror('Restore failed',str(exc))
