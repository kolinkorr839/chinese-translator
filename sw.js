// Bump this whenever STATIC_ASSETS changes, to force a fresh precache.
// HTML no longer needs a bump -- it is network-first (see the fetch handler).
const CACHE_NAME = 'chinese-translator-v5';
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
  'https://cdn.jsdelivr.net/npm/pinyin-pro@3.29.3/dist/index.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      // Per-asset instead of addAll: addAll is all-or-nothing, so a single
      // failure (the cross-origin CDN, say) would abort the install and leave
      // the site with no service worker at all.
      .then(cache => Promise.allSettled(STATIC_ASSETS.map(url => cache.add(url))))
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
  // Only GETs are cacheable; let anything else go straight to the network.
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  if (url.hostname === 'translate.googleapis.com' || url.hostname === 'translate.google.com') {
    e.respondWith(fetch(e.request));
    return;
  }

  // All HTML is network-first: a deploy is visible on the next load, and the
  // cache is only an offline fallback. Cache-first here would pin every page
  // until CACHE_NAME changed, so returning visitors would never see updates.
  const isHTML = e.request.mode === 'navigate'
    || url.pathname.endsWith('/')
    || url.pathname.endsWith('.html');

  if (isHTML) {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return resp;
      }).catch(() =>
        // ignoreSearch so a cache-busting ?v= query still matches the cached page.
        caches.match(e.request, { ignoreSearch: true })
          .then(cached => cached || caches.match('./index.html'))
      )
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
