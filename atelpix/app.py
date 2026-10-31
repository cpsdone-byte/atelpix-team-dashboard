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

BG='#111318'; PANEL='#191d24'; PANEL2='#202630'; TEXT='#f1f3f5'; MUTED='#a6adb8'; ORANGE='#D46605'; GREEN='#43b581'; RED='#e05b5b'
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
        if self.store.initialized: self.show_login()
        else: self.show_setup()

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
                secret=self.store.setup(p.get()); codes=self.store.generate_recovery_codes()
                self.store.set_meta('security_email',em.get().strip())
                uri=f'otpauth://totp/Atelpix:Owner?secret={secret}&issuer=Atelpix&algorithm=SHA1&digits=6&period=30'
                messagebox.showinfo('Authenticator setup',f'Add this secret manually in your Authenticator App:\n\n{secret}\n\nAccount URI:\n{uri}\n\nSave these one-time recovery codes securely now:\n\n'+'\n'.join(codes)+'\n\nThey will not be shown again.')
                self.store.close(); self.show_login()
            except Exception as e: messagebox.showerror('Setup failed',str(e))
        self.btn(c,'CREATE OWNER ACCOUNT',create,True).pack(fill='x')
        self.label(c,'No network connection or online account is used.',8,MUTED).pack(pady=(15,0))

    def show_login(self):
        c=self.auth_shell('Owner Login','Encrypted local database · Offline')
        self.label(c,'Owner password',9,MUTED).pack(anchor='w'); p=self.entry(c,show='●'); p.pack(fill='x',pady=(5,15),ipady=8)
        def proceed():
            try: self.store.unlock(p.get())
            except Exception as e: messagebox.showerror('Login failed',str(e)); return
            code=simpledialog.askstring('Two-factor authentication','Enter your 6-digit Authenticator code.\nFor recovery, enter a one-time recovery code.',parent=self)
            if not code: self.store.close(); return
            recovery='-' in code or len(''.join(x for x in code if x.isalnum()))>6
            if not self.store.verify_second_factor(code,recovery):
                messagebox.showerror('Verification failed','Invalid or already-used verification code.'); self.store.close(); self.show_login(); return
            self.unlocked=True; self.time_format=self.store.meta('time_format') or '24h'; self.show_main(); self.check_backup_due(); self.tick()
        self.btn(c,'UNLOCK DASHBOARD',proceed,True).pack(fill='x')
        self.label(c,'Forgot password? There is no cloud reset. Use a valid recovery plan and keep your backups safe.',8,MUTED,wraplength=330).pack(pady=(14,0))

    def show_main(self):
        self.clear(); self.configure(bg=BG)
        self.sidebar=tk.Frame(self,bg='#0d0f13',width=220); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        logo_area=tk.Frame(self.sidebar,bg='#0d0f13'); logo_area.pack(fill='x',padx=18,pady=(22,25))
        self.logo_label=tk.Label(logo_area,text='ATELPIX',fg=ORANGE,bg='#0d0f13',font=('Segoe UI',19,'bold')); self.logo_label.pack(anchor='w')
        self.label(logo_area,'SECURE CLIENT DASHBOARD',7,MUTED,bg='#0d0f13').pack(anchor='w')
        if LOGO_PATH.exists(): self.load_logo()
        for name,fn in [('Dashboard',self.dashboard),('Clients',self.clients_page),('World Clocks',self.clocks_page),('Activity Log',self.activity_page),('Settings',self.settings_page)]:
            tk.Button(self.sidebar,text='  '+name,command=fn,anchor='w',bg='#0d0f13',fg=TEXT,activebackground=PANEL2,activeforeground=ORANGE,relief='flat',bd=0,padx=17,pady=13,font=('Segoe UI',10)).pack(fill='x')
        tk.Frame(self.sidebar,bg='#2a303a',height=1).pack(fill='x',pady=15)
        self.btn(self.sidebar,'LOCK SESSION',self.lock).pack(fill='x',padx=14,side='bottom',pady=18)
        self.main=tk.Frame(self,bg=BG); self.main.pack(side='left',fill='both',expand=True,padx=26,pady=24)
        self.dashboard()

    def page_head(self,title,sub):
        self.clock_labels=[]; self.clock_tree=None
        for w in self.main.winfo_children(): w.destroy()
        self.label(self.main,title,22,TEXT,True,bg=BG).pack(anchor='w')
        self.label(self.main,sub,9,MUTED,bg=BG).pack(anchor='w',pady=(4,18))

    def metric(self,parent,title,value):
        c=self.panel(parent,padx=18,pady=15); self.label(c,title.upper(),8,MUTED,bg=PANEL, bold=True).pack(anchor='w'); self.label(c,str(value),25,TEXT,True,bg=PANEL).pack(anchor='w',pady=(7,0)); return c

    def dashboard(self):
        self.page_head('Dashboard','Your private Atelpix workspace · Stored on this PC only')
        row=tk.Frame(self.main,bg=BG); row.pack(fill='x')
        clients=self.store.conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
        self.metric(row,'Total Clients',clients).pack(side='left',fill='x',expand=True,padx=(0,10))
        self.metric(row,'World Clocks',len(self.store.clocks())).pack(side='left',fill='x',expand=True,padx=10)
        due='Backup due' if self.store.backup_due() else 'Up to date'
        self.metric(row,'Backup Status',due).pack(side='left',fill='x',expand=True,padx=(10,0))
        mid=tk.Frame(self.main,bg=BG); mid.pack(fill='both',expand=True,pady=18)
        left=self.panel(mid,padx=18,pady=16); left.pack(side='left',fill='both',expand=True,padx=(0,10))
        self.label(left,'WORLD CLOCK OVERVIEW',9,ORANGE,True).pack(anchor='w',pady=(0,12))
        self.clock_labels=[]
        for cid,city,country,tz in self.store.clocks()[:5]:
            line=tk.Frame(left,bg=PANEL); line.pack(fill='x',pady=7)
            self.label(line,f'{city}, {country}',10,TEXT,True,bg=PANEL).pack(side='left')
            v=self.label(line,'--:--',12,ORANGE,True,bg=PANEL); v.pack(side='right'); self.clock_labels.append((v,tz))
        right=self.panel(mid,padx=18,pady=16); right.pack(side='left',fill='both',expand=True,padx=(10,0))
        self.label(right,'SECURITY & BACKUP',9,ORANGE,True).pack(anchor='w')
        for t in ['Encrypted local database','Password + Authenticator 2FA','Single Owner account','No network / cloud features','Backups stored locally only']:
            self.label(right,'✓  '+t,9,GREEN,bg=PANEL).pack(anchor='w',pady=8)
        self.btn(right,'BACKUP NOW',self.backup_now,True).pack(anchor='w',pady=(12,0))
        self.label(self.main,'Recent activity',12,TEXT,True,bg=BG).pack(anchor='w')
        for at,event,detail in self.store.audit_events(5): self.label(self.main,f'• {at[:19].replace("T"," ")}  {event}  {detail}',8,MUTED,bg=BG).pack(anchor='w',pady=2)

    def clients_page(self):
        self.page_head('Client Management','Create, search and maintain your private client records')
        top=tk.Frame(self.main,bg=BG); top.pack(fill='x',pady=(0,12))
        search=self.entry(top); search.pack(side='left',fill='x',expand=True,ipady=8)
        search.insert(0,'Search name, country, city, email, phone…')
        status_filter=ttk.Combobox(top,values=['All','Active','Prospect','On Hold','Inactive'],state='readonly',width=12); status_filter.set('All'); status_filter.pack(side='left',padx=8,ipady=5)
        self.btn(top,'ADD CLIENT',lambda:self.client_form(),True).pack(side='right',padx=(10,0))
        cols=('id','name','country','city','email','phone','status'); tree=ttk.Treeview(self.main,columns=cols,show='headings')
        for c,w in [('id',45),('name',190),('country',110),('city',100),('email',180),('phone',130),('status',80)]: tree.heading(c,text=c.upper()); tree.column(c,width=w,anchor='w')
        tree.pack(fill='both',expand=True)
        def populate(*_):
            tree.delete(*tree.get_children())
            q=search.get(); q='' if q.startswith('Search name') else q
            for r in self.store.list_clients(q,status_filter.get()): tree.insert('','end',values=(r[0],r[1],r[2],r[3],r[5],r[7],r[10]))
        def selected():
            s=tree.selection()
            if not s: messagebox.showinfo('Select client','Select a client first.'); return None
            return int(tree.item(s[0])['values'][0])
        def edit():
            cid=selected()
            if cid:
                row=self.store.conn.execute('SELECT * FROM clients WHERE id=?',(cid,)).fetchone(); data={k:row[i+1] for i,(k,_) in enumerate(FIELDS)}; self.client_form(data,cid); populate()
        def delete():
            cid=selected()
            if cid and messagebox.askyesno('Confirm deletion','Permanently delete this client? This cannot be undone.'):
                pw=simpledialog.askstring('Re-authentication','Enter Owner password to delete this client:',show='●',parent=self)
                if pw and self.store.reauthenticate(pw): self.store.delete_client(cid); populate()
                elif pw: messagebox.showerror('Access denied','Incorrect Owner password.')
        actions=tk.Frame(self.main,bg=BG); actions.pack(fill='x',pady=10)
        self.btn(actions,'VIEW / EDIT',edit).pack(side='left'); self.btn(actions,'DELETE',delete).pack(side='left',padx=8)
        search.bind('<KeyRelease>',populate); status_filter.bind('<<ComboboxSelected>>',populate); populate(); self.client_tree=tree

    def client_form(self,data=None,client_id=None):
        data=data or {}; win=tk.Toplevel(self); win.title('Client Record'); win.configure(bg=BG); win.geometry('540x690'); win.transient(self); win.grab_set()
        self.label(win,'Client Details',17,TEXT,True,bg=BG).pack(anchor='w',padx=22,pady=18)
        body=tk.Frame(win,bg=BG); body.pack(fill='both',expand=True,padx=22)
        entries={}
        for key,title in FIELDS:
            self.label(body,title,9,MUTED,bg=BG).pack(anchor='w',pady=(5,2))
            if key=='notes':
                e=tk.Text(body,height=4,bg=PANEL2,fg=TEXT,insertbackground=TEXT,relief='flat'); e.pack(fill='x'); e.insert('1.0',data.get(key,'') or '')
            elif key=='status':
                e=ttk.Combobox(body,values=['Active','Prospect','On Hold','Inactive'],state='readonly'); e.pack(fill='x',ipady=4); e.set(data.get(key,'Active') or 'Active')
            else:
                e=self.entry(body); e.pack(fill='x',ipady=5); e.insert(0,data.get(key,'') or '')
            entries[key]=e
        def save():
            d={k:(v.get('1.0','end').strip() if isinstance(v,tk.Text) else v.get().strip()) for k,v in entries.items()}
            try: self.store.save_client(d,client_id); win.destroy(); self.clients_page()
            except Exception as e: messagebox.showerror('Save failed',str(e),parent=win)
        self.btn(win,'SAVE CLIENT',save,True).pack(fill='x',padx=22,pady=18)

    def clocks_page(self):
        self.page_head('World Clocks','Add any city using its IANA time-zone identifier')
        bar=tk.Frame(self.main,bg=BG); bar.pack(fill='x',pady=(0,12))
        city=self.entry(bar); city.pack(side='left',fill='x',expand=True,ipady=7); city.insert(0,'City')
        country=self.entry(bar); country.pack(side='left',fill='x',expand=True,padx=6,ipady=7); country.insert(0,'Country')
        tz=self.entry(bar); tz.pack(side='left',fill='x',expand=True,ipady=7); tz.insert(0,'America/Toronto')
        tree=ttk.Treeview(self.main,columns=('id','city','country','tz','time','date'),show='headings')
        for c,w in [('id',40),('city',140),('country',140),('tz',210),('time',150),('date',150)]: tree.heading(c,text=c.upper()); tree.column(c,width=w)
        tree.pack(fill='both',expand=True)
        def populate():
            tree.delete(*tree.get_children())
            for cid,c,co,z in self.store.clocks(): tree.insert('','end',values=(cid,c,co,z,'',''))
            self.clock_tree=tree
        def add():
            try: self.store.add_clock(city.get(),country.get(),tz.get()); populate()
            except Exception as e: messagebox.showerror('Invalid time zone',str(e))
        def remove():
            s=tree.selection()
            if s and messagebox.askyesno('Remove clock','Remove selected city?'): self.store.delete_clock(int(tree.item(s[0])['values'][0])); populate()
        row=tk.Frame(self.main,bg=BG); row.pack(fill='x',pady=10); self.btn(row,'ADD CLOCK',add,True).pack(side='left'); self.btn(row,'REMOVE SELECTED',remove).pack(side='left',padx=8)
        populate(); self.clock_tree=tree

    def activity_page(self):
        self.page_head('Security Activity','Local audit history stored inside the encrypted database')
        tree=ttk.Treeview(self.main,columns=('at','event','detail'),show='headings')
        for c,w in [('at',220),('event',240),('detail',500)]: tree.heading(c,text=c.upper()); tree.column(c,width=w)
        for r in self.store.audit_events(500): tree.insert('','end',values=(r[0],r[1],r[2]))
        tree.pack(fill='both',expand=True)

    def settings_page(self):
        self.page_head('Settings','Owner security, appearance, local data and backup preferences')
        box=self.panel(self.main,padx=18,pady=16); box.pack(fill='x',pady=7)
        self.label(box,'COMPANY BRANDING',10,ORANGE,True).pack(anchor='w')
        self.btn(box,'UPLOAD / CHANGE COMPANY LOGO',self.change_logo).pack(anchor='w',pady=8)
        self.btn(box,'REMOVE COMPANY LOGO',self.remove_logo).pack(anchor='w')
        box2=self.panel(self.main,padx=18,pady=16); box2.pack(fill='x',pady=7)
        self.label(box2,'SECURITY',10,ORANGE,True).pack(anchor='w')
        self.btn(box2,'START / VIEW TEAM LAN ACCESS',self.team_lan_access,True).pack(anchor='w',pady=8)
        self.btn(box2,'STOP TEAM LAN ACCESS',self.stop_team_lan).pack(anchor='w')
        self.btn(box2,'CHANGE OWNER PASSWORD',self.change_password).pack(anchor='w',pady=8)
        self.btn(box2,'REGENERATE RECOVERY CODES',self.regen_codes).pack(anchor='w')
        box3=self.panel(self.main,padx=18,pady=16); box3.pack(fill='x',pady=7)
        self.label(box3,'PREFERENCES & BACKUP',10,ORANGE,True).pack(anchor='w')
        fmt=ttk.Combobox(box3,values=['12h','24h'],state='readonly',width=8); fmt.set(self.time_format); fmt.pack(anchor='w',pady=7)
        self.btn(box3,'SAVE TIME FORMAT',lambda:self.save_format(fmt.get())).pack(anchor='w')
        self.label(box3,'Automatic session lock (minutes)',9,MUTED,bg=PANEL).pack(anchor='w',pady=(12,3))
        lockvar=ttk.Combobox(box3,values=['1','5','10','15','30'],state='readonly',width=8); lockvar.set(self.store.meta('lock_minutes') or '10'); lockvar.pack(anchor='w')
        self.btn(box3,'SAVE AUTO-LOCK',lambda:self.save_lock_minutes(lockvar.get())).pack(anchor='w',pady=7)
        self.btn(box3,'BACKUP NOW',self.backup_now).pack(anchor='w',pady=8)
        self.btn(box3,'RESTORE ENCRYPTED BACKUP',self.restore_backup).pack(anchor='w')
        self.btn(box3,'OPEN LOCAL DATA FOLDER',lambda:os.startfile(APP_DIR) if os.name=='nt' else messagebox.showinfo('Data folder',str(APP_DIR))).pack(anchor='w',pady=8)
        self.label(self.main,'Security email is stored locally for reference. No email recovery or alerts are sent because this app has no online connectivity.',8,MUTED,bg=BG,wraplength=800).pack(anchor='w',pady=8)

    def team_lan_access(self):
        if self.lan_server is None: self.lan_server=LANReadOnlyServer(self.store)
        try:
            info=self.lan_server.start()
            messagebox.showinfo('Team LAN Access',
                'Team PC-তে Team Viewer খুলে নিচের তথ্য দিন.\n\n'
                f"Server URL: {info['url']}\n\nAccess Token: {info['token']}\n\n"
                f"Certificate SHA-256 Fingerprint: {info['fingerprint']}\n\n"
                'একই Wi-Fi/LAN প্রয়োজন. Owner PC চালু ও Dashboard unlocked থাকতে হবে. '
                'Access বন্ধ করতে Stop Team LAN Access চাপুন. Token গোপন রাখুন.')
            self.store.audit('LAN_TEAM_ACCESS_STARTED',f"HTTPS port {info['port']}")
        except Exception as e: messagebox.showerror('LAN Access',str(e))
    def stop_team_lan(self):
        if self.lan_server:
            self.lan_server.stop(); self.lan_server=None
            messagebox.showinfo('LAN Access','Team LAN access stopped. Existing connections are closed.')
        else: messagebox.showinfo('LAN Access','Team LAN access is not running.')

    def save_format(self,v): self.time_format=v; self.store.set_meta('time_format',v); messagebox.showinfo('Saved','Time format preference saved.')
    def save_lock_minutes(self,v): self.store.set_meta('lock_minutes',v); self._activity(); messagebox.showinfo('Saved',f'Automatic lock set to {v} minute(s).')
    def change_logo(self):
        f=filedialog.askopenfilename(filetypes=[('Image files','*.png *.jpg *.jpeg *.gif *.bmp')])
        if f:
            APP_DIR.mkdir(parents=True,exist_ok=True)
            for old in APP_DIR.glob('company_logo.*'): old.unlink(missing_ok=True)
            shutil.copy2(f,LOGO_PATH.with_suffix(Path(f).suffix)); self.refresh_logo(); messagebox.showinfo('Logo','Company logo updated locally.')
    def remove_logo(self):
        for p in APP_DIR.glob('company_logo.*'): p.unlink(missing_ok=True)
        self.refresh_logo(); messagebox.showinfo('Logo','Company logo removed.')
    def refresh_logo(self):
        if not hasattr(self,'logo_label'): return
        self.logo_img=None; self.logo_label.configure(image='',text='ATELPIX',fg=ORANGE,font=('Segoe UI',19,'bold'))
        if LOGO_PATH.exists() or list(APP_DIR.glob('company_logo.*')): self.load_logo()
    def load_logo(self):
        try:
            from PIL import Image,ImageTk
            p=next(APP_DIR.glob('company_logo.*')); im=Image.open(p); im.thumbnail((175,65)); self.logo_img=ImageTk.PhotoImage(im); self.logo_label.configure(image=self.logo_img,text='')
        except Exception: pass
    def change_password(self):
        old=simpledialog.askstring('Change password','Current password:',show='●',parent=self); new=simpledialog.askstring('Change password','New password (12+ characters):',show='●',parent=self)
        if old and new:
            try: self.store.change_password(old,new); messagebox.showinfo('Password','Password changed successfully.')
            except Exception as e: messagebox.showerror('Password',str(e))
    def regen_codes(self):
        if not messagebox.askyesno('Regenerate codes','All previous recovery codes will stop working. Continue?'): return
        pw=simpledialog.askstring('Re-authentication','Enter Owner password:',show='●',parent=self)
        if not pw or not self.store.reauthenticate(pw): messagebox.showerror('Access denied','Incorrect Owner password.'); return
        codes=self.store.generate_recovery_codes(); messagebox.showinfo('New recovery codes','Save these codes securely. They are shown only once:\n\n'+'\n'.join(codes))

    def backup_now(self):
        default=APP_DIR/'Backups'/f'Atelpix_Backup_{datetime.now():%Y%m%d_%H%M%S}.atbak'
        try:
            default.parent.mkdir(parents=True,exist_ok=True)
            self.store.backup(default); messagebox.showinfo('Backup complete',f'Encrypted backup created on this PC:\n{default}')
        except Exception as e: messagebox.showerror('Backup failed',str(e))
    def check_backup_due(self):
        if self.store.backup_due():
            try:
                folder=APP_DIR/'Backups'; folder.mkdir(parents=True,exist_ok=True)
                self.store.backup(folder/f'Atelpix_Auto_{datetime.now():%Y%m%d_%H%M%S}.atbak')
                messagebox.showinfo('Automatic backup','A scheduled encrypted backup was created in the local Backups folder.')
            except Exception as e: messagebox.showerror('Automatic backup failed',str(e))
    def restore_backup(self):
        backup_dir=(APP_DIR/'Backups').resolve(); backup_dir.mkdir(parents=True,exist_ok=True)
        f=filedialog.askopenfilename(initialdir=str(backup_dir),filetypes=[('Encrypted Atelpix Backup','*.atbak')])
        if not f: return
        try:
            Path(f).resolve().relative_to(backup_dir)
        except ValueError:
            messagebox.showerror('Invalid location','For privacy, restore backups only from this PC’s local Atelpix Backups folder.'); return
        current_pw=simpledialog.askstring('Re-authentication','Enter current Owner password:',show='●',parent=self)
        if not current_pw: return
        backup_pw=simpledialog.askstring('Backup password','Enter the Owner password that was active when this backup was created:',show='●',parent=self)
        if not backup_pw: return
        if not messagebox.askyesno('Confirm restore','Restore will replace the current database with the selected backup. Continue?'): return
        try: self.store.restore(Path(f),backup_pw,current_pw); messagebox.showinfo('Restore complete','Backup integrity validated and restored. The app will restart its view.'); self.dashboard()
        except Exception as e: messagebox.showerror('Restore failed',str(e))

    def tick(self):
        if not self.unlocked: return
        lock_minutes=int(self.store.meta('lock_minutes') or '10')
        if time.monotonic()-self.last_activity > lock_minutes*60:
            self.lock(); return
        if hasattr(self,'clock_labels'):
            for lbl,tz in self.clock_labels:
                try: lbl.configure(text=datetime.now(ZoneInfo(tz)).strftime('%I:%M:%S %p' if self.time_format=='12h' else '%H:%M:%S'))
                except Exception: lbl.configure(text='Invalid zone')
        if getattr(self,'clock_tree',None) is not None:
            for iid in self.clock_tree.get_children():
                vals=list(self.clock_tree.item(iid)['values']); z=vals[3]
                try:
                    now=datetime.now(ZoneInfo(z)); vals[4]=now.strftime('%I:%M:%S %p' if self.time_format=='12h' else '%H:%M:%S'); vals[5]=now.strftime('%Y-%m-%d')
                except Exception: vals[4]='Invalid'; vals[5]=''
                self.clock_tree.item(iid,values=vals)
        # Automatic scheduled backup: while unlocked, if due, create it without prompting.
        if self.store.backup_due():
            try:
                folder=APP_DIR/'Backups'; folder.mkdir(parents=True,exist_ok=True)
                self.store.backup(folder/f'Atelpix_Auto_{datetime.now():%Y%m%d_%H%M%S}.atbak')
            except Exception: pass
        self.after(1000,self.tick)

    def close_app(self):
        if self.lan_server:
            self.lan_server.stop(); self.lan_server=None
        if self.unlocked:
            self.store.close(); self.unlocked=False
        self.destroy()

    def lock(self):
        if self.lan_server:
            self.lan_server.stop(); self.lan_server=None
        if self.unlocked:
            self.store.close(); self.unlocked=False
        self.show_login()

if __name__=='__main__':
    App().mainloop()
