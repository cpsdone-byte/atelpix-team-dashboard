"""Owner-side HTTPS read-only LAN service. No cloud, VPN, relay, or router setup."""
from __future__ import annotations
import hashlib, json, os, secrets, socket, ssl, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class LANReadOnlyServer:
    def __init__(self, store, port=8765):
        self.store=store; self.port=port; self.httpd=None; self.thread=None
        self.token=secrets.token_urlsafe(36)
        self.cert_path=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Atelpix'/'SecureClientDashboard'/'lan-cert.pem'
        self.key_path=self.cert_path.with_name('lan-key.pem')
        self.fingerprint=''
    def _certificate(self):
        self.cert_path.parent.mkdir(parents=True,exist_ok=True)
        if not self.cert_path.exists() or not self.key_path.exists():
            key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
            subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Atelpix Local Owner')])
            cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                  .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1))
                  .not_valid_after(datetime.now(timezone.utc)+timedelta(days=3650))
                  .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False)
                  .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256()))
            self.key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            self.cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            try: os.chmod(self.key_path,0o600)
            except OSError: pass
        cert=x509.load_pem_x509_certificate(self.cert_path.read_bytes())
        self.fingerprint=cert.fingerprint(hashes.SHA256()).hex(':').upper()
    def start(self):
        if self.httpd: return self.info()
        self._certificate(); owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def _send(self,code,obj):
                raw=json.dumps(obj,ensure_ascii=False).encode('utf-8')
                self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
            def do_GET(self):
                if not secrets.compare_digest(self.headers.get('Authorization',''), 'Bearer '+owner.token):
                    self._send(401,{'error':'unauthorized'}); return
                try:
                    if self.path=='/api/health': self._send(200,{'status':'ok','version':1}); return
                    if self.path=='/api/clients':
                        rows=owner.store.list_clients()
                        keys=['id','name','country','city','email','phone','status']
                        self._send(200,{'clients':[dict(zip(keys,(r[0],r[1],r[2],r[3],r[5],r[7],r[10]))) for r in rows]}); return
                    if self.path=='/api/clocks':
                        self._send(200,{'clocks':[{'id':r[0],'city':r[1],'country':r[2],'timezone':r[3]} for r in owner.store.clocks()]}); return
                    self._send(404,{'error':'not_found'})
                except Exception: self._send(503,{'error':'owner_dashboard_locked_or_unavailable'})
            def do_POST(self): self._send(405,{'error':'read_only'})
            do_PUT=do_POST; do_PATCH=do_POST; do_DELETE=do_POST
        self.httpd=ThreadingHTTPServer(('0.0.0.0',self.port),Handler)
        self.httpd.daemon_threads=True
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.minimum_version=ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(str(self.cert_path),str(self.key_path)); self.httpd.socket=ctx.wrap_socket(self.httpd.socket,server_side=True)
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True); self.thread.start()
        return self.info()
    def info(self):
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('192.0.2.1',80)); ip=s.getsockname()[0]; s.close()
        except OSError: ip='Owner-PC-LAN-IP'
        return {'url':f'https://{ip}:{self.port}','token':self.token,'fingerprint':self.fingerprint,'port':self.port}
    def rotate_token(self): self.token=secrets.token_urlsafe(36); return self.token
    def stop(self):
        if self.httpd:
            self.httpd.shutdown(); self.httpd.server_close(); self.httpd=None; self.thread=None
