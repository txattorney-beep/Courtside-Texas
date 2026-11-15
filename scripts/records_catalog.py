"""Expose existing official court and clerk links without implying universal coverage."""
import gzip,json,html
PORTALS=[
 {'label':'PACER Case Locator','url':'https://pcl.uscourts.gov/pcl/index.jsf','note':'Nationwide federal case index. PACER account required; fees may apply.','sourceUrl':'https://pacer.uscourts.gov/find-case/search-national-index'},
 {'label':'re:SearchTX','url':'https://research.txcourts.gov/CourtRecordsSearch/Home','note':'Texas civil court records. Account required; coverage and document fees vary.','sourceUrl':'https://guides.sll.texas.gov/court-records/texas-courts'}
]
def add_records_links(dist,catalog):
 for c in catalog['courts']:
  links=[];seen=set()
  def add(url,label,kind,note=''):
   if not url.startswith(('https://','http://')) or url.rstrip('/') in seen:return
   seen.add(url.rstrip('/'));links.append({'url':url,'label':label,'kind':kind,'note':note})
  # County-specific alternatives lead when verified; otherwise use the court's existing official portal.
  for a in c.get('docketAlternatives',[]):add(a['url'],a.get('label') or a['county']+' County records','county',a.get('access',''))
  docket=c['docket'];host=docket['url']
  label='Court records · PACER / CM/ECF' if c['level'].startswith('Federal') else 'Court records · TAMES' if c['level']=='State appellate' else 'Court records · re:SearchTX' if 'research.txcourts.gov' in host else docket.get('label','Court records search')
  add(host,label,'statewide' if 'research.txcourts.gov' in host else 'court',docket.get('access',''))
  for clerk in c.get('clerks',[]):
   county=clerk['county'];directory='card.txcourts.gov' in clerk['url']
   add(clerk['url'],('Find '+county+' district clerk (OCA)' if directory else county+' County district clerk'),'clerk','Clerk information and records access. An online search may not be available.')
  c['records']=links
 catalog['recordPortals']=PORTALS
 (dist/'data/catalog.json.gz').write_bytes(gzip.compress(json.dumps(catalog,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
 return catalog

def quick_links():
 return '<nav class="records-shortcuts" aria-label="Court records portals"><strong>Records &amp; dockets</strong>'+''.join(f'<a href="{html.escape(p["url"],quote=True)}" target="_blank" rel="noopener">{html.escape(p["label"])} ↗</a>' for p in PORTALS)+'</nav>'

def court_links(c):
 return '<section class="court-records" id="records"><h2>Records &amp; docket search</h2><p>Use the court or county portal below. Clerk links provide records access information where a separate search portal is not listed.</p><ul>'+''.join(f'<li><a href="{html.escape(r["url"],quote=True)}" target="_blank" rel="noopener">{html.escape(r["label"])} ↗</a>{"<p>"+html.escape(r["note"])+"</p>" if r["note"] else ""}</li>' for r in c['records'])+'</ul>'+quick_links()+'</section>'
