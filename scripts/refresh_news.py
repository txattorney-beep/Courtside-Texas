"""Public RSS headlines only. No article scraping, paywall access or generated news."""
import datetime as dt,email.utils,html,json,pathlib,re,urllib.request,urllib.parse,xml.etree.ElementTree as ET,concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parents[1];DATA=ROOT/'public/data';UA='CourtsideTexas/1.0 (+https://courtsidetexas.com; public news links)'
FEEDS=[
 {'name':'The Texas Tribune','url':'https://feeds.texastribune.org/feeds/main/','category':'Texas','kind':'Reporting','filter':r'\b(court|courts|lawsuit|lawsuits|judge|judges|attorney|legal|litigation|ruling|injunction|appeals?|justices?|judicial|prosecutor|prosecution|indictment|sentenc\w+|jury)\b','domains':['texastribune.org']},
 {'name':'State Bar of Texas','url':'https://blog.texasbar.com/feed/','category':'Practice','kind':'Bar news','domains':['blog.texasbar.com']},
 {'name':'U.S. Court of Appeals for the Fifth Circuit','url':'https://www.ca5.uscourts.gov/feeds/opinions','category':'Fifth Circuit','kind':'Opinion','domains':['ca5.uscourts.gov']},
 {'name':'U.S. Court of Appeals for the Fifth Circuit','url':'https://www.ca5.uscourts.gov/feeds/news','category':'Fifth Circuit','kind':'Court announcement','domains':['ca5.uscourts.gov']}
]
SOURCES=[{'name':n,'url':u} for n,u in [('Fifth Circuit opinions','https://www.ca5.uscourts.gov/opinions'),('Supreme Court of Texas','https://www.txcourts.gov/supreme/orders-opinions/'),('Court of Criminal Appeals','https://www.txcourts.gov/cca/opinions/'),('The Texas Tribune','https://www.texastribune.org/'),('Texas Public Radio','https://www.tpr.org/'),('Texas Bar Blog','https://blog.texasbar.com/'),('Texas Lawyer','https://www.law.com/texaslawyer/'),('The Texas Lawbook','https://texaslawbook.net/'),('How Appealing','https://howappealing.abovethelaw.com/')]]
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def canonical(url):
 p=urllib.parse.urlsplit(url);q=urllib.parse.parse_qsl(p.query)
 q=[(k,v) for k,v in q if not k.startswith('utm_') and k not in ['output','ref','source']]
 return urllib.parse.urlunsplit((p.scheme,p.netloc.lower(),p.path,urllib.parse.urlencode(q),''))
def parsedate(s):
 try:d=email.utils.parsedate_to_datetime(s)
 except Exception:d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
 return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d

def collect(source,now):
 records=[];status={'source':source['name'],'feed':source['url'],'checkedAt':now.isoformat()}
 try:
  req=urllib.request.Request(source['url'],headers={'User-Agent':UA})
  with urllib.request.urlopen(req,timeout=25) as r:tree=ET.fromstring(r.read(5_000_000))
  entries=tree.findall('.//item')
  if not entries:raise ValueError('Feed has no RSS items')
  for entry in entries[:60]:
   title=clean(entry.findtext('title'));url=(entry.findtext('link') or '').strip();description=clean(entry.findtext('description'))
   try:published=parsedate(entry.findtext('pubDate') or entry.findtext('{http://purl.org/dc/elements/1.1/}date') or '')
   except Exception:continue
   if re.search(r'finalizes? divorce',title,re.I):continue
   if not title or not url.startswith(('http://','https://')) or not now-dt.timedelta(days=30)<=published<=now+dt.timedelta(hours=12):continue
   if source.get('filter') and not re.search(source['filter'],title+' '+description,re.I):continue
   host=urllib.parse.urlsplit(url).hostname or ''
   if host.startswith('feeds.') or not any(host==d or host.endswith('.'+d) for d in source['domains']):
    try:
     with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA},method='HEAD'),timeout=12) as r:url=r.url
    except Exception:continue
   host=urllib.parse.urlsplit(url).hostname or ''
   if not any(host==d or host.endswith('.'+d) for d in source['domains']):continue
   kind=source['kind']
   if kind=='Opinion':kind='Unpublished opinion' if '/unpub/' in url else 'Published opinion' if '/pub/' in url else 'Court opinion'
   records.append({'title':title,'url':canonical(url),'publisher':source['name'],'date':published.date().isoformat(),'category':source['category'],'kind':kind})
  status.update(success=True,items=len(records))
 except Exception as error:status.update(success=False,error=str(error)[:200])
 return records,status

def run():
 now=dt.datetime.now(dt.timezone.utc);path=DATA/'news.json';old=json.loads(path.read_text()) if path.exists() else {'articles':[]};merged={}
 for a in old['articles']:
  if 0<=(now.date()-dt.date.fromisoformat(a['date'][:10])).days<=30 and not (urllib.parse.urlsplit(a['url']).hostname or '').startswith('feeds.') and not re.search(r'finalizes? divorce',a['title'],re.I):merged[canonical(a['url'])]=a
 statuses=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for rows,status in pool.map(lambda source:collect(source,now),FEEDS):
   statuses.append(status)
   for row in rows:merged[canonical(row['url'])]=row
 for a in json.loads((DATA/'news-seed.json').read_text()):
  if 0<=(now.date()-dt.date.fromisoformat(a['date'][:10])).days<=30 and not (urllib.parse.urlsplit(a['url']).hostname or '').startswith('feeds.') and not re.search(r'finalizes? divorce',a['title'],re.I):merged[canonical(a['url'])]=a
 if not any(s.get('success') for s in statuses):raise RuntimeError('All news feeds failed; retain the last published edition')
 ordered=sorted(merged.values(),key=lambda a:a['date'],reverse=True);articles=[]
 for category in ['Texas','Fifth Circuit','Practice']:
  group=[x for x in ordered if x['category']==category]
  if category=='Fifth Circuit':
   curated={x['url'] for x in json.loads((DATA/'news-seed.json').read_text())}
   group.sort(key=lambda x:(x['url'] in curated,x['kind']=='Published opinion',x['kind']=='Court announcement',x['date']),reverse=True)
  articles.extend(group[:12 if category=='Fifth Circuit' else 18])
 if not articles:raise ValueError('No recent headlines; retain prior publication')
 result={'checkedAt':now.isoformat(),'articles':articles,'sources':SOURCES,'feedStatus':statuses}
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'articles':len(articles),'sources':statuses}));return result
if __name__=='__main__':run()
