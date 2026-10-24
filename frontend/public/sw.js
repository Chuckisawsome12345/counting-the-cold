/* Counting the Cold: service worker for offline phone mode.
 *
 * - App shell: the page and its built files are cached when the worker installs, so the app opens with no signal.
 * - API: network first, with the last few /api/point answers (and the small /api/* lists) kept for when the signal drops.
 *   A saved answer served because the network failed carries the header `x-ctc-offline: 1`, which the app turns into
 *   its "offline, as of [date]" banner.
 * - Map tiles and fonts: kept as they are seen, so the places you have looked at still draw.
 *
 * Bump VERSION when this file changes so old caches are dropped.
 */
const VERSION = 'v1'
const SHELL = `ctc-shell-${VERSION}`
const DATA = `ctc-data-${VERSION}`
const TILES = `ctc-tiles-${VERSION}`

const MAX_POINTS = 5 // last-viewed orchards kept
const MAX_TILES = 300
const SLOW_NETWORK_MS = 6000 // weak signal counts as offline once a saved answer exists

const isApi = (url) => url.pathname.startsWith('/api/')
const isPoint = (url) => url.pathname === '/api/point'
const isTile = (url) => url.hostname.endsWith('tile.openstreetmap.org')
const isFont = (url) => url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com'

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL)
      // The page and the hashed files it loads. They were fetched before this worker took control, so fetch them again.
      const html = await (await fetch('/', { cache: 'reload' })).text()
      const built = [...html.matchAll(/(?:src|href)="(\/[^"]+\.(?:js|css|svg|png|webmanifest))"/g)].map((m) => m[1])
      await cache.addAll(['/', ...new Set(built)])
      await self.skipWaiting()
    })(),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL, DATA, TILES])
      for (const name of await caches.keys()) if (!keep.has(name)) await caches.delete(name)
      await self.clients.claim()
    })(),
  )
})

// A copy of a saved response, marked so the app knows it is not live.
async function offlineCopy(response) {
  const headers = new Headers(response.headers)
  headers.set('x-ctc-offline', '1')
  return new Response(await response.blob(), { status: response.status, statusText: response.statusText, headers })
}

async function trimPoints(cache) {
  const keys = (await cache.keys()).filter((r) => isPoint(new URL(r.url)))
  for (const old of keys.slice(0, Math.max(0, keys.length - MAX_POINTS))) await cache.delete(old)
}

async function latestPoint(cache) {
  const keys = (await cache.keys()).filter((r) => isPoint(new URL(r.url)))
  return keys.length ? cache.match(keys[keys.length - 1]) : undefined
}

// Network first; if the network fails or is slow and a saved copy exists, serve that.
async function networkFirst(request, cacheName, { point = false } = {}) {
  const cache = await caches.open(cacheName)
  const network = fetch(request).then(async (response) => {
    if (response.ok) {
      await cache.delete(request) // delete first so the newest answer is last in the list
      await cache.put(request, response.clone())
      if (point) await trimPoints(cache)
    }
    return response
  })
  network.catch(() => {}) // a late failure after we already answered from the cache is not an error
  const slow = new Promise((_, reject) => setTimeout(() => reject(new Error('slow')), SLOW_NETWORK_MS))
  try {
    return await Promise.race([network, slow])
  } catch {
    const saved = (await cache.match(request)) ?? (point ? await latestPoint(cache) : undefined)
    if (saved) return offlineCopy(saved)
    return network
  }
}

// The page itself: network first, keeping the newest copy for offline.
async function navigation(request) {
  const cache = await caches.open(SHELL)
  try {
    const response = await Promise.race([
      fetch(request),
      new Promise((_, reject) => setTimeout(() => reject(new Error('slow')), SLOW_NETWORK_MS)),
    ])
    if (response.ok) await cache.put('/', response.clone())
    return response
  } catch {
    return (await cache.match('/')) ?? Response.error()
  }
}

// Built files have hashed names, so a cached one never goes stale.
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  const saved = await cache.match(request)
  if (saved) return saved
  const response = await fetch(request)
  if (response.ok) await cache.put(request, response.clone())
  return response
}

// Show what we have now, refresh it for next time.
async function staleWhileRevalidate(request, cacheName, limit) {
  const cache = await caches.open(cacheName)
  const saved = await cache.match(request)
  const refresh = fetch(request)
    .then(async (response) => {
      if (response.ok || response.type === 'opaque') {
        await cache.put(request, response.clone())
        if (limit) {
          const keys = await cache.keys()
          for (const old of keys.slice(0, Math.max(0, keys.length - limit))) await cache.delete(old)
        }
      }
      return response
    })
    .catch(() => undefined)
  return saved ?? (await refresh) ?? Response.error()
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)

  if (isApi(url)) {
    event.respondWith(networkFirst(request, DATA, { point: isPoint(url) }))
  } else if (isTile(url)) {
    event.respondWith(staleWhileRevalidate(request, TILES, MAX_TILES))
  } else if (isFont(url)) {
    event.respondWith(staleWhileRevalidate(request, SHELL))
  } else if (url.origin === self.location.origin) {
    if (request.mode === 'navigate') event.respondWith(navigation(request))
    else event.respondWith(cacheFirst(request, SHELL))
  }
})
