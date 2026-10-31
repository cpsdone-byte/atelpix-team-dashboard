import hashlib, http.client, ssl, urllib.parse
from atelpix.lan_server import LANReadOnlyServer
class FakeStore:
 def list_clients(self): return [(1,'Example','US','NY','America/New_York','x@example.com','','123','','','Active','now','now')]
 def clocks(self): return [(1,'Dhaka','Bangladesh','Asia/Dhaka')]
def call(info,path,token=None,method='GET'):
 u=urllib.parse.urlparse(info['url']); c=http.client.HTTPSConnection(u.hostname,u.port,context=ssl._create_unverified_context(),timeout=5); c.connect()
 fp=':'.join(f'{b:02X}' for b in hashlib.sha256(c.sock.getpeercert(binary_form=True)).digest())
 c.request(method,path,headers={'Authorization':'Bearer '+(token if token is not None else info['token'])}); r=c.getresponse(); status=r.status; body=r.read(); c.close(); return status,fp,body
def test_lan_security_contract():
 s=LANReadOnlyServer(FakeStore(),port=18766)
 try:
  info=s.start()
  assert call(info,'/api/health')[0]==200
  assert call(info,'/api/health','invalid-token')[0]==401
  assert call(info,'/api/clients',method='POST')[0]==405
  assert call(info,'/api/clients',method='DELETE')[0]==405
  assert call(info,'/api/clients')[1]==info['fingerprint']
  assert call(info,'/api/clients')[0]==200
  assert call(info,'/api/clocks')[0]==200
 finally: s.stop()
