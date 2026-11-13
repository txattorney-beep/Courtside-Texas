"""Refresh Texas state court metadata and official TOPICs court/document associations.
No credentials or nonpublic records. Python 3 stdlib only. Use --output DIR.
TOPICs publishes live JSON endpoints consumed by its own public search UI.
"""
import argparse,collections,concurrent.futures,csv,datetime,html,io,json,pathlib,re,time,urllib.request,urllib.parse
SOURCE='https://card.txcourts.gov/directorysearch.aspx'
TOPICS='https://topics.txcourts.gov/LocalRulesPublic/'
RESEARCH='https://research.txcourts.gov/CourtRecordsSearch/'
TAMES='https://search.txcourts.gov/CaseSearch.aspx'
# Official district-record portal links listed by the Texas State Law Library.
# https://guides.sll.texas.gov/court-records/texas-courts (retrieved 2026-11-13)
COUNTY_DOCKETS={
 'El Paso':'https://www.epcounty.com/576/Records-Search',
 'Bexar':'https://www.bexar.org/3703/Records',
 'Collin':'https://www.collincountytx.gov/Services/case-information',
 'Dallas':'https://www.dallascounty.org/services/record-search/',
 'Denton':'https://justice1.dentoncounty.gov/PublicAccess/default.aspx',
 'Harris':'https://www.hcdistrictclerk.com/eDocs/Public/Search.aspx',
 'Tarrant':'https://www.tarrantcountytx.gov/en/district-clerk/services/district-clerk-court-document-lookup.html',
 'Travis':'https://odysseyweb.traviscountytx.gov/Portal'
}
PRACTICE_SOURCES={
 'tx-coa-6':'https://www.txcourts.gov/6thcoa/practice-before-the-court/',
 'tx-coa-12':'https://www.txcourts.gov/12thcoa/practice-before-the-court/',
 'tx-supreme':'https://txcourts.gov/supreme/practice-before-the-court.aspx',
 'tx-cca':'https://www.txcourts.gov/cca/practice-before-the-court/rules-procedures/'
}

def timestamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fetch(url,timeout=40):
 for attempt in range(2):
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'TexasCourtReference/1.0 (public legal reference directory)'})
   with urllib.request.urlopen(request,timeout=timeout) as r:
    if r.status!=200:raise ValueError('HTTP '+str(r.status))
    return r.read()
  except Exception:
   if attempt:raise
   time.sleep(.5)
def export_url(kind):
 return 'https://card.txcourts.gov/ExcelExportPublic.aspx?'+urllib.parse.urlencode({'type':'C','export':'E','SortBy':'tblCounty.Sort_ID, tblCourt.Court_Identifier','Active_Flg':'true','Court_Type_CD':kind,'Court_Sub_Type_CD':0,'County_ID':0,'City_CD':0,'Court':'','DistrictPrimaryLocOnly':0,'AdminJudicialRegion':0,'COADistrictId':0})
def parse_tsv(raw):
 lines=raw.decode('utf-8-sig').splitlines()
 if lines and lines[0].startswith('sep='):lines=lines[1:]
 rows=list(csv.DictReader(lines,delimiter='\t'))
 if not rows or 'Court' not in rows[0]:raise ValueError('Missing expected court directory columns')
 return [{k:(v or '').strip() for k,v in row.items() if k} for row in rows]
def slug(s):return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def district_key(name,county):
 return slug(name+(' '+county if name.lower().startswith('criminal') else ''))
def canonical_name(name):
 name=name.strip()
 if 'Court of Appeals' in name:
  m=re.search(r'(\d+)(?:st|nd|rd|th)',name)
  return ('coa'+m[1]) if m else name.lower()
 name=re.sub(r'\s+-\s+.+ County$','',name)
 return re.sub(r'\s+',' ',name).lower()
