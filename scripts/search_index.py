"""Build the same cross-site search snapshot on every publishing/refresh run."""
import gzip, json, re, html

def build_search_index(root, dist, catalog):
    records=[]
    def add(**record):
        record.setdefault('body','')
        record.setdefault('keywords','')
        records.append(record)
    court_docs={d['id']:set(d.get('courtIds',[])) for d in catalog['documents']}
    for c in catalog['courts']:
        ids={str(x) if str(x).startswith('oca-') else 'oca-'+str(x) for x in c.get('ruleDocumentIds',[])}
        ids.update('oca-'+str(x) for r in c.get('regionalRules',[]) for x in r['documentIds'])
        for did in ids:
            if did in court_docs: court_docs[did].add(c['id'])
        places=' · '.join(c.get('cities',[])+c.get('counties',[]))
        add(id=c['id'],kind='courts',title=c['name'],url='/courts/'+c['id']+'/',sourceUrl=c['url'],recordUrl=c['records'][0]['url'],recordLabel=c['records'][0]['label'],
            detail=c['level']+(' · '+places if places else ''),body=' '.join(filter(None,[c.get('judge'),places])),
            keywords=' '.join([c.get('shortName',''),c['level'],*c.get('aliases',[])]))
    for d in catalog['documents']:
        add(id=d['id'],kind=d['category'],title=d['title'],url='/?document='+d['id']+'#'+d['category'],
            sourceUrl=d['sourceUrl'],detail=' · '.join(filter(None,[d.get('county') or d.get('jurisdiction'),d.get('documentType'),d.get('versionNote')])),
            status=d.get('status','link-only'),courtIds=sorted(court_docs[d['id']]),keywords=d.get('courtGroup',''))
    for a in catalog['admin']['agencies']:
        add(id=a['id'],kind='admin',title=a['name'],url=a['url'],detail=f'Title {a["title"]} · {a["title_name"]} · Part {a["part"]}',
            body='Agency directory entry. Full administrative rule text is searched at the official Texas Secretary of State portal.',
            keywords='Texas Administrative Code TAC agency rules '+''.join(w[0] for w in a['name'].split() if w.lower() not in {'of','the','and','on'}))
    for a in catalog['admin']['titles']:
        add(id=a['id'],kind='admin',title=a['name'],url=a['url'],detail=f'Texas Administrative Code · Title {a["number"]}',keywords='TAC administrative rules')
    news=json.loads((dist/'data/news.json').read_text())
    for i,a in enumerate(news['articles']):
        add(id='news-'+str(i),kind='news',title=a['title'],url=a['url'],detail=a['publisher']+' · '+a['date'],
            keywords=' '.join([a['publisher'],a['category'],a.get('kind','')]),date=a['date'])
    for i,p in enumerate(catalog['recordPortals']):
        add(id='records-portal-'+str(i),kind='pages',title=p['label'],url=p['url'],detail='Court records & docket search',body=p['note'],keywords='records dockets case search PACER' if i==0 else 'records dockets case search research tx re search texas')
    bio=html.unescape(re.sub('<[^>]+>',' ',(root/'public/biography.html').read_text()))
    add(id='about',kind='pages',title='About Eric A. Hudson',url='/about/',detail='The lawyer behind Courtside Texas',body=' '.join(bio.split()))
    add(id='sources',kind='pages',title='Sources, coverage & updates',url='/#sources',detail='Official sources and weekly updates',body='Court directory, local rule indexing, civil practice rules, administrative agency directory, docket access and retrieval coverage.')
    add(id='desk',kind='pages',title='My Courts & downloadable directory',url='/#desk',detail='Your personal court list',body='Save favorite courts, import or export your court list, download the portable offline directory, install on your phone.')
    texts=[]
    for shard in catalog['status']['textShards']:
        texts.extend({'id':d['id'],'text':' '.join(d['text'].split())} for d in json.loads(gzip.decompress((dist/shard.lstrip('/')).read_bytes())))
    def write(name,data):
        (dist/'data'/name).write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    write('search-index.json.gz',{'records':records,'checkedAt':catalog['status']['checkedAt'],'newsCheckedAt':news['checkedAt']})
    write('search-text.json.gz',texts)
