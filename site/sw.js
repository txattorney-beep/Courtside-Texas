/* Cache the pocket directory for offline access; prefer live sources when online. */
const CACHE='courtside-b1707ff5f8e49cca';
const SHELL=['/','/assets/app.93c398523b64.js','/assets/search-engine.b113c7630c34.js','/assets/bio.47077794217d.js','/assets/styles.96038fe18e7d.css','/brand-mark.svg','/favicon.svg','/data/catalog.json.gz','/offline-template.html'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('courtside-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin)return;
 event.respondWith((async()=>{
  const cache=await caches.open(CACHE);
  try{const response=await fetch(event.request,{cache:'no-cache'});if(response.ok){event.waitUntil(cache.put(event.request,response.clone()));return response}const previous=await cache.match(event.request);return previous||response}
  catch(error){const previous=await cache.match(event.request);if(previous)return previous;if(event.request.mode==='navigate')return (await cache.match('/'))||Response.error();return Response.error()}
 })());
});
