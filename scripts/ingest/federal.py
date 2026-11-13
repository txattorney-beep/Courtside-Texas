"""Refresh current official rule links from their landing pages; preserve prior text on failure."""
import pathlib,json,urllib.request,urllib.parse,html.parser,subprocess,tempfile,datetime,hashlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
class Links(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.href=None;self.label=''
 def handle_starttag(self,t,a):
  if t=='a':self.href=dict(a).get('href');self.label=''
 def handle_data(self,s):
  if self.href:self.label+=s
 def handle_endtag(self,t):
  if t=='a' and self.href:self.links.append((self.href,self.label));self.href=None
PATTERNS={'trcp':r'rules.*civil.*procedure','texas-trcp':r'rules.*civil.*procedure','trap':r'rules.*appellate.*procedure','tre':r'rules.*evidence','trja':r'rules.*judicial.*administration','txwd-local':r'Local-Rules-Full-Copy','txsd-local':r'LR_.*\.pdf','txnd-local-civil':r'CIVRULES\.pdf','txnd-local-criminal':r'CRIMRULES\.pdf','ca5-local':r'5thcir-iop','ca5-combined':r'federalrulesofappellateprocedure'}
def request(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CourtsideTexas/1.0 (public rules reference; ehudson@atlawpllc.com)'}),timeout=45) as r:return r.read(30_000_000)
def run():
 path=ROOT/'data'/'federal-sources.json';source=json.loads(path.read_text());now=datetime.datetime.now(datetime.timezone.utc).isoformat();pages={}
 for d in source['rules']:
  url=d['url'];page=d['sourcePage'];d['checkedAt']=now
  try:
   if page not in pages:
    p=Links();p.feed(request(page).decode(errors='replace'));pages[page]=p.links
   pattern=PATTERNS.get(d['id'])
   if pattern:
    matches=[urllib.parse.urljoin(page,u) for u,label in pages[page] if re.search(pattern,u+' '+label,re.I) and not re.search(r'proposed|redline|superseded',label,re.I)]
    if matches:url=matches[0]
  except Exception:pass
  try:
   b=request(url)
   if not b.startswith(b'%PDF'):raise ValueError('Official document did not return a PDF')
   with tempfile.TemporaryDirectory() as td:
    f=pathlib.Path(td)/'rule.pdf';f.write_bytes(b);r=subprocess.run(['pdftotext','-layout',str(f),'-'],capture_output=True,timeout=60)
    text=r.stdout.decode(errors='replace').strip()
   if len(text)<60:raise ValueError('No extractable PDF text')
   target=ROOT/'data'/'seed-texts'/(d['id']+'.txt');target.parent.mkdir(exist_ok=True);target.write_text(text)
   d['lastRetrievalFailed']=False
   if url!=d['url']:d['versionNote']='Current compilation linked by the official source'
   d.update(url=url,textPath=str(target.relative_to(ROOT)),retrieval='direct-pdf',note='Retrieved from the official source.',sha256=hashlib.sha256(b).hexdigest(),retrievedAt=now)
  except Exception as err:
   d['note']='Latest direct retrieval failed; prior text retained where available. '+str(err)[:150]
   d['lastRetrievalFailed']=True
 (path).write_text(json.dumps(source,indent=2))
if __name__=='__main__':run()
