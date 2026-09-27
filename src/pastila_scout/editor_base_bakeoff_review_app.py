from __future__ import annotations
import argparse,hashlib,json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

HTML='''<!doctype html><meta charset="utf-8"><title>EDITOR blind review</title><style>body{font:17px system-ui;max-width:1100px;margin:30px auto;padding:0 20px}article{border:1px solid #bbb;padding:16px;margin:12px 0;border-radius:8px}.out{background:#f5f5f5}button{font-size:18px;padding:12px 24px}select{font-size:16px}label{display:block;margin:8px 0}</style><h1>EDITOR — evaluare blind</h1><div id="app"></div><script>let D,I=0;async function load(){D=await(await fetch('/api')).json();I=D.done;draw()}function sel(n,opts){return `<label>${n}: <select id="${n}">${opts.map(x=>`<option>${x}</option>`).join('')}</select></label>`}function draw(){let a=document.querySelector('#app');if(I>=D.cases.length){a.innerHTML='<h2>48/48 blocate. Oprește-te aici.</h2>';return}let c=D.cases[I];a.innerHTML=`<p>${I+1}/48</p><h2>${c.case_id}</h2><p><b>Cerință:</b> ${c.request}</p><article><b>Autoritate factuală</b>${c.source_authority.map(x=>`<p>${x.quote}</p>`).join('')}</article>${['A','B','C'].map(x=>`<article class=out><b>${x}</b><p>${c.outputs[x]}</p>${sel('safety_'+x,['PASS','FAIL','UNSURE'])}${sel('suff_'+x,['PASS','FAIL','UNSURE'])}${sel('romanian_'+x,[1,2,3,4,5])}${sel('natural_'+x,[1,2,3,4,5])}${sel('usable_'+x,[1,2,3,4,5])}</article>`).join('')}${sel('winner',['A','B','C','TIE'])}<button onclick="save()">Blochează și continuă</button>`}async function save(){let c=D.cases[I],v={case_id:c.case_id,winner:winner.value,scores:{}};for(let x of ['A','B','C'])v.scores[x]={factual_safety:window['safety_'+x].value,factual_sufficiency:window['suff_'+x].value,functional_romanian:+window['romanian_'+x].value,naturalness:+window['natural_'+x].value,usable_realization:+window['usable_'+x].value};let r=await fetch('/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(v)});if(!r.ok){alert(await r.text());return}I++;draw()}load()</script>'''
class App:
 def __init__(self,pack,state):
  self.pack=json.loads(pack.read_text());core={k:v for k,v in self.pack.items() if k!='pack_identity'}
  expected=hashlib.sha256((json.dumps(core,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
  if self.pack.get('pack_identity')!=expected or len(self.pack.get('cases',[]))!=48:raise ValueError('pack identity/inventory')
  self.state=state;state.mkdir(parents=True,exist_ok=True)
 def done(self):return sum((self.state/f'{c["case_id"]}.json').exists() for c in self.pack['cases'])
 def score(self,v):
  case=self.pack['cases'][self.done()];
  if v.get('case_id')!=case['case_id'] or v.get('winner') not in ('A','B','C','TIE'):raise ValueError('invalid case/winner')
  if set(v.get('scores',{}))!={'A','B','C'}:raise ValueError('scores')
  for s in v['scores'].values():
   if s['factual_safety'] not in ('PASS','FAIL','UNSURE') or s['factual_sufficiency'] not in ('PASS','FAIL','UNSURE') or any(s[k] not in range(1,6) for k in ('functional_romanian','naturalness','usable_realization')):raise ValueError('rubric')
  v['pack_identity']=self.pack['pack_identity'];v['receipt_identity']=hashlib.sha256((json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
  raw=(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode();fd=os.open(self.state/f'{case["case_id"]}.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  if self.done()==48:
   ids=[json.loads((self.state/f'{c["case_id"]}.json').read_text())['receipt_identity'] for c in self.pack['cases']]
   closure={'status':'PASS_48_BLIND_LOCKED','pack_identity':self.pack['pack_identity'],'receipts':ids};closure['closure_identity']=hashlib.sha256((json.dumps(closure,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
   raw=(json.dumps(closure,sort_keys=True,separators=(',',':'))+'\n').encode();fd=os.open(self.state/'closure.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/':b=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b)
  elif self.path=='/api':b=json.dumps({'cases':self.server.app.pack['cases'],'done':self.server.app.done()},ensure_ascii=False).encode();self.send_response(200);self.end_headers();self.wfile.write(b)
  else:self.send_error(404)
 def do_POST(self):
  try:n=int(self.headers.get('Content-Length','0'));self.server.app.score(json.loads(self.rfile.read(n)));self.send_response(204);self.end_headers()
  except Exception as e:self.send_error(400,str(e))
 def log_message(self,*a):pass
def main():
 p=argparse.ArgumentParser();p.add_argument('--pack',type=Path,required=True);p.add_argument('--state',type=Path,required=True);p.add_argument('--port',type=int,default=8774);a=p.parse_args();s=ThreadingHTTPServer(('127.0.0.1',a.port),H);s.app=App(a.pack,a.state);print(f'OPEN MANUALLY: http://127.0.0.1:{a.port}',flush=True);s.serve_forever()
if __name__=='__main__':main()
