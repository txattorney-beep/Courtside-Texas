import urllib.request,json,pathlib,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parents[1];key=(root/'public'/'indexnow-key.txt').read_text().strip();tree=ET.parse(root/'dist'/'sitemap.xml');urls=[e.text for e in tree.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
payload={'host':'courtsidetexas.com','key':key,'keyLocation':'https://courtsidetexas.com/indexnow-key.txt','urlList':urls}
try:
 with urllib.request.urlopen(urllib.request.Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json; charset=utf-8'}),timeout=30) as r:print('IndexNow notification status:',r.status,'URLs:',len(urls))
except Exception as e:print('IndexNow notification was not accepted:',str(e));raise
