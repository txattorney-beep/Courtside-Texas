import sys,pathlib,subprocess,concurrent.futures,os,tempfile,hashlib,json,time
ROOT=pathlib.Path(__file__).resolve().parents[2];CACHE=ROOT/'work'/'rules-cache';OUT=ROOT/'work'/'ocr-cache';OUT.mkdir(parents=True,exist_ok=True)
def extract(p):
 out=OUT/(p.stem+'.txt')
 if out.exists():return 'cached'
 try:
  s=subprocess.run(['pdftotext',str(p),'-'],capture_output=True,timeout=45).stdout.decode(errors='replace')
  if len(s.strip())>60:return 'text'
  with tempfile.TemporaryDirectory() as tmp:
   r=subprocess.run(['pdftoppm','-r','130','-gray','-png',str(p),tmp+'/p'],capture_output=True,timeout=180)
   if r.returncode:return 'error'
   pages=sorted(pathlib.Path(tmp).glob('p-*.png'));outtext=[]
   for image in pages:
    r=subprocess.run(['tesseract',str(image),'stdout','--psm','3'],capture_output=True,timeout=45,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    if r.returncode:raise ValueError('OCR failure')
    outtext.append(r.stdout.decode(errors='replace'))
   text='\n\f\n'.join(outtext)
   out.write_text(text)
   return 'ocr' if len(text.strip())>60 else 'empty'
 except Exception:return 'error'
def main():
 counts={}
 files=sorted(CACHE.glob('*.pdf'))
 manifest=ROOT/'data'/'local-documents.json'
 if manifest.exists():
  pending={d['id'].removeprefix('oca-') for d in json.loads(manifest.read_text()) if d.get('status')=='scan-only'}
  files=[p for p in files if p.stem in pending]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  for i,s in enumerate(ex.map(extract,files),1):
   counts[s]=counts.get(s,0)+1
   if i%50==0:print(json.dumps({'processed':i,**counts}),flush=True)
 print(json.dumps(counts),flush=True)
if __name__=='__main__':main()
