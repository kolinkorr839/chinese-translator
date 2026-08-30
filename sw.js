const CACHE_NAME = 'chinese-translator-v3';
const STATIC_ASSETS = [
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './mandarin_translation.html',
  './mandarin_flashcards.html',
  './mandarin_flashcards_2.html',
  './pinyin_chart.html',
  './pinyin_guide.html',
  './grammar_guide.html',
  './grammar_flashcards.html',
  './mandarin_in_14_days.html',
  './simplified_to_traditional_guide.html',
  './simplified_to_traditional_cheat_sheet.html',
  './simplified_traditional_flashcards.html',
  'https://cdn.jsdelivr.net/npm/pinyin-pro@3/dist/index.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  if (url.hostname === 'translate.googleapis.com' || url.hostname === 'translate.google.com') {
    e.respondWith(fetch(e.request));
    return;
  }

  if (e.request.url.endsWith('/index.html') || e.request.url.endsWith('/')) {
    e.respondWith(
      fetch(e.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return resp;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
