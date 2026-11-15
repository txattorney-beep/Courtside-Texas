import pathlib,json,gzip,xml.etree.ElementTree as ET,re
ROOT=pathlib.Path(__file__).resolve().parents[1];p=ROOT/'dist';c=json.loads(gzip.decompress((p/'data'/'catalog.json.gz').read_bytes()));courts=c['courts'];docs=c['documents'];ids={x['id'] for x in courts};dids={x['id'] for x in docs}
assert len(ids)==len(courts)>=541
assert len([x for x in courts if x['level']=='State district'])>=519
assert len([x for x in courts if x['level']=='State appellate'])==17
assert len({n for x in courts for n in x['counties']})==254
assert all(x.get('docket',{}).get('url','').startswith(('https://','http://')) for x in courts)
assert len(c['admin']['titles'])>=17 and len(c['admin']['agencies'])>=100
assert len(docs)==len(dids)>=1400
texts={}
for f in c['status']['textShards']:
 for d in json.loads(gzip.decompress((p/f.lstrip('/')).read_bytes())):assert d['id'] in dids;texts[d['id']]=d['text']
assert len(texts)>600
assert 'summary judgment' in texts['txnd-local-civil'].lower()
for court in courts:
 assert (p/'courts'/court['id']/'index.html').exists()
 for doc in court.get('ruleDocumentIds',[]):assert ('oca-'+str(doc)) in dids
s=ET.parse(p/'sitemap.xml');urls=[x.text for x in s.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')];assert len(urls)>=547 and len(urls)==len(set(urls))
assert 'Sitemap: https://courtsidetexas.com/sitemap.xml' in (p/'robots.txt').read_text()
assert 'noindex' not in (p/'index.html').read_text()
assert all((p/x).exists() for x in ['app.js','styles.css','offline-template.html','brand-mark.svg','favicon.svg','indexnow-key.txt'])
news=json.loads((p/'data/news.json').read_text())
articles=news['articles'];news_urls=[a['url'] for a in articles]
assert articles and len(news_urls)==len(set(news_urls))
assert all(a['category'] in ['Texas','Fifth Circuit','Practice'] and a['title'] and a['publisher'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}',a['date']) and a['url'].startswith('https://') for a in articles)
assert news['feedStatus'] and any(source.get('success') for source in news['feedStatus'])
news_html=(p/'news/index.html').read_text()
from html import escape
assert all(escape(url,quote=True) in news_html for url in news_urls)
assert 'https://courtsidetexas.com/news/' in urls
bio=(ROOT/'public/biography.html').read_text()
assert bio in (p/'about/index.html').read_text()
assert json.loads((p/'bio.js').read_text().removeprefix('window.COURTSIDE_BIO=').removesuffix(';'))==bio
business=[x for x in courts if x['level']=='Business Court']
assert {x['division'] for x in business}=={1,3,4,8,11}
assert len(courts)>=546 and all(x['docket']['label']=='re:SearchTX' for x in business)
assert next(x for x in business if x['division']==3)['counties'].count('Bastrop')==1
assert 'Montgomery' in next(x for x in business if x['division']==11)['counties']
for court in business:
 assert len([d for d in docs if court['id'] in d.get('courtIds',[])])>=2
app=(p/'app.js').read_text()
assert 'class="news-shortcut" href="/news/"' in app
assert 'Business Court' in app and 'business-local-rules' in dids
for page in [p/'index.html',p/'about/index.html',p/'courts/index.html']:
 assert 'href="/news/"' in page.read_text()
 assert '/assets/styles.' in page.read_text()
assert re.search(r'src="/assets/app\.[a-f0-9]+\.js"',(p/'index.html').read_text())
assert '__COURTSIDE_RELEASE__' not in (p/'sw.js').read_text()
print(json.dumps({'passed':True,'courts':len(courts),'documents':len(docs),'searchable':len(texts),'sitemapPages':len(urls)}))
