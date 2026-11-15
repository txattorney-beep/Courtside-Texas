/* Shared by the search worker, accessible result rendering and regression checks. */
(function(root){
'use strict';
const groups={courts:'Courts',local:'Local rules',practice:'Practice rules',news:'Legal news',admin:'Administrative rules',pages:'About & site information'};
const contexts={courts:'Courts first',desk:'Courts first',local:'Local rules first',practice:'Practice rules first',news:'News first',admin:'Administrative rules first',about:'Site information first',sources:'Site information first'};
const generic=new Set(['court','courts','rule','rules','news','legal','local','texas','state','federal','practice','docket','dockets']);
const stop=new Set(['a','an','and','are','at','by','for','from','in','is','of','on','the','to','with','find','search','show','me']);
function normalize(value){return String(value||'').toLowerCase().replace(/\b5th\b/g,'fifth').replace(/\b1st\b/g,'first').replace(/\b2nd\b/g,'second').replace(/\b3rd\b/g,'third');}
function tokens(query){return [...new Set((normalize(query).match(/[\p{L}\p{N}]+/gu)||[]).filter(t=>!stop.has(t)))].slice(0,20);}
function pattern(term){return new RegExp('\\b'+term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+(term.endsWith('s')?'':'s?')+'\\b','i');}
function prepare(records){return records.map(r=>({...r,_title:normalize(r.title),_meta:normalize((r.detail||'')+' '+(r.keywords||'')),_body:normalize(r.body)}));}
function matchingCourtIds(courts,query){const records=prepare(courts.map(c=>({id:c.id,kind:'courts',title:c.name,detail:[c.shortName,c.level,c.judge,...(c.aliases||[]),...(c.cities||[]),...(c.counties||[])].filter(Boolean).join(' ')})));return new Set(run(records,query,'courts').groups.flatMap(g=>g.items.map(r=>r.id)));}
function attachTexts(records,texts){const byId=new Map(texts.map(t=>[t.id,t.text]));for(const r of records){if(byId.has(r.id)){r.body=byId.get(r.id);r._body=normalize(r.body);r.fullText=true;}}}
function excerpt(text,terms,length=310){text=String(text||'').replace(/\s+/g,' ').trim();const matches=terms.map(t=>text.search(pattern(t))).filter(i=>i>=0);const phrase=normalize(text).indexOf(terms.join(' '));const start=Math.max(0,(phrase>=0?phrase:matches.length?Math.min(...matches):0)-80);return (start?'…':'')+text.slice(start,start+length)+(start+length<text.length?'…':'');}
function highlight(text,query){const ts=tokens(query);const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));if(!ts.length)return escape(text);const rx=new RegExp('\\b('+ts.sort((a,b)=>b.length-a.length).map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+(t.endsWith('s')?'':'s?')).join('|')+')\\b','gi');let out='',last=0;String(text).replace(rx,(match,...args)=>{const at=args[args.length-2];out+=escape(String(text).slice(last,at))+'<mark>'+escape(match)+'</mark>';last=at+match.length;return match;});return out+escape(String(text).slice(last));}
function run(records,query,context='courts'){
 const ts=tokens(query),topic=ts.filter(t=>!generic.has(t)),required=topic.length?topic:ts,checks=required.map(pattern),allChecks=ts.map(pattern),hits=new Map(),phrases=['business court','fifth circuit','supreme court','district court','court of appeals','civil procedure'].filter(p=>normalize(query).includes(p));
 if(!required.length)return {groups:[],total:0,terms:ts};
 for(const r of records){
  const haystack=r._title+' '+r._meta+' '+r._body;
  if(!checks.every(p=>p.test(haystack))||!phrases.every(p=>haystack.includes(p)))continue;
  let score=checks.reduce((n,p)=>n+(p.test(r._title)?40:p.test(r._meta)?12:2),0)+allChecks.reduce((n,p)=>n+(p.test(r._title)?5:0),0);
  const phrase=normalize(query).trim();if(r._title.includes(phrase))score+=35;
  if(required.length>1&&r._body.includes(required.join(' ')))score+=8;
  hits.set(r.id,{id:r.id,kind:r.kind,title:r.title,url:r.url,sourceUrl:r.sourceUrl,detail:r.detail,status:r.status,date:r.date,fullText:!!r.fullText,score,snippet:excerpt(r.body,phrases.length?phrases[0].split(' '):required),courtIds:r.courtIds});
 }
 // Match a court through its linked rules too, without treating an unrelated court as a direct title match.
 const byId=new Map(records.filter(r=>r.kind==='courts').map(r=>[r.id,r]));
 for(const hit of [...hits.values()])if(hit.kind==='local')for(const id of hit.courtIds||[]){const c=byId.get(id);if(!c||hits.has(id))continue;hits.set(id,{id,kind:'courts',title:c.title,url:c.url,sourceUrl:c.sourceUrl,detail:c.detail,score:Math.min(20,hit.score/4),snippet:'Matching linked rule: '+hit.title,related:true});}
 const priority=({desk:'courts',about:'pages',sources:'pages'})[context]||context;
 const order=Object.keys(groups);if(order.includes(priority)){order.splice(order.indexOf(priority),1);order.unshift(priority);}
 const result=order.map(kind=>({kind,label:groups[kind],items:[...hits.values()].filter(r=>r.kind===kind).sort((a,b)=>b.score-a.score||(kind==='news'?(b.date||'').localeCompare(a.date||''):0)||a.title.localeCompare(b.title,undefined,{numeric:true}))})).filter(g=>g.items.length);
 return {groups:result,total:hits.size,terms:ts};
}
const api={groups,contexts,tokens,prepare,matchingCourtIds,attachTexts,run,highlight,excerpt};root.CourtsideSearch=api;if(typeof module!=='undefined')module.exports=api;
// Loading and full-text matching stay off the main thread, including on phones.
if(typeof importScripts==='function'&&typeof document==='undefined'){
 let metadataPromise,textPromise,records,latest=0;
 async function read(url){const response=await fetch(url,{cache:'no-cache'});if(!response.ok)throw new Error('Search data could not load');return JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());}
 function metadata(){if(!metadataPromise)metadataPromise=read('/data/search-index.json.gz').then(data=>{records=prepare(data.records);return records;}).catch(e=>{metadataPromise=null;throw e;});return metadataPromise;}
 function fulltext(){if(!textPromise)textPromise=read('/data/search-text.json.gz').then(texts=>attachTexts(records,texts)).catch(e=>{textPromise=null;throw e;});return textPromise;}
 root.onmessage=async({data})=>{latest=data.id;try{await metadata();if(data.id!==latest)return;root.postMessage({id:data.id,...run(records,data.query,data.context),loading:true});try{await fulltext();if(data.id===latest)root.postMessage({id:data.id,...run(records,data.query,data.context),loading:false});}catch{if(data.id===latest)root.postMessage({id:data.id,...run(records,data.query,data.context),loading:false,warning:'Full rule text could not load. These results cover titles, courts, news and agency entries. Retry to search the full rule text.'});}}catch{if(data.id===latest)root.postMessage({id:data.id,error:'Search data could not load. Check your connection and try again.'});}};
}
})(typeof self!=='undefined'?self:globalThis);
