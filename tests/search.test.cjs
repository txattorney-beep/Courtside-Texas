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