def normalize_courts(directory_rows,rules_court_rows,checked_at):
 groups={};clerks={}
 for row in directory_rows:
  name=row['Court'];typ=row['Court Type'];county=row['County']
  if typ=='District Clerk Office':clerks[county]=row;continue
  if typ not in ('District','District Criminal Court','Court of Appeals','Supreme Court','Court of Criminal Appeals'):continue
  if typ=='Court of Appeals':
   num=int(re.match(r'\d+',name)[0]);key='tx-coa-'+str(num);name=re.sub(r' \(.+\)$','',name)
  elif typ=='Supreme Court':key='tx-supreme';name='Supreme Court of Texas'
  elif typ=='Court of Criminal Appeals':key='tx-cca'
  else:key='tx-district-'+district_key(name,county)
  if key not in groups:
   docket={'url':RESEARCH,'label':'Search civil cases on re:SearchTX','access':'Account required; document fees may apply. Coverage varies. For criminal cases, use the county district clerk.'}
   if typ in ('Court of Appeals','Supreme Court','Court of Criminal Appeals'):
    coa='coa'+str(num).zfill(2) if typ=='Court of Appeals' else ('cossup' if typ=='Supreme Court' else 'coscca')
    docket={'url':TAMES+'?coa='+coa,'label':'Search appellate cases in TAMES','access':'Public case search. Records refresh nightly.'}
   groups[key]={'id':key,'name':name+(' · '+county+' County' if typ=='District Criminal Court' else ''),'courtType':typ,'level':'State appellate' if typ in ('Court of Appeals','Supreme Court','Court of Criminal Appeals') else 'State district','jurisdiction':'Texas','counties':[],'cities':[],'locations':[],'url':row['Website'] or SOURCE,'urlStatus':'directory-listed' if row['Website'] else 'directory-fallback','docket':docket,'sourceUrl':SOURCE,'checkedAt':checked_at,'rulesCourtIds':[],'ruleDocumentIds':[],'rulesStatus':'not-listed-in-oca-index'}
  court=groups[key]
  if county and county not in court['counties']:court['counties'].append(county)
  if row['City'] and row['City'] not in court['cities']:court['cities'].append(row['City'])
  court['locations'].append({'county':county,'city':row['City'],'url':row['Website'] or None,'address':row['Address'],'zip':row['Zip Code'],'phone':row['Phone'],'email':row['Email'],'sourceName':row['Court']})
 index={}
 for court in groups.values():
  for loc in court['locations']:index[(canonical_name(loc['sourceName']),loc['county'])]=court
 for row in rules_court_rows:
  name,county,group,typ,oid=row
  if group not in ('District','COA'):continue
  court=index.get((canonical_name(name),county))
  if court:
   court['rulesCourtIds'].append(str(oid));court['rulesStatus']='pending'
 for court in groups.values():
  court['counties'].sort();court['cities'].sort()
  available=next((loc['url'] for loc in court['locations'] if loc['url']),None)
  if available:court['url']=available;court['urlStatus']='directory-listed'
  court['docketAlternatives']=[{'county':c,'url':COUNTY_DOCKETS[c],'label':c+' County court records','access':'Official county portal; sign-in and document availability vary.','sourceUrl':('https://www.epcounty.com/576/Records-Search' if c=='El Paso' else 'https://guides.sll.texas.gov/court-records/texas-courts')} for c in court['counties'] if c in COUNTY_DOCKETS]
  if court['id'] in PRACTICE_SOURCES:court['practiceUrl']=PRACTICE_SOURCES[court['id']]
  if court['id']=='tx-coa-6':court['rulesNote']='The Sixth Court states that it has no local rules. Its practice policies are available on its official practice page.'
  court['clerks']=[{'county':c,'url':clerks[c]['Website'] or SOURCE,'phone':clerks[c]['Phone']} for c in court['counties'] if c in clerks]
  if court['courtType']=='District Criminal Court':
   county=court['counties'][0]
   court['docket']={'url':COUNTY_DOCKETS.get(county,clerks.get(county,{}).get('Website') or SOURCE),'label':'County criminal records access','access':'Official county portal. Search availability, sign-in and document access vary; contact the district clerk if needed.'}
 return list(groups.values())
