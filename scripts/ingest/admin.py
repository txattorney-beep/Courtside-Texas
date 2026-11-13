#!/usr/bin/env python3
"""Discover the public Texas Administrative Code title/agency directory.
Uses ordinary read-only public Appian UI GET data URLs observed in portal HTML.
No credentials. This does not claim to download all rule text.
"""
import urllib.request, urllib.parse, re, json, concurrent.futures, datetime, pathlib, time
BASE='https://texas-sos.appianportalsgov.com/rules-and-meetings'
def request(url,headers=None):
 return urllib.request.urlopen(urllib.request.Request(url,headers=headers or {'User-Agent':'CourtsideTexas/1.0 (public legal reference directory)'}),timeout=40).read()
def get_headers():
 page=request(BASE+'?interface=VIEW_TAC').decode()
 jsurl=re.search(r'<script src="([^"]+\.js)"',page).group(1)
 js=request(jsurl).decode()
 flags=int(re.search(r'BigInt\("(0b[01]+)"',js).group(1),2)
 return {'Accept':'application/vnd.appian.tv.ui+json','Content-Type':'application/vnd.appian.tv+json','X-Appian-Ui-State':'stateful','X-Appian-Features':format(flags&0x7fffffff,'x'),'X-Appian-Features-Extended':format(flags,'x'),'x-appian-suppress-www-authenticate':'true','User-Agent':'CourtsideTexas/1.0 (public legal reference directory)'}
def fetch_ui(headers,**params):
 query=urllib.parse.urlencode({'interface':'VIEW_TAC',**params})
 for attempt in range(3):
  try: return json.loads(request(BASE+'/_/ui?'+query,headers))
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
def rich_items(x):
 if isinstance(x,dict):
  if x.get('#t')=='RichTextItem':yield x
  for v in x.values():yield from rich_items(v)
 elif isinstance(x,list):
  for v in x:yield from rich_items(v)
def label(x):return ''.join(str(z.get('#v','')) for z in x.get('text',[]) if isinstance(z,dict)).strip()
def get_directory(output_dir):
 output_dir=pathlib.Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
 headers=get_headers(); root=fetch_ui(headers)
 rows=list(rich_items(root['ui']));titles=[]
 for i,row in enumerate(rows):
  m=re.fullmatch(r'TITLE (\d+)',label(row))
  if m and i+1<len(rows):titles.append({'id':'tac-title-'+m[1],'number':int(m[1]),'name':label(rows[i+1]).title(),'url':BASE+'?interface=VIEW_TAC&title='+m[1]})
 def get_parts(t):
  j=fetch_ui(headers,title=t['number']); (output_dir/f'title-{t["number"]}.json').write_text(json.dumps(j))
  rows=list(rich_items(j['ui']));parts=[]
  for i,r in enumerate(rows):
   m=re.fullmatch(r'PART (\d+)',label(r))
   if m and i+1<len(rows):parts.append({'id':f'tac-{t["number"]}-{m[1]}','title':t['number'],'title_name':t['name'],'part':int(m[1]),'name':label(rows[i+1]).title(),'url':BASE+f'?interface=VIEW_TAC&title={t["number"]}&part={m[1]}','search_url':BASE+'?interface=SEARCH_TAC','status':'official-directory','text_indexed':False})
  return parts
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  groups=list(pool.map(get_parts,titles))
 result={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'publisher':'Texas Secretary of State','source_url':'https://www.sos.texas.gov/tac/index.shtml','browse_url':BASE+'?interface=VIEW_TAC','search_url':BASE+'?interface=SEARCH_TAC','scope':'Complete current title and agency/part directory returned by the official portal; rule text remains searchable at official source.','titles':titles,'agencies':[r for g in groups for r in g]}
 result['register']={'name':'Texas Register','url':'https://www.sos.texas.gov/texreg/index.shtml','current_html_url':'https://www.sos.state.tx.us/texreg/sos/','current_pdf_index_url':'https://www.sos.texas.gov/texreg/pdf/currview/index.shtml','archive_url':'https://www.sos.texas.gov/texreg/archive/index.shtml','rss_url':'https://www.sos.state.tx.us/texreg/texreg.xml','note':'Rulemaking notices and proposed or emergency rules are distinct from codified rules currently in effect.'}
 if len(titles)<17 or len(result['agencies'])<100:raise ValueError('Unexpectedly incomplete official TAC directory; preserve prior snapshot')
 (output_dir/'administrative.json').write_text(json.dumps(result,indent=2));print(json.dumps({'titles':len(titles),'agency_parts':len(result['agencies']),'output':str(output_dir/'administrative.json')}),flush=True)
 return result
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',default=str(pathlib.Path(__file__).parent));a=p.parse_args();get_directory(a.output)
