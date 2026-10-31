"""Encrypted local-only storage. SQLite exists only in memory while unlocked."""
from __future__ import annotations
import io, os, sqlite3, json, time, shutil
from pathlib import Path
from datetime import datetime, timezone
from .security import *

APP_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Atelpix' / 'SecureClientDashboard'
DB_PATH = APP_DIR / 'clients.atdb'
LOGO_PATH = APP_DIR / 'company_logo'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clients (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, country TEXT DEFAULT '', city TEXT DEFAULT '',
 timezone TEXT DEFAULT 'UTC', email TEXT DEFAULT '', whatsapp TEXT DEFAULT '', phone TEXT DEFAULT '',
 website TEXT DEFAULT '', notes TEXT DEFAULT '', status TEXT DEFAULT 'Active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clocks (id INTEGER PRIMARY KEY AUTOINCREMENT, city TEXT NOT NULL, country TEXT DEFAULT '', timezone TEXT NOT NULL UNIQUE, sort_order INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS recovery (code_hash TEXT PRIMARY KEY, used_at TEXT DEFAULT NULL);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, event TEXT NOT NULL, detail TEXT DEFAULT '');
'''
DEFAULT_CLOCKS = [('Dhaka','Bangladesh','Asia/Dhaka'),('New York','United States','America/New_York'),('Toronto','Canada','America/Toronto'),('Sydney','Australia','Australia/Sydney'),('London','United Kingdom','Europe/London')]

class LocalStore:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path); self.conn = None; self.password = None; self.failures = 0; self.locked_until = 0

    @property
    def initialized(self): return self.path.exists()

    def setup(self, password: str, owner_name: str = 'Owner') -> str:
        if self.initialized: raise SecurityError('Owner account already exists.')
        if len(password) < 12: raise SecurityError('Use at least 12 characters for the Owner password.')
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.executescript(SCHEMA)
        secret = totp_secret()
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany('INSERT INTO clocks(city,country,timezone,sort_order) VALUES(?,?,?,?)', [(c,co,t,i) for i,(c,co,t) in enumerate(DEFAULT_CLOCKS)])
        self.conn.execute('INSERT INTO meta VALUES(?,?)', ('totp_secret', secret))
        self.conn.execute('INSERT INTO meta VALUES(?,?)', ('owner_name', owner_name))
        self.conn.execute('INSERT INTO meta VALUES(?,?)', ('last_backup', ''))
        self.password = password
        self.audit('OWNER_ACCOUNT_CREATED','First-time setup')
        self._save()
        return secret

    def unlock(self, password: str) -> None:
        now = time.time()
        if now < self.locked_until: raise SecurityError(f'Too many attempts. Try again in {int(self.locked_until-now)} seconds.')
        if not self.initialized: raise SecurityError('No Owner account exists yet.')
        try: raw = decrypt_container(DB_MAGIC, self.path.read_bytes(), password)
        except SecurityError:
            self.failures += 1
            if self.failures >= 5: self.locked_until = time.time() + min(900, 30 * (2 ** min(self.failures-5, 4)))
            raise
        self.failures = 0; self.password = password
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.deserialize(raw)
        self.audit('OWNER_LOGIN','Password-only Owner login accepted')

    def close(self):
        if self.conn:
            try: self.audit('SESSION_LOCKED','Application locked')
            except Exception: pass
            self._save(); self.conn.close(); self.conn = None
        self.password = None

    def _require(self):
        if self.conn is None or self.password is None: raise SecurityError('Application is locked.')

    def _save(self):
        self._require(); raw = self.conn.serialize(); atomic_write(self.path, encrypt_container(DB_MAGIC, raw, self.password))

    def meta(self, key):
        self._require(); row=self.conn.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone(); return row[0] if row else None

    def set_meta(self,key,value):
        self._require(); self.conn.execute('INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value))); self._save()

    def audit(self,event,detail=''):
        if self.conn is not None:
            self.conn.execute('INSERT INTO audit(at,event,detail) VALUES(?,?,?)',(datetime.now(timezone.utc).isoformat(),event,detail))
            if event not in ('OWNER_LOGIN',): self._save()

    def reset_authenticator(self):
        """Replace the Owner TOTP secret after password re-authentication."""
        self._require()
        secret = totp_secret()
        self.set_meta('totp_secret', secret)
        codes = self.generate_recovery_codes()
        self.audit('AUTHENTICATOR_RESET','Authenticator replaced after Owner password verification')
        self._save()
        return secret, codes

    def verify_second_factor(self, code: str, recovery: bool=False) -> bool:
        self._require()
        if recovery:
            digest=recovery_hash(code)
            row=self.conn.execute('SELECT code_hash FROM recovery WHERE code_hash=? AND used_at IS NULL',(digest,)).fetchone()
            if not row: return False
            self.conn.execute('UPDATE recovery SET used_at=? WHERE code_hash=?',(datetime.now(timezone.utc).isoformat(),digest))
            self.audit('RECOVERY_CODE_USED','One-time recovery code consumed'); self._save(); return True
        ok=verify_totp(self.meta('totp_secret'),code)
        if ok: self.audit('TOTP_LOGIN_SUCCESS','Authenticator accepted')
        else: self.audit('TOTP_LOGIN_FAILED','Invalid authenticator code')
        self._save(); return ok

    def generate_recovery_codes(self):
        self._require(); codes=make_recovery_codes()
        self.conn.execute('DELETE FROM recovery')
        self.conn.executemany('INSERT INTO recovery(code_hash) VALUES(?)',[(recovery_hash(c),) for c in codes])
        self.audit('RECOVERY_CODES_REGENERATED',f'{len(codes)} codes generated'); self._save(); return codes

    def list_clients(self, query='', status=''):
        self._require(); q=f'%{query.strip()}%'
        sql='''SELECT * FROM clients WHERE (name LIKE ? OR country LIKE ? OR city LIKE ? OR email LIKE ? OR phone LIKE ? OR whatsapp LIKE ?)'''
        args=[q,q,q,q,q,q]
        if status and status!='All': sql+=' AND status=?'; args.append(status)
        return self.conn.execute(sql+' ORDER BY name COLLATE NOCASE',args).fetchall()

    def save_client(self, data: dict, client_id=None):
        self._require(); required=data.get('name','').strip()
        if not required: raise ValueError('Client/Company Name is required.')
        fields=['name','country','city','timezone','email','whatsapp','phone','website','notes','status']
        values=[data.get(k,'').strip() for k in fields]; now=datetime.now(timezone.utc).isoformat()
        if client_id:
            self.conn.execute('UPDATE clients SET '+','.join(f'{k}=?' for k in fields)+',updated_at=? WHERE id=?',values+[now,client_id]); event='CLIENT_UPDATED'
        else:
            self.conn.execute('INSERT INTO clients('+','.join(fields)+',created_at,updated_at) VALUES('+','.join('?' for _ in fields)+',?,?)',values+[now,now]); event='CLIENT_ADDED'
        self.audit(event,required); self._save()

    def delete_client(self, client_id):
        self._require(); row=self.conn.execute('SELECT name FROM clients WHERE id=?',(client_id,)).fetchone()
        if row: self.conn.execute('DELETE FROM clients WHERE id=?',(client_id,)); self.audit('CLIENT_DELETED',row[0]); self._save()

    def clocks(self): self._require(); return self.conn.execute('SELECT id,city,country,timezone FROM clocks ORDER BY sort_order,id').fetchall()
    def add_clock(self,city,country,tz):
        self._require(); from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try: ZoneInfo(tz)
        except Exception: raise ValueError('Enter a valid IANA time zone, e.g. America/Toronto.')
        self.conn.execute('INSERT INTO clocks(city,country,timezone,sort_order) VALUES(?,?,?,COALESCE((SELECT MAX(sort_order)+1 FROM clocks),0))',(city.strip(),country.strip(),tz.strip())); self.audit('CLOCK_ADDED',f'{city}, {tz}'); self._save()
    def delete_clock(self,clock_id): self._require(); self.conn.execute('DELETE FROM clocks WHERE id=?',(clock_id,)); self.audit('CLOCK_REMOVED',str(clock_id)); self._save()

    def reauthenticate(self, password):
        self._require()
        return hmac.compare_digest(self.password, password)

    def change_password(self, old_password, new_password):
        self._require()
        if not hmac.compare_digest(self.password,old_password): raise SecurityError('Current password is incorrect.')
        if len(new_password)<12: raise SecurityError('New password must contain at least 12 characters.')
        self.password=new_password; self.audit('OWNER_PASSWORD_CHANGED','Owner password changed'); self._save()

    def backup(self, destination: Path):
        self._require(); self.audit('BACKUP_CREATED',destination.name)
        encrypted_db=self.path.read_bytes()
        blob=encrypt_container(BACKUP_MAGIC,encrypted_db,self.password)
        atomic_write(Path(destination),blob); self.set_meta('last_backup',datetime.now(timezone.utc).isoformat())
        return Path(destination)

    def restore(self, source: Path, backup_password: str, current_password: str):
        self._require()
        if not hmac.compare_digest(self.password,current_password): raise SecurityError('Owner re-authentication failed.')
        payload=decrypt_container(BACKUP_MAGIC,Path(source).read_bytes(),backup_password)
        # Validate the nested database with the password that protected this backup.
        plain=decrypt_container(DB_MAGIC,payload,backup_password)
        test=sqlite3.connect(':memory:', check_same_thread=False); test.deserialize(plain)
        test.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="clients"').fetchone(); test.close()
        # Replace the in-memory database only after all integrity checks pass.
        self.conn.close()
        self.conn=sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.deserialize(plain)
        # Re-encrypt restored contents using the current Owner password.
        atomic_write(self.path,encrypt_container(DB_MAGIC,plain,self.password))
        self.audit('BACKUP_RESTORED',Path(source).name); self._save()

    def backup_due(self):
        last=self.meta('last_backup') or ''
        if not last: return True
        try: return (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds() >= 7*86400
        except Exception: return True

    def audit_events(self,limit=100): self._require(); return self.conn.execute('SELECT at,event,detail FROM audit ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
