const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),zlib=require('node:zlib');
const engine=require('../public/search-engine.js');
const read=name=>JSON.parse(zlib.gunzipSync(fs.readFileSync('dist/data/'+name)));
const snapshot=read('search-index.json.gz');
const records=engine.prepare(snapshot.records);
engine.attachTexts(records,read('search-text.json.gz'));

test('business court rules finds all five divisions and related rules',()=>{
 const result=engine.run(records,'business court rules','courts');
 assert.equal(result.groups[0].kind,'courts');
 assert.equal(result.groups[0].items.filter(r=>r.title.includes('Business Court')).length,5);
 assert.ok(result.groups.find(g=>g.kind==='local').items.some(r=>r.id==='business-local-rules'));
 assert.equal(result.groups[0].items.slice(0,5).filter(r=>r.title.includes('Business Court')).length,5);
});
test('priority changes group order, never the results included',()=>{
 const court=engine.run(records,'business court rules','courts');
 for(const [context,first] of [['local','local'],['desk','courts']]){
  const result=engine.run(records,'business court rules',context);
  assert.equal(result.groups[0].kind,first);
  assert.equal(result.total,court.total);
 }
});
test('news is first when searching from the news desk, with courts and rules retained',()=>{
 const result=engine.run(records,'Fifth Circuit','news');
 assert.equal(result.groups[0].kind,'news');
 assert.ok(result.groups.some(g=>g.kind==='courts'));
 assert.ok(result.groups.some(g=>g.kind==='local'));
});
test('a matching business headline is included even when the query also asks for rules',()=>{
 const sample=engine.prepare([{id:'story',kind:'news',title:'Texas Business Court adopts new procedures',detail:'Official court update',url:'https://example.com'}]);
 assert.equal(engine.run(sample,'business court rules','courts').total,1);
});
test('full rule text is matched and the excerpt includes the query',()=>{
 const result=engine.run(records,'summary judgment','practice');
 assert.equal(result.groups[0].kind,'practice');
 const rule=result.groups.find(g=>g.kind==='local').items.find(r=>r.id==='txnd-local-civil');
 assert.ok(rule?.fullText);assert.match(rule.snippet,/summary judgment/i);
});
test('full text matches link back to the associated court',()=>{
 const result=engine.run(records,'summary judgment','courts');
 assert.equal(result.groups[0].kind,'courts');
 assert.ok(result.groups[0].items.some(r=>r.id==='txnd'&&r.related));
});
test('all sections including agency entries, site biography and saved court help are searchable',()=>{
 assert.equal(engine.run(records,'Environmental Quality','admin').groups[0].kind,'admin');
 assert.ok(engine.run(records,'Hudson','about').groups[0].items.some(r=>r.id==='about'));
 assert.ok(engine.run(records,'download directory','sources').groups[0].items.some(r=>r.id==='desk'));
});
test('ordinal aliases work, no-result and punctuation-only queries are safe',()=>{
 assert.ok(engine.run(records,'5th Circuit','courts').groups[0].items.some(r=>r.id==='ca5'));
 assert.equal(engine.run(records,'zzzzquasarunlikely','courts').total,0);
 for(const q of ['', '?!', 'the and of'])assert.equal(engine.run(records,q).total,0);
});
test('highlighting safely escapes user-controlled text',()=>{
 assert.equal(engine.highlight('<script>business</script> & court','business court'), '&lt;script&gt;<mark>business</mark>&lt;/script&gt; &amp; <mark>court</mark>');
});
test('all documents, courts, news and agency entries are represented exactly once',()=>{
 const catalog=read('catalog.json.gz');
 assert.equal(records.filter(r=>r.kind==='courts').length,catalog.courts.length);
 assert.equal(records.filter(r=>['local','practice'].includes(r.kind)).length,catalog.documents.length);
 assert.equal(records.filter(r=>r.kind==='admin').length,catalog.admin.titles.length+catalog.admin.agencies.length);
 assert.equal(records.filter(r=>r.kind==='news').length,JSON.parse(fs.readFileSync('dist/data/news.json')).articles.length);
 assert.equal(new Set(records.map(r=>r.id)).size,records.length);
});
test('every static reference page has a full-site form and news prioritizes news',()=>{
 for(const [page,context] of [['courts','courts'],['rules','local'],['practice','practice'],['administrative-rules','admin'],['about','about'],['news','news']]){
  const html=fs.readFileSync('dist/'+page+'/index.html','utf8');
  assert.match(html,/action="\/search\/"/);
  assert.ok(html.includes('name="context" value="'+context+'"'));
 }
 assert.ok(fs.existsSync('dist/search/index.html'));
});
test('fingerprinted search page and worker use the same versioned engine',()=>{
 const html=fs.readFileSync('dist/search/index.html','utf8');
 const engineAsset=html.match(/src="(\/assets\/search-engine\.[^\"]+)"/)[1];
 const ui=fs.readFileSync('dist/search.js','utf8');
 assert.ok(ui.includes("new Worker('"+engineAsset+"')"));
 assert.ok(fs.existsSync('dist'+engineAsset));
});

