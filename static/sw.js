// static/service-worker.js
// Service Worker for Avicenna App

const CACHE_NAME = 'avicenna-cache-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/site.webmanifest',
  '/static/sw.js',
  '/static/tracker/css/style.css',
  // Add more static assets as needed
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request);
      })
  );
});
