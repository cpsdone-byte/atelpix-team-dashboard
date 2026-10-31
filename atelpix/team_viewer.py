"""Read-only Team workstation client. HTTPS certificate fingerprint is pinned by user."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import http.client, ssl, json, hashlib, threading
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo
BG='#111318'; PANEL='#191d24'; TEXT='#f1f3f5'; MUTED='#a6adb8'; ORANGE='#D46605'
class TeamViewer(tk.Tk):
 def __init__(self):
  super().__init__(); self.title('Atelpix Team Viewer'); self.geometry('1050x680'); self.configure(bg=BG); self.url=None; self.token=None; self.fp=None
  self.style=ttk.Style(self); self.style.theme_use('clam'); self.style.configure('Treeview',background=PANEL,foreground=TEXT,fieldbackground=PANEL,rowheight=28); self.style.configure('Treeview.Heading',background='#202630',foreground=TEXT)
  self.login()
 def label(self,p,t): return tk.Label(p,text=t,bg=BG,fg=TEXT,font=('Segoe UI',10))
 def login(self):
  f=tk.Frame(self,bg=PANEL,padx=25,pady=25); f.place(relx=.5,rely=.5,anchor='center')
  tk.Label(f,text='ATELPIX · TEAM VIEWER',bg=PANEL,fg=ORANGE,font=('Segoe UI',20,'bold')).pack(pady=(0,15))
  self.urlv=self.field(f,'Owner Server URL (example https://192.168.1.10:8765)')
  self.tokenv=self.field(f,'Team access token')
  self.fpv=self.field(f,'Owner certificate SHA-256 fingerprint (shown on Owner PC)')
  tk.Button(f,text='CONNECT SECURELY',command=self.connect,bg=ORANGE,fg='white',relief='flat',padx=15,pady=10).pack(fill='x',pady=12)
  self.label(f,'Read-only access. Same Wi-Fi/LAN required. No cloud or VPN.').pack()
 def field(self,p,t):
  self.label(p,t).pack(anchor='w',pady=(8,3)); e=tk.Entry(p,width=64,bg='#202630',fg=TEXT,insertbackground=TEXT,relief='flat'); e.pack(ipady=8); return e
 def request(self,path):
  u=urlparse(self.url); ctx=ssl._create_unverified_context(); c=http.client.HTTPSConnection(u.hostname,u.port or 443,context=ctx,timeout=8)
  c.connect(); cert=c.sock.getpeercert(binary_form=True) if c.sock else None
  if not cert: c.close(); raise RuntimeError('TLS certificate unavailable')
  actual=':'.join(f'{b:02X}' for b in hashlib.sha256(cert).digest())
  expected=':'.join(x.zfill(2) for x in self.fp.replace(' ','').replace('-',':').split(':'))
  if not __import__('hmac').compare_digest(actual,expected): c.close(); raise RuntimeError('Owner certificate fingerprint mismatch. Connection blocked.')
  c.request('GET',path,headers={'Authorization':'Bearer '+self.token,'Connection':'close'}); r=c.getresponse()
  body=r.read(); c.close()
  if r.status!=200: raise RuntimeError('Server response: '+str(r.status))
  return json.loads(body.decode('utf-8'))
 def connect(self):
  self.url=self.urlv.get().strip().rstrip('/'); self.token=self.tokenv.get().strip(); self.fp=self.fpv.get().strip().upper()
  if not self.url.startswith('https://') or not self.token or not self.fp: messagebox.showerror('Connect','Enter HTTPS URL, token and certificate fingerprint.'); return
  try: self.request('/api/health')
  except Exception as e: messagebox.showerror('Connection failed',str(e)); return
  self.show_data(); self.refresh()
 def show_data(self):
  for w in self.winfo_children(): w.destroy()
  head=tk.Frame(self,bg=BG); head.pack(fill='x',padx=20,pady=15)
  tk.Label(head,text='ATELPIX · TEAM VIEWER',bg=BG,fg=ORANGE,font=('Segoe UI',18,'bold')).pack(side='left')
  tk.Label(head,text='READ ONLY  •  LIVE REFRESH',bg=BG,fg='#43b581',font=('Segoe UI',9,'bold')).pack(side='right')
  self.status=self.label(self,'Connecting…'); self.status.pack(anchor='w',padx=20)
  self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=20,pady=15)
  cf=tk.Frame(self.tabs,bg=BG); wf=tk.Frame(self.tabs,bg=BG); self.tabs.add(cf,text='Client List'); self.tabs.add(wf,text='World Clock')
  cols=('name','country','city','email','phone','status'); self.tree=ttk.Treeview(cf,columns=cols,show='headings')
  for c,w in [('name',220),('country',130),('city',120),('email',220),('phone',140),('status',100)]: self.tree.heading(c,text=c.upper()); self.tree.column(c,width=w)
  self.tree.pack(fill='both',expand=True,padx=8,pady=8)
  self.clocks=tk.Text(wf,bg=PANEL,fg=TEXT,relief='flat',font=('Segoe UI',13),state='disabled'); self.clocks.pack(fill='both',expand=True,padx=8,pady=8)
 def refresh(self):
  if not self.url: return
  def work():
   try: data=self.request('/api/clients'); clocks=self.request('/api/clocks'); self.after(0,lambda:self.render(data,clocks))
   except Exception as e: self.after(0,lambda:self.status.configure(text='Disconnected: '+str(e)))
  threading.Thread(target=work,daemon=True).start()
  self.after(5000,self.refresh)
 def render(self,data,clocks):
  self.tree.delete(*self.tree.get_children())
  for r in data['clients']: self.tree.insert('','end',values=(r.get('name'),r.get('country'),r.get('city'),r.get('email'),r.get('phone'),r.get('status')))
  self.clocks.configure(state='normal'); self.clocks.delete('1.0','end')
  for c in clocks['clocks']:
   try: now=datetime.now(ZoneInfo(c['timezone'])).strftime('%Y-%m-%d  %H:%M:%S')
   except Exception: now='Invalid timezone'
   self.clocks.insert('end',f"{c['city']}, {c['country']}   {now}   ({c['timezone']})\n\n")
  self.clocks.configure(state='disabled'); self.status.configure(text=f"Connected · {len(data['clients'])} clients · refreshes every 5 seconds")
