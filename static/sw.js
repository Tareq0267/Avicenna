// Service Worker for Avicenna App
// Bump this version on every deploy to bust caches
const CACHE_VERSION = 'v2.2.0';
const CACHE_NAME = 'avicenna-cache-' + CACHE_VERSION;
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/site.webmanifest',
  '/static/tracker/css/style.css',
];

// Install: cache assets and immediately take over
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Activate: delete all old caches and claim clients
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: network-first for navigation & CSS, cache-first for other assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Network-first for HTML pages and CSS (always get fresh)
  if (event.request.mode === 'navigate' || url.pathname.endsWith('.css')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-first for other static assets (images, fonts, JS libs)
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
