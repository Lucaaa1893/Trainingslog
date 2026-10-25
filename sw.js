// Offline-Cache für den Trainingslog. VERSION erhöhen, wenn sich Dateien ändern.
const VERSION = 25;
const CACHE = 'trainingslog-v' + VERSION;
const CORE = ['./', './index.html', './manifest.json', './icon2-180.png', './icon2-192.png', './icon2-512.png'];

self.addEventListener('install', e => {
  // cache:'reload' umgeht den Browser-Zwischenspeicher, damit wirklich die neue Version geladen wird
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.all(CORE.map(u => fetch(new Request(u, { cache:'reload' })).then(r => r.ok && c.put(u, r)).catch(() => {}))))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // App-Seite: immer frisch aus dem Netz (ohne Zwischenspeicher), offline aus dem Cache
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req.url, { cache:'no-store' }).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put('./index.html', copy)); }
      return r;
    }).catch(() => caches.match('./index.html').then(h => h || caches.match('./'))));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r && r.ok && url.origin === location.origin) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return r;
  })));
});
