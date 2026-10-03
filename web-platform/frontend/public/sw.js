const CACHE_NAME = 'dms-v2';
const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
];

function isCacheableStaticRequest(request) {
  if (request.method !== 'GET' || request.headers.has('Authorization')) return false;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return false;

  // Never cache API/authenticated data, document content, or signed URLs.
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/auth/') ||
    url.searchParams.has('token') ||
    url.searchParams.has('signature') ||
    url.searchParams.has('X-Amz-Signature')
  ) return false;

  // Cache only the explicit app shell and build-generated static assets.
  return APP_SHELL.includes(url.pathname) || url.pathname.startsWith('/assets/');
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (!isCacheableStaticRequest(request)) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => caches.delete(cacheName))
      )
    )
  );
});
