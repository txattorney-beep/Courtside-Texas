"""Submit the published sitemap after verifying the public IndexNow key."""
import urllib.request,urllib.error,json,pathlib,xml.etree.ElementTree as ET,time
root=pathlib.Path(__file__).resolve().parents[1]
key=(root/'public'/'indexnow-key.txt').read_text().strip()
origin='https://courtsidetexas.com'
headers={'User-Agent':'CourtsideTexas/1.0 (+https://courtsidetexas.com)','Content-Type':'application/json; charset=utf-8'}
sitemap=root/'dist'/'sitemap.xml'
if not sitemap.exists():sitemap=root/'site'/'sitemap.xml'
urls=[e.text for e in ET.parse(sitemap).findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
key_url=origin+'/'+key+'.txt'
with urllib.request.urlopen(urllib.request.Request(key_url,headers=headers),timeout=30) as response:
 if response.read().decode().strip()!=key:raise ValueError('Published IndexNow key does not match')
payload={'host':'courtsidetexas.com','key':key,'keyLocation':key_url,'urlList':urls}
for attempt in range(3):
 try:
  request=urllib.request.Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers=headers)
  with urllib.request.urlopen(request,timeout=30) as response:
   print('IndexNow accepted:',response.status,'URLs:',len(urls));break
 except urllib.error.HTTPError as error:
  detail=error.read().decode(errors='replace')[:1000]
  print('IndexNow response:',error.code,detail)
  if error.code not in (403,429,500,502,503,504) or attempt==2:raise
  time.sleep(20)
