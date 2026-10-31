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
        messagebox.showinfo(
            'Atelpix data location',
            f'Database path:\n{self.store.path}\n\nDatabase exists: {self.store.initialized}'
        )
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
        def reset_authenticator():
            password=p.get()
            if not password:
                messagebox.showwarning('Owner password required','Enter your Owner password first.')
                return
            try:
                self.store.unlock(password)
            except Exception as e:
                messagebox.showerror('Verification failed',str(e))
                return
            if not messagebox.askyesno('Reset Authenticator','This will replace the lost Authenticator setup and invalidate all old recovery codes. Your client database will be backed up first. Continue?'):
                self.store.close()
                return
            try:
                folder=APP_DIR/'Backups'
                folder.mkdir(parents=True,exist_ok=True)
                backup_path=folder/f'Atelpix_Before_Authenticator_Reset_{datetime.now():%Y%m%d_%H%M%S}.atbak'
                self.store.backup(backup_path)
                secret,codes=self.store.reset_authenticator()
                messagebox.showinfo('Authenticator reset','Backup created at:\\n'+str(backup_path)+'\\n\\nAdd this new secret to your Authenticator App:\\n\\n'+secret+'\\n\\nSave these new one-time recovery codes securely:\\n\\n'+'\\n'.join(codes)+'\\n\\nThe old Authenticator code and recovery codes will no longer work.')
                self.store.close()
                self.show_login()
            except Exception as e:
                try: self.store.close()
                except Exception: pass
                messagebox.showerror('Reset failed','Authenticator reset could not be completed.\\n\\n'+str(e))
        self.btn(c,'UNLOCK DASHBOARD',proceed,True).pack(fill='x')
        self.label(c,'Forgot password? There is no cloud reset. Use a valid recovery plan and keep your backups safe.',8,MUTED,wraplength=330).pack(pady=(14,0))

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
\n
