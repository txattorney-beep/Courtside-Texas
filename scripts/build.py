import pathlib,json,html,shutil,gzip,hashlib,datetime,re,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1];DIST=ROOT/'dist';ORIGIN='https://courtsidetexas.com';e=html.escape

def build():
 if DIST.exists():shutil.rmtree(DIST)
 shutil.copytree(ROOT/'public',DIST)
 biography=(ROOT/'public'/'biography.html').read_text()
 (DIST/'bio.js').write_text('window.COURTSIDE_BIO='+json.dumps(biography)+';')
 (DIST/'eric-hudson.jpg').unlink(missing_ok=True)
 cat=json.loads(gzip.decompress((DIST/'data'/'catalog.json.gz').read_bytes()))
 from business_catalog import add_business_courts
 cat=add_business_courts(ROOT,DIST,cat)
 from records_catalog import add_records_links,quick_links,court_links
 cat=add_records_links(DIST,cat)
 search_page=DIST/"search/index.html"
 search_page.write_text(search_page.read_text().replace("<!--RECORDS_PORTALS-->",quick_links()))
 urls=['/'];stamp=cat['status']['checkedAt'][:10]
 def link(url,label):return f'<a href="{e(url,quote=True)}" target="_blank" rel="noopener">{e(label)} ↗</a>' if url.startswith(('https://','http://')) else ''
 def page(path,title,desc,content,entity=None):
  context='courts' if path.startswith('/courts') else {'rules':'local','practice':'practice','administrative-rules':'admin','about':'about'}.get(path.strip('/'),'courts')
  search=f'<form action="/search/" role="search" class="site-search-form"><label class="visually-hidden" for="reference-search">Search all Courtside Texas</label><input type="search" id="reference-search" name="q" placeholder="Search courts, rules, news, and agencies…" maxlength="240"><input type="hidden" name="context" value="{context}"><button type="submit">Search</button></form><p class="site-search-hint">Searches all of Courtside, with this section first.</p>'
  target=DIST/path.strip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);urls.append(path)
  structured={'@context':'https://schema.org','@type':'WebPage','name':title,'description':desc,'url':ORIGIN+path,'publisher':{'@type':'Person','name':'Eric A. Hudson','url':ORIGIN+'/about/'}}
  if entity:structured['mainEntity']=entity
  target.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Courtside Texas</title><meta name="description" content="{e(desc,quote=True)}"><link rel="canonical" href="{ORIGIN+path}"><meta name="theme-color" content="#193e38"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/search.css"><script type="application/ld+json">{json.dumps(structured).replace('<',chr(92)+'u003c')}</script></head><body><main class="main details"><nav class="reference-nav"><a class="back-link" href="/">← Courtside Texas</a><a class="back-link" href="/news/">Legal news ↗</a></nav><h1 style="font-size:48px">{e(title)}</h1>{search}{content}<footer class="footer"><p>A resource by <a href="/about/">Eric A. Hudson</a>.  Verify current rules at their official source.  Directory checked {stamp}.</p><a href="/">Search the directory →</a></footer></main></body></html>''')
 for c in cat['courts']:
  ids={str(x) if str(x).startswith('oca-') else 'oca-'+str(x) for x in c.get('ruleDocumentIds',[])}
  for r in c.get('regionalRules',[]):ids.update('oca-'+str(x) for x in r['documentIds'])
  docs=[d for d in cat['documents'] if d['id'] in ids or c['id'] in d.get('courtIds',[])]
  jurisdiction=', '.join(c['counties']) or ', '.join(c['cities'])
  content=f'<p>{e(c["level"])} · {e(jurisdiction)}</p>'+(f'<p>Judge: {e(c["judge"])}</p>' if c.get('judge') else '')+f'<div class="toolbar">{link(c["url"],"Official court website")}{link(c["records"][0]["url"],"Records search")}</div><p>{e(c["records"][0]["note"])}</p><p><a class="primary" href="/?court={e(c["id"],quote=True)}">Open in searchable directory</a></p><h2>Local rules and regional rules</h2><p>Documents associated with this court or its administrative judicial region. Verify applicability to the relevant county and proceeding.</p><ul>'+''.join(f'<li>{link(d["sourceUrl"],d["title"])}</li>' for d in docs)+'</ul>'
  if not docs:content+='<p>No court-specific documents are linked in the current repository. Check the court website for local rules and standing orders.</p>'
  content+=court_links(c)
  content+='<h2>Court locations</h2>'+''.join(f'<p><strong>{e(l.get("county") or l.get("city") or "Location")}</strong><br>{e(l.get("address", ""))}<br>{e(l.get("city", ""))}, TX {e(l.get("zip", ""))}<br>{link(l["url"],"Location website") if l.get("url") else ""}</p>' for l in c.get('locations',[]))
  content+='<p>'+link(c['sourceUrl'],'Official directory source')+'</p>'
  page('/courts/'+c['id']+'/',c['name'],f'{c["name"]}: official website, docket portal, local rules, locations and court information. {jurisdiction}.',content,{'@type':'GovernmentOrganization','name':c['name'],'url':c['url']})
 courtlist=quick_links()+'<p>Texas Business Court divisions, state district and appellate courts, federal district courts, and the Fifth Circuit.</p><ul>'+''.join(f'<li><a href="/courts/{e(c["id"])}/">{e(c["name"])}</a> · {e(", ".join(c["counties"]) or c["level"])}</li>' for c in cat['courts'])+'</ul>'
 page('/courts/','Texas court directory','Browse Texas Business Court divisions, state district courts, state appellate courts, federal district courts, and the Fifth Circuit.',courtlist)
 for catname,path,title in [('local','rules','Texas local court rules'),('practice','practice','Federal and Texas civil practice rules')]:
  ds=[d for d in cat['documents'] if d['category']==catname];body='<p><a class="primary" href="/#'+('local' if catname=='local' else 'practice')+'">Search indexed rule text</a></p><ul>'+''.join(f'<li>{link(d["sourceUrl"],d["title"])} · {e(d.get("county") or d.get("jurisdiction") or "")}</li>' for d in ds)+'</ul>';page('/'+path+'/',title,'Official-source links and searchable rule collections for Texas litigation.',body)
 admin=cat['admin'];body='<p>'+link(admin['search_url'],'Search all Texas Administrative Code text')+'</p><ul>'+''.join(f'<li>{link(a["url"],a["name"])} · Title {a["title"]}, Part {a["part"]}</li>' for a in admin['agencies'])+'</ul>';page('/administrative-rules/','Texas administrative agency rules','All Texas Administrative Code titles and agency parts, with official links and statewide rule search.',body)
 page('/about/','Eric A. Hudson','Eric A. Hudson, litigation partner and creator of Courtside Texas.', '<p class="lead">Commercial litigation.  Trials. Arbitration. Appeals.</p>'+biography+'<p><a href="mailto:ehudson@atlawpllc.com">ehudson@atlawpllc.com</a> · <a href="/#about">About Courtside and contact information</a></p>')
 from news_page import build_news_page
 build_news_page(ROOT,DIST)
 from search_index import build_search_index
 build_search_index(ROOT,DIST,cat)
 urls.append('/news/')
 dates=sitemap_dates(urls,DIST,ROOT/'site')
 xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{ORIGIN+u}</loc><lastmod>{dates[u]}</lastmod></url>' for u in urls)+'</urlset>'
 # Catalog data and scripts must remain crawlable so engines can render the app.
 # Internal search results carry noindex,follow in their HTML, not a crawl block.
 (DIST/'sitemap.xml').write_text(xml);(DIST/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n');(DIST/'CNAME').write_text('courtsidetexas.com\n');(DIST/'.nojekyll').touch()
 (DIST/'404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found | Courtside Texas</title><link rel="stylesheet" href="/styles.css"><main class="main"><h1>Let’s get you to the right court.</h1><p>This page could not be found.</p><a class="primary" href="/">Search Courtside Texas</a></main></html>')
 version_assets(DIST)
 print(json.dumps({'pages':len(urls),'courts':len(cat['courts']),'sitemap':'dist/sitemap.xml'}))
def sitemap_dates(urls,dist,previous):
 """Keep lastmod stable until a page's content changes, not every build."""
 old={}
 if (previous/'sitemap.xml').exists():
  ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
  for entry in ET.parse(previous/'sitemap.xml').findall('s:url',ns):
   old[entry.findtext('s:loc',namespaces=ns)]=entry.findtext('s:lastmod',namespaces=ns)
 today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
 def normalized(path):
  return re.sub(r'/assets/([a-z-]+)\.[a-f0-9]{12}\.(js|css)',r'/\1.\2',path.read_text())
 result={}
 for url in urls:
  relative=url.strip('/')+'/index.html' if url!='/' else 'index.html'
  prior=previous/relative;last=old.get(ORIGIN+url)
  unchanged=prior.exists() and normalized(dist/relative)==normalized(prior)
  result[url]=last if unchanged and last else today
 return result

def version_assets(dist):
 built_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 files=['search-engine.js','search.js','search.css','app.js','bio.js','styles.css','news.js','news.css']
 version=hashlib.sha256(b''.join((dist/name).read_bytes() for name in files)+(ROOT/'public/sw.js').read_bytes()).hexdigest()[:16]
 mapping={}
 assets=dist/'assets';assets.mkdir(exist_ok=True)
 for name in files:
  source=(dist/name).read_text().replace('__COURTSIDE_RELEASE__',version).replace('__COURTSIDE_BUILT_AT__',built_at)
  for old,new in mapping.items():source=source.replace("'"+old+"'","'"+new+"'")
  (dist/name).write_text(source)
  digest=hashlib.sha256(source.encode()).hexdigest()[:12]
  stem,extension=name.rsplit('.',1);target=f'/assets/{stem}.{digest}.{extension}'
  (dist/target.lstrip('/')).write_text(source);mapping['/'+name]=target
 for page in dist.rglob('*.html'):
  content=page.read_text()
  for old,new in mapping.items():content=content.replace('"'+old+'"','"'+new+'"')
  page.write_text(content)
 worker=(dist/'sw.js').read_text().replace('__COURTSIDE_RELEASE__',version)
 for old,new in mapping.items():worker=worker.replace("'"+old+"'","'"+new+"'")
 (dist/'sw.js').write_text(worker)
 (dist/'release.json').write_text(json.dumps({'version':version,'builtAt':built_at}))

if __name__=='__main__':build()