def parse_ajr(raw):
 rows=[]
 for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw.decode('utf-8-sig'),re.S|re.I):
  cells=[html.unescape(re.sub(r'<[^>]+>',' ',td)).strip() for td in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S|re.I)]
  if len(cells)==8 and cells[-1].isdigit() and cells[4]=='Judge':rows.append(cells)
 if len(rows)<400:raise ValueError('Unexpected administrative region judge directory')
 return rows
def attach_ajr(courts,ajr_rows,associations,county_ajr_rows=None):
 court_index={c['id']:c for c in courts}
 regions={}
 for a in associations:
  if a['group']=='AJR':
   match=re.search(r'(\d+)',a['courtName'])
   if match:regions[int(match[1])]=a
 for row in ajr_rows:
  typ,name,county,judge,title,address,phone,region=row
  court=court_index.get('tx-district-'+district_key(name,county))
  if not court:continue
  court['judge']=' '.join(judge.split())
  primary=next((loc for loc in court['locations'] if loc['county']==county),None)
  if primary and primary['url']:court['url']=primary['url'];court['urlStatus']='directory-listed'
  court['primaryAdministrativeRegion']=int(region)
  court['judgeSourceUrl']='https://card.txcourts.gov/ajrdata.aspx?ct=55'
 county_regions={}
 for row in county_ajr_rows or []:county_regions[row[2]]=int(row[-1])
 for court in courts:
  by_region={}
  for county in court['counties']:
   if county in county_regions:by_region.setdefault(county_regions[county],[]).append(county)
  court['administrativeRegions']=sorted(by_region)
  court['regionalRules']=[]
  for region,counties in sorted(by_region.items()):
   if region in regions:
    a=regions[region]
    court['regionalRules'].append({'region':region,'counties':counties,'name':a['courtName'],'url':a['url'],'documentIds':a['documentIds'],'status':a['status']})
 return courts
def fetch_association(row,cache_dir=None):
 name,county,group,typ,oid=row;oid=str(oid);url=TOPICS+'DocumentDetailsForCourt/'+oid
 result={'ocaCourtId':oid,'courtName':name.strip(),'county':county,'group':group,'type':typ,'url':url,'checkedAt':timestamp(),'documentIds':[]}
 try:
  data=fetch(url).decode('utf-8-sig')
  if 'Document(s) for ' not in data:raise ValueError('Unexpected court detail markup')
  if cache_dir:(cache_dir/(oid+'.html')).write_text(data)
  result['documentIds']=sorted(set(re.findall(r'/LocalRulesPublic/PreviewAttachment/(\d+)',data)),key=int)
  result['status']='ok' if result['documentIds'] else 'no-documents-posted'
 except Exception as exc:result.update(status='fetch-failed',error=str(exc)[:250])
 return result
def attach_associations(courts,associations):
 by_id={a['ocaCourtId']:a for a in associations}
 for c in courts:
  aa=[by_id[i] for i in c['rulesCourtIds'] if i in by_id]
  c['ruleDocumentIds']=sorted(set(d for a in aa for d in a['documentIds']),key=int)
  if c['rulesCourtIds']:
   statuses=[a['status'] for a in aa]
   c['rulesStatus']='fetch-failed' if 'fetch-failed' in statuses or len(aa)!=len(c['rulesCourtIds']) else ('indexed' if c['ruleDocumentIds'] else 'no-documents-posted')
  c['localRulesUrls']=[TOPICS+'DocumentDetailsForCourt/'+i for i in c['rulesCourtIds']]
 return courts
def write_json(path,data):
 path=pathlib.Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')));tmp.replace(path)
