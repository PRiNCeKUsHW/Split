/* FlatSplit service worker — cache version {{ version }}
 *
 * Money data must never be served stale while the flat's machine is
 * reachable, so pages are network-first and the cache is only a fallback for
 * when the host is switched off. Static assets are cache-first: WhiteNoise
 * gives them stable URLs, so a cached copy is always correct.
 */
const CACHE = "flatsplit-v{{ version }}";
const STATIC_PREFIX = "{{ static_url }}";
const OFFLINE_URL = "/offline/";

const PRECACHE = [
  OFFLINE_URL,
  STATIC_PREFIX + "css/app.css",
  STATIC_PREFIX + "vendor/bootstrap.min.css",
  STATIC_PREFIX + "vendor/bootstrap.bundle.min.js",
  STATIC_PREFIX + "vendor/htmx.min.js",
  STATIC_PREFIX + "vendor/alpine.min.js",
  STATIC_PREFIX + "fonts/grotesk-var.woff2",
  STATIC_PREFIX + "fonts/plex-mono-400.woff2",
  STATIC_PREFIX + "fonts/plex-mono-600.woff2",
  STATIC_PREFIX + "icons/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/admin/")) return;

  if (url.pathname.startsWith(STATIC_PREFIX)) {
    event.respondWith(
      caches.match(request).then((hit) => hit || fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
        return response;
      }))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request).then((hit) => hit || caches.match(OFFLINE_URL)))
  );
});
