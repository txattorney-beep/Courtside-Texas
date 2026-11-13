"""Assemble an explicitly labeled public-source snapshot and gzip search shards."""
import pathlib,json,datetime,gzip,hashlib,subprocess,html
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run():
 data=ROOT/'data';out=ROOT/'public'/'data';out.mkdir(parents=True,exist_ok=True)
 courts=json.loads((data/'state-courts.json').read_text());fed=json.loads((data/'federal-sources.json').read_text());admin=json.loads((data/'administrative.json').read_text());docs=[]
 for c in fed['courts']:
  courts.append({'id':c['id'],'name':c['name'],'shortName':c.get('shortName'),'level':c['kind'],'jurisdiction':'Federal','counties':[],'cities':c.get('divisions',[]),'url':c['website'],'urlStatus':'official','docket':{'url':c['docketUrl'],'label':'PACER / CM/ECF','access':c['docketAccess']},'docketAlternatives':[],'localRulesUrls':[c['rulesPage']],'ruleDocumentIds':[],'locations':[],'sourceUrl':c['directorySource'],'checkedAt':c['verifiedDate'],'sourceNote':c.get('directCheckNote','')})
 for d in fed['rules']:
  p=ROOT/d['textPath'] if d.get('textPath') else None;text=html.unescape(p.read_text()) if p and p.exists() else ''
  st='stale' if text and d.get('lastRetrievalFailed') else 'cached-source' if d['retrieval']=='indexed-source-text' else 'indexed' if text else 'link-only'
  docs.append({'id':d['id'],'title':d['title'],'category':'local' if d['group']=='local' else 'practice','documentType':'Local Rules' if d['group']=='local' else 'Practice Rules','courtIds':d.get('courtIds',[]),'jurisdiction':'Texas' if d['id'] in {'trcp','trap','tre','trja'} else 'Federal','sourceUrl':d['url'],'sourcePage':d['sourcePage'],'checkedAt':d['checkedAt'],'retrievedAt':d.get('retrievedAt',d['checkedAt']) if text else None,'status':st,'note':d.get('note',''),'versionNote':d.get('versionNote',''),'text':text,'sha256':d.get('sha256')})
 local=data/'local-documents.json'
 if local.exists():localdocs=json.loads(local.read_text())
 else:
  rows=json.loads((data/'rules-documents.json').read_text())['data'];now=datetime.datetime.now(datetime.timezone.utc).isoformat();localdocs=[]
  for r in rows:
   if not any(t in r[4] for t in ['District','COA','AJR','Business Court']):continue
   typ,title,posted,county,group,sub,identifier=r;p=ROOT/'work'/'rules-cache'/(identifier+'.pdf');text=''
   if p.exists():
    try:text=subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,timeout=30).stdout.decode(errors='replace').strip()
    except Exception:pass
   localdocs.append({'id':'oca-'+identifier,'title':title,'category':'local','documentType':typ,'county':county,'courtGroup':group,'sourceUrl':'https://topics.txcourts.gov/LocalRulesPublic/PreviewAttachment/'+identifier,'sourcePage':'https://topics.txcourts.gov/LocalRulesPublic/CourtDetailsForDocument/'+identifier,'postedDate':posted,'checkedAt':now,'retrievedAt':now if p.exists() else None,'status':'indexed' if len(text)>60 else 'scan-only' if p.exists() else 'unavailable','text':text[:950000]})
 for d in localdocs:
  ocr=ROOT/'work'/'ocr-cache'/(d['id'].removeprefix('oca-')+'.txt')
  if len(d.get('text','').strip())<60 and ocr.exists():
   text=ocr.read_text().strip()
   if len(text)>60:d.update(text=text[:950000],status='ocr')
 docs+=localdocs
 courts.sort(key=lambda c:(c['level'],c['name']))
 if len(courts)<541 or len({c['id'] for c in courts})!=len(courts):raise ValueError('Court directory completeness/uniqueness failed')
 if len(docs)<1400:raise ValueError('Incomplete document manifest')
 textdocs=[{'id':d['id'],'text':d.pop('text')} for d in docs if d.get('text')]
 for d in docs:d.pop('text',None)
 shards=[]
 for old in out.glob('text-*.json.gz'):old.unlink()
 for i in range(0,len(textdocs),50):
  payload=json.dumps(textdocs[i:i+50],ensure_ascii=False,separators=(',',':')).encode();name='text-'+str(i//50)+'.json.gz';(out/name).write_bytes(gzip.compress(payload,mtime=0));shards.append('/data/'+name)
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();status={'checkedAt':now,'textShards':shards,'courts':len(courts),'documents':len(docs),'indexedDocuments':len(textdocs),'refreshStatus':'Full source report available below. Source availability varies.','schedule':'0 12 * * 1','timezone':'UTC'}
 result={'courts':courts,'documents':docs,'admin':admin,'status':status}
 (out/'catalog.json.gz').write_bytes(gzip.compress(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode(),mtime=0));(out/'catalog.json').unlink(missing_ok=True)
 print(json.dumps({'courts':len(courts),'documents':len(docs),'textDocuments':len(textdocs),'textBytes':sum(len(d['text']) for d in textdocs),'shards':len(shards)}))
 return result
if __name__=='__main__':run()