def run(output,refresh_directory=True,refresh_associations=True):
 output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True);checked=timestamp();rows=[]
 for kind,name in [(55,'district'),(1558,'coa'),(1557,'cca'),(1543,'scot')]:
  path=output/(name+'-export.tsv')
  if refresh_directory or not path.exists():path.write_bytes(fetch(export_url(kind)))
  rows+=parse_tsv(path.read_bytes())
 ajr_path=output/'ajr.html'
 if refresh_directory or not ajr_path.exists():ajr_path.write_bytes(fetch('https://card.txcourts.gov/ajrdata.aspx?ct=55'))
 ajr_rows=parse_ajr(ajr_path.read_bytes())
 county_ajr_path=output/'ajr-counties.html'
 if refresh_directory or not county_ajr_path.exists():county_ajr_path.write_bytes(fetch('https://card.txcourts.gov/ajrdata.aspx?ct=54'))
 county_ajr_rows=parse_ajr(county_ajr_path.read_bytes())
 rules_courts=json.loads(fetch(TOPICS+'GetAllCourtsWithLocalRules'))['data'];documents=json.loads(fetch(TOPICS+'GetAllLocalRuleDocuments'))['data']
 write_json(output/'rules-courts.json',rules_courts);write_json(output/'rules-documents.json',{'data':documents})
 courts=normalize_courts(rows,rules_courts,checked);write_json(output/'state-courts.json',courts)
 targets=[r for r in rules_courts if r[2] in ('District','COA','AJR')]
 cache_dir=output/'court-pages';cache_dir.mkdir(exist_ok=True)
 assoc_path=output/'court-rule-associations.json';associations=[]
 old_associations={}
 if assoc_path.exists():
  try:old_associations={a['ocaCourtId']:a for a in json.loads(assoc_path.read_text())}
  except (ValueError,KeyError):pass
 if not refresh_associations and assoc_path.exists():associations=json.loads(assoc_path.read_text())
 else:
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   for n,result in enumerate(pool.map(lambda r:fetch_association(r,cache_dir),targets),1):
    if result['status']=='fetch-failed' and result['ocaCourtId'] in old_associations:
     old=old_associations[result['ocaCourtId']]
     result['documentIds']=old.get('documentIds',[])
     result['lastSuccessfulCheck']=old.get('lastSuccessfulCheck',old.get('checkedAt'))
     result['usingPreviousAssociations']=True
    associations.append(result)
    if n%25==0:
     write_json(assoc_path,associations);print('court associations',n,'/',len(targets),flush=True)
 write_json(assoc_path,associations);courts=attach_ajr(attach_associations(courts,associations),ajr_rows,associations,county_ajr_rows);write_json(output/'state-courts.json',courts)
 summary={'checkedAt':checked,'districtCourts':sum(c['level']=='State district' for c in courts),'appellateCourts':sum(c['level']=='State appellate' for c in courts),'courtLocations':sum(len(c['locations']) for c in courts),'districtCounties':len({n for c in courts if c['level']=='State district' for n in c['counties']}),'rulesDocuments':len(documents),'rulesIndexCourts':len(rules_courts),'associations':dict(collections.Counter(a['status'] for a in associations)),'courtRulesStatus':dict(collections.Counter(c['rulesStatus'] for c in courts))}
 matched={i for c in courts for i in c['rulesCourtIds']}
 summary['unmatchedRulesCourts']=[{'name':r[0],'county':r[1],'ocaCourtId':str(r[4])} for r in rules_courts if r[2] in ('District','COA') and str(r[4]) not in matched]
 summary['courtWebsiteStatus']=dict(collections.Counter(c['urlStatus'] for c in courts))
 write_json(output/'state-summary.json',summary);print(json.dumps(summary,indent=2),flush=True);return courts,documents,associations
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default=str(pathlib.Path(__file__).parent));p.add_argument('--use-cached-directory',action='store_true');p.add_argument('--use-cached-associations',action='store_true');a=p.parse_args();run(a.output,not a.use_cached_directory,not a.use_cached_associations)