const vm=require('node:vm');
test('the court-page fallback itself finds business courts when the query includes rules',()=>{
 const app=fs.readFileSync('public/app.js','utf8');
 const fn=app.split('\n').find(line=>line.startsWith('function courtResults()'));
 const context={window:{CourtsideSearch:engine},catalog:read('catalog.json.gz'),query:'business court rules',view:'courts',saved:new Set(),filter:'all',county:''};
 vm.createContext(context);vm.runInContext(fn+';this.matches=courtResults()',context);
 assert.equal(context.matches.length,5);
 assert.ok(context.matches.every(c=>c.level==='Business Court'));
 context.county='Harris';vm.runInContext('this.matches=courtResults()',context);assert.equal(context.matches.length,1);
});
test('back and forward navigation routes legacy queries to the full-site search',()=>{
 const app=fs.readFileSync('public/app.js','utf8');
 const handler=app.slice(app.indexOf("window.addEventListener('popstate'"),app.indexOf("window.addEventListener('beforeinstallprompt'"));
 let callback,redirect;
 const context={URLSearchParams,window:{addEventListener:(_,fn)=>{callback=fn;}},location:{search:'?q=business+court+rules',hash:''},routes:{courts:'Court directory'},searchAll:(q,replace)=>redirect={q,replace},render:()=>assert.fail('A legacy query must not render court-only results')};
 vm.createContext(context);vm.runInContext(handler,context);callback();
 assert.deepEqual(redirect,{q:'business court rules',replace:true});
});
function workerHarness(cached){
 const calls={reads:0,writes:0,fetches:[]};
 const ctx={Request,Response,Headers,URL,console,module:{exports:{}},caches:{default:{match:async()=>{calls.reads++;return cached?.clone();},put:async()=>{calls.writes++;}}},fetch:async(url,options)=>{calls.fetches.push({url,options});return new Response('content');}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('cloudflare/worker.js','utf8').replace('export default','module.exports ='),ctx);
 return {worker:ctx.module.exports,calls,wait:{waitUntil:()=>{}}};
}
test('cached HTML is revalidated by browsers even if the stored response had a four-hour TTL',async()=>{
 const {worker,calls,wait}=workerHarness(new Response('old edge response',{headers:{'Cache-Control':'public, max-age=14400'}}));
 const r=await worker.fetch(new Request('https://courtsidetexas.com/'),{},wait);
 assert.equal(r.headers.get('Cache-Control'),'no-cache, max-age=0, must-revalidate');
 assert.equal(calls.fetches.length,0);
});
test('release and service worker checks bypass edge cache; fingerprinted assets remain cacheable',async()=>{
 for(const path of ['/release.json','/sw.js']){
  const {worker,calls,wait}=workerHarness(new Response('stale'));
  const r=await worker.fetch(new Request('https://courtsidetexas.com'+path),{},wait);
  assert.equal(calls.reads,0);assert.equal(calls.writes,0);assert.equal(calls.fetches[0].options.cf.cacheTtl,0);
  assert.match(r.headers.get('Cache-Control'),/must-revalidate/);
 }
 const {worker,wait}=workerHarness(new Response('script'));
 const r=await worker.fetch(new Request('https://courtsidetexas.com/assets/app.123456abcdef.js'),{},wait);
 assert.equal(r.headers.get('Cache-Control'),'public, max-age=31536000, immutable');
});

test('every court exposes records links in its static page and search result',()=>{
 const catalog=read('catalog.json.gz');
 for(const court of catalog.courts){
  assert.ok(court.records.length>0,court.id);
  assert.ok(court.records.every(r=>/^https?:\/\//.test(r.url)),court.id);
  const page=fs.readFileSync('dist/courts/'+court.id+'/index.html','utf8');
  assert.ok(page.includes('id="records"'),court.id);
  assert.ok(page.includes('Records search'),court.id);
  const result=records.find(r=>r.id===court.id);
  assert.equal(result.recordUrl,court.records[0].url,court.id);
 }
});
test('records shortcuts and county/clerk alternatives survive building and portable export',()=>{
 const catalog=read('catalog.json.gz');
 assert.ok(catalog.recordPortals.some(p=>p.url==='https://pcl.uscourts.gov/pcl/index.jsf'));
 assert.ok(catalog.recordPortals.some(p=>p.label==='re:SearchTX'));
 const harris=catalog.courts.find(c=>c.level==='State district'&&c.counties.length===1&&c.counties[0]==='Harris');
 assert.ok(harris.records[0].url.includes('hcdistrictclerk.com'));
 assert.ok(harris.records.some(r=>r.url.includes('research.txcourts.gov')));
 const rural=catalog.courts.find(c=>c.level==='State district'&&c.records.some(r=>r.kind==='clerk'));
 assert.ok(rural);
 const app=fs.readFileSync('public/app.js','utf8');
 assert.ok(app.includes('recordPortals:catalog.recordPortals'));
 const offline=fs.readFileSync('dist/offline-template.html','utf8');
 assert.ok(offline.includes('All records links')&&offline.includes('DATA.recordPortals'));
 for(const path of ['news/index.html','search/index.html','courts/index.html']){
  const page=fs.readFileSync('dist/'+path,'utf8');
  assert.ok(page.includes('PACER Case Locator')&&page.includes('re:SearchTX'),path);
 }
});

test('release checks never downgrade a new page or enter a reload loop',async()=>{
 const app=fs.readFileSync('public/app.js','utf8');
 const fn=app.split('\n').find(line=>line.startsWith('async function checkRelease()'));
 let latest={version:'old',builtAt:'2026-11-14T12:00:00Z'},reloads=0;
 const storage=new Map();
 const context={navigator:{onLine:true},document:{visibilityState:'visible'},releaseCheckRunning:false,APP_RELEASE:'current',APP_BUILT_AT:'2026-11-15T12:00:00Z',fetch:async()=>({ok:true,json:async()=>latest}),sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},location:{reload:()=>reloads++},$:()=>null,Date};
 vm.createContext(context);vm.runInContext(fn,context);
 await context.checkRelease();assert.equal(reloads,0);
 latest={version:'new',builtAt:'2026-11-16T12:00:00Z'};
 await context.checkRelease();await context.checkRelease();assert.equal(reloads,1);
});
