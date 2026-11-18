/** Public static files are versioned in the owner's GitHub repository. */
const ORIGIN='https://courtsidetexas.com';
const REPOSITORY='https://raw.githubusercontent.com/txattorney-beep/Courtside-Texas/main/site';
const TYPES={html:'text/html; charset=utf-8',js:'application/javascript; charset=utf-8',css:'text/css; charset=utf-8',json:'application/json; charset=utf-8',svg:'image/svg+xml',txt:'text/plain; charset=utf-8',xml:'application/xml; charset=utf-8',gz:'application/gzip',webmanifest:'application/manifest+json',png:'image/png',jpg:'image/jpeg'};
function isNews(path){return path==='/news/index.html'||path==='/data/news.json'}
function toBrowser(response,path,method){
 const headers=new Headers(response.headers);
 const fingerprinted=/^\/assets\/[^/]+\.[a-f0-9]{12}\.(js|css)$/.test(path);
 const fresh=/\.(html|js|css)$/.test(path)||path==='/release.json';
 headers.set('Cache-Control',isNews(path)?'no-store':fingerprinted?'public, max-age=31536000, immutable':fresh?'no-cache, max-age=0, must-revalidate':'public, max-age=120');
 return new Response(method==='HEAD'?null:response.body,{status:response.status,headers});
}
export default {
 async fetch(request,env,ctx){
  const url=new URL(request.url);
  if(url.hostname==='www.courtsidetexas.com'||url.protocol!=='https:')return Response.redirect(ORIGIN+url.pathname+url.search,301);
  if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers:{Allow:'GET, HEAD'}});
  let path;try{path=decodeURIComponent(url.pathname)}catch{return new Response('Bad request',{status:400})}
  if(path.includes('..')||path.includes('\\')||path.split('/').some(s=>s.startsWith('.'))||path.length>400)return new Response('Not found',{status:404});
  if(!path.split('/').pop().includes('.')){if(!path.endsWith('/'))return Response.redirect(ORIGIN+path+'/'+url.search,301);path+='index.html'}
  const extension=path.split('.').pop();if(!TYPES[extension])return new Response('Not found',{status:404});
  // Compatibility switch: older open tabs must never auto-reload on version mismatch.
  if(path==='/release.json')return new Response(request.method==='HEAD'?null:JSON.stringify({version:null,automaticReload:false}),{headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
  const news=isNews(path);
  const uncached=news||path==='/release.json'||path==='/sw.js';
  const key=new Request(ORIGIN+path,{method:'GET'});let cached=uncached?null:await caches.default.match(key);
  if(cached)return toBrowser(cached,path,request.method);
  const fallback=async()=>{const saved=await caches.default.match(new Request(ORIGIN+path+'?last-good-news=1'));if(!saved)return null;const r=toBrowser(saved,path,request.method);r.headers.set('X-Courtside-News','last-good-origin-unavailable');return r;};
  try{
   const upstream=await fetch(REPOSITORY+path+(uncached?'?courtside-refresh='+Math.floor(Date.now()/1000):''),{headers:{'User-Agent':'CourtsideTexas/1.0'},cf:{cacheTtl:uncached?0:120,cacheEverything:true}});
   if(!upstream.ok){if(news){const saved=await fallback();if(saved)return saved;}console.log(JSON.stringify({event:'origin_error',status:upstream.status,path}));return new Response(upstream.status===404?'Page not found. Visit https://courtsidetexas.com/':'Source temporarily unavailable. Please retry shortly.',{status:upstream.status===404?404:503,headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}})}
   const headers=new Headers({'Content-Type':TYPES[extension],'Cache-Control':'public, max-age=120','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin','Strict-Transport-Security':'max-age=31536000; includeSubDomains','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' https://static.wixstatic.com data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'",'Permissions-Policy':'camera=(), microphone=(), geolocation=()'});
   if(news)headers.set('X-Courtside-News','origin-checked');
   if(upstream.headers.get('etag'))headers.set('ETag',upstream.headers.get('etag'));
   const response=new Response(upstream.body,{status:200,headers});if(news){const saved=response.clone();saved.headers.set('Cache-Control','public, max-age=604800');ctx.waitUntil(caches.default.put(new Request(ORIGIN+path+'?last-good-news=1'),saved));}
   if(!uncached)ctx.waitUntil(caches.default.put(key,response.clone()));return toBrowser(response,path,request.method);
  }catch(e){if(news){const saved=await fallback();if(saved)return saved;}console.log(JSON.stringify({event:'origin_failure',path}));return new Response('Temporarily unavailable. Please retry shortly.',{status:503,headers:{'Cache-Control':'no-store'}})}
 }
};
