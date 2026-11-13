"""Unattended weekly refresh; publication happens only after validation succeeds."""
import pathlib,sys,json,gzip,shutil,subprocess,datetime,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'scripts'/'ingest'))
import state_courts,admin,federal,local_rules,ocr,assemble

def restore():
 p=ROOT/'public'/'data'/'catalog.json.gz';old=json.loads(gzip.decompress(p.read_bytes()));texts={}
 for path in old['status']['textShards']:
  for d in json.loads(gzip.decompress((ROOT/'public'/path.lstrip('/')).read_bytes())):texts[d['id']]=d['text']
 (ROOT/'data').mkdir(exist_ok=True);(ROOT/'data'/'seed-texts').mkdir(exist_ok=True)
 previous=[]
 for d in old['documents']:
  d['text']=texts.get(d['id'],'');previous.append(d)
  if not d['id'].startswith('oca-') and d['text']:(ROOT/'data'/'seed-texts'/(d['id']+'.txt')).write_text(d['text'])
 (ROOT/'data'/'documents.json').write_text(json.dumps(previous))
 return old

def run():
 old=restore();stage=ROOT/'work'/'state';stage.mkdir(parents=True,exist_ok=True)
 backup=ROOT/'data'/'court-rule-associations.json'
 if backup.exists():shutil.copyfile(backup,stage/backup.name)
 elif backup.with_suffix('.json.gz').exists():(stage/backup.name).write_bytes(gzip.decompress(backup.with_suffix('.json.gz').read_bytes()))
 courts,rows,associations=state_courts.run(stage)
 if len(courts)<530:raise ValueError('Court directory unexpectedly incomplete; preserve published snapshot')
 for f in ['state-courts.json','court-rule-associations.json','state-summary.json','rules-documents.json']:shutil.copyfile(stage/f,ROOT/'data'/f)
 try:result=admin.get_directory(ROOT/'work'/'admin');(ROOT/'data'/'administrative.json').write_text(json.dumps(result))
 except Exception as e:
  a=old['admin'];a['refreshError']=str(e);(ROOT/'data'/'administrative.json').write_text(json.dumps(a));print('TAC directory retained after failed refresh:',str(e))
 federal.run();local_rules.main();ocr.main();assemble.run()
 backup.with_suffix('.json.gz').write_bytes(gzip.compress(backup.read_bytes(),mtime=0))
 print('Refresh complete:',datetime.datetime.now(datetime.timezone.utc).isoformat())
if __name__=='__main__':run()
