// @odoo-module ignore
/* eslint-disable no-restricted-globals */
/* global VERSION, PRECACHE_URLS */
// VERSION and PRECACHE_URLS are prepended by the controller serving this file.

const CACHE_PREFIX = "preventa-";
const CACHE_NAME = `${CACHE_PREFIX}${VERSION}`;
const APP_PATH = "/preventa";
const NETWORK_ONLY = [`${APP_PATH}/api/`, `${APP_PATH}/link`, `${APP_PATH}/service-worker.js`];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) =>
            Promise.all(
                PRECACHE_URLS.map((url) =>
                    cache.add(new Request(url, { cache: "reload" })).catch((error) => {
                        console.warn("[preventa sw] precache failed", url, error);
                    })
                )
            )
        )
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        (async () => {
            const names = await caches.keys();
            await Promise.all(
                names
                    .filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
            await self.clients.claim();
        })()
    );
});

const cacheFirst = async (request, cacheKey) => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(cacheKey || request, { ignoreSearch: Boolean(cacheKey) });
    if (cached) {
        return cached;
    }
    const response = await fetch(request);
    if (response.ok && response.type === "basic") {
        cache.put(cacheKey || request, response.clone());
    }
    return response;
};

self.addEventListener("fetch", (event) => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== "GET" || url.origin !== self.location.origin) {
        return;
    }
    if (NETWORK_ONLY.some((prefix) => url.pathname.startsWith(prefix))) {
        return;
    }
    if (url.pathname === APP_PATH || url.pathname === `${APP_PATH}/`) {
        event.respondWith(cacheFirst(request, APP_PATH));
        return;
    }
    if (
        url.pathname.startsWith("/web/assets/") ||
        url.pathname.startsWith("/web/static/") ||
        url.pathname.startsWith(APP_PATH)
    ) {
        event.respondWith(cacheFirst(request));
    }
});

self.addEventListener("message", (event) => {
    if (event.data === "SKIP_WAITING") {
        self.skipWaiting();
    }
});
