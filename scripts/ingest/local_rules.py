"""Official OCA document extraction. No login, CAPTCHA or robots bypass."""
import sys,concurrent.futures,datetime,hashlib,json,os,pathlib,subprocess,tempfile,time,urllib.request,urllib.error
BASE='https://topics.txcourts.gov/LocalRulesPublic/'
UA='CourtsideTexas/1.0 (public court rules index; ehudson@atlawpllc.com)'
def get(url):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=45) as r: return r.read(30_000_000)
  except urllib.error.HTTPError as e:
   if e.code not in (429,500,502,503,504): raise
   if attempt==2: raise
   time.sleep(2**attempt)
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
def main():
 root=pathlib.Path(__file__).resolve().parents[2]; cache=root/'work'/'rules-cache';cache.mkdir(parents=True,exist_ok=True)
 rows=json.loads(get(BASE+'GetAllLocalRuleDocuments'))['data']; rows=[r for r in rows if any(t in r[4] for t in ['District','COA','AJR','Business Court'])]
 previous={}
 old=root/'data'/'documents.json'
 if old.exists(): previous={d['id']:d for d in json.loads(old.read_text())}
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def fetch(r):
  typ,title,posted,county,group,sub,identifier=r;id='oca-'+str(identifier);url=BASE+'PreviewAttachment/'+str(identifier)
  d={'id':id,'title':title,'category':'local','documentType':typ,'county':county,'courtGroup':group,'sourceUrl':url,'sourcePage':BASE+'CourtDetailsForDocument/'+str(identifier),'postedDate':posted,'checkedAt':now,'retrievedAt':None,'status':'unavailable','text':''}
  try:
   p=cache/(str(identifier)+'.pdf');b=p.read_bytes() if '--resume' in sys.argv and p.exists() else get(url)
   if not b.startswith(b'%PDF'):raise ValueError('Source did not return a PDF')
   h=hashlib.sha256(b).hexdigest()
   oldhash=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else previous.get(id,{}).get('sha256')
   if oldhash and oldhash!=h:(root/'work'/'ocr-cache'/(str(identifier)+'.txt')).unlink(missing_ok=True)
   p.write_bytes(b)
   if previous.get(id,{}).get('sha256')==h and previous[id].get('text'): text=previous[id]['text']
   else:
    t=subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,timeout=60)
    if t.returncode: raise ValueError('PDF text extraction failed')
    text=t.stdout.decode('utf-8',errors='replace').strip()
   d.update(text=text[:950000],sha256=h,retrievedAt=now,status=('ocr' if previous.get(id,{}).get('status')=='ocr' and previous.get(id,{}).get('sha256')==h else 'indexed') if len(text)>60 else 'scan-only')
   if len(text)>950000:d['truncated']=True
  except Exception as e:
   if previous.get(id,{}).get('text'):
    old=previous[id];d.update(text=old['text'],retrievedAt=old.get('retrievedAt'),sha256=old.get('sha256'),status='stale')
   d['error']=str(e)[:220]
  return d
 out=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  for d in ex.map(fetch,rows):
   out.append(d)
   if len(out)%50==0:(root/'data'/'local-documents-progress.json').write_text(json.dumps(out,ensure_ascii=False))
   if len(out)%50==0:print(json.dumps({'processed':len(out),'total':len(rows),'indexed':sum(bool(x['text']) for x in out)}),flush=True)
 (root/'data'/'local-documents.json').write_text(json.dumps(out,ensure_ascii=False));print(json.dumps({'complete':len(out),'indexed':sum(bool(x['text']) for x in out)}),flush=True)
if __name__=='__main__':main()
