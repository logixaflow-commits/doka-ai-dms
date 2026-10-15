// Enterprise DMS Service Worker - Hybrid Caching Strategy
const CACHE_VERSION = 'v5';
const STATIC_CACHE_NAME = `dms-static-${CACHE_VERSION}`;
const API_CACHE_NAME = `dms-api-${CACHE_VERSION}`;
const MAX_CACHE_SIZE = 50 * 1024 * 1024; // 50MB max cache size
const STATIC_CACHE_TTL = 30 * 24 * 60 * 60 * 1000; // 30 days in ms
const API_CACHE_TTL = 10 * 60 * 1000; // 10 minutes in ms

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/dashboard',
    '/login',
    '/offline',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/dashboard.js',
    '/static/js/fetch_helper.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    '/static/icons/icon-96x96.png',
    '/static/manifest.json',
    // Add CDN assets
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome',
    'https://fonts.googleapis.com'
];

// API endpoints that should NOT be cached (for security)
const NO_CACHE_PATTERNS = [
    '/api/auth',
    '/api/documents/upload',
    '/api/documents/bulk',
    '/api/admin',
    '/documents/', // Document previews
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        }).catch((error) => {
            console.error('Failed to cache static assets:', error);
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches and enforce size limit
self.addEventListener('activate', (event) => {
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            cleanupOldCaches(),
            // Enforce cache size limit
            enforceCacheSizeLimit()
        ])
    );
    self.clients.claim();
});

// Fetch event - handle requests with hybrid caching strategy
self.addEventListener('fetch', ( event) => {
    const url = new URL(event.request.url);
    
    // Handle document previews - Network First with NO cache (security)
    if (url.pathname.startsWith('/documents/') && !url.pathname.endsWith('/documents')) {
        handleDocumentPreview(event);
        return;
    }
    
    // Handle sensitive API calls - Network First, no cache
    if (shouldSkipCache(url.pathname)) {
        handleNoCacheRequest(event);
        return;
    }
    
    // Handle API calls - Network First with fallback to cache (10min TTL)
    if (url.pathname.startsWith('/api/')) {
        handleAPIRequest(event);
        return;
    }
    
    // Handle static assets - Cache First with 30-day expiry
    handleStaticAsset(event);
});

// Check if request should skip cache
function shouldSkipCache(pathname) {
    return NO_CACHE_PATTERNS.some(pattern => pathname.includes(pattern));
}

// Handle document previews - Network First, NO cache
function handleDocumentPreview(event) {
    event.respondWith(
        fetch(event.request).catch(() => {
            // Return error page or offline fallback
            return caches.match('/offline');
        })
    );
}

// Handle sensitive API calls - Network First, no cache
function handleNoCacheRequest(event) {
    event.respondWith(
        fetch(event.request).catch(() => {
            return new Response(JSON.stringify({ error: 'Network error' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            });
        })
    );
}

// Handle API calls - Network First with fallback to cache (10min TTL)
function handleAPIRequest(event) {
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Cache successful GET API responses
                if (response.ok && event.request.method === 'GET') {
                    const responseClone = response.clone();
                    caches.open(API_CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Fall back to cache if network fails
                return caches.match(event.request).then((cached) => {
                    if (cached) {
                        console.log('API request served from cache:', event.request.url);
                        return cached;
                    }
                    // Return error if no cache available
                    return new Response(JSON.stringify({ error: 'Network error' }), {
                        status: 503,
                        headers: { 'Content-Type': 'application/json' }
                    });
                });
            })
    );
}

// Handle static assets - Cache First with 30-day expiry
function handleStaticAsset(event) {
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            // Check if cached response is still valid
            if (cachedResponse) {
                const cachedDate = cachedResponse.headers.get('date');
                if (cachedDate) {
                    const age = Date.now() - new Date(cachedDate).getTime();
                    if (age < STATIC_CACHE_TTL) {
                        console.log('Static asset served from cache:', event.request.url);
                        return cachedResponse;
                    }
                }
            }
            
            // Fetch from network
            return fetch(event.request).then((response) => {
                if (response.ok) {
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            }).catch(() => {
                // Return cached response if available (even if expired)
                if (cachedResponse) {
                    console.log('Serving expired static asset from cache:', event.request.url);
                    return cachedResponse;
                }
                // Return offline page for navigation requests
                if (event.request.mode === 'navigate') {
                    return caches.match('/offline');
                }
                return new Response('Offline', { status: 503 });
            });
        })
    );
}

// Clean up old caches
async function cleanupOldCaches() {
    const cacheNames = await caches.keys();
    const dmsCaches = cacheNames.filter(name => name.startsWith('dms-') && name !== STATIC_CACHE_NAME && name !== API_CACHE_NAME);
    
    await Promise.all(
        dmsCaches.map(name => caches.delete(name))
    );
    
    console.log('Cleaned up', dmsCaches.length, 'old caches');
}

// Enforce cache size limit (max 50MB)
async function enforceCacheSizeLimit() {
    try {
        const cacheNames = await caches.keys();
        let totalSize = 0;
        const cacheEntries = [];
        
        for (const cacheName of cacheNames) {
            if (!cacheName.startsWith('dms-')) continue;
            
            const cache = await caches.open(cacheName);
            const keys = await cache.keys();
            
            for (const request of keys) {
                const response = await cache.match(request);
                if (response) {
                    const size = response.headers.get('content-length') ? 
                              parseInt(response.headers.get('content-length')) : 
                              response.blob().then(blob => blob.size);
                    totalSize += size;
                    cacheEntries.push({ cacheName, request, size });
                }
            }
        }
        
        // If over limit, remove oldest entries
        if (totalSize > MAX_CACHE_SIZE) {
            console.log(`Cache size (${(totalSize/1024/1024).toFixed(2)}MB) exceeds limit (${MAX_CACHE_SIZE/1024/1024}MB). Cleaning up...`);
            
            // Sort by cache name then remove oldest entries
            cacheEntries.sort((a, b) => b.size - a.size);
            
            for (const entry of cacheEntries) {
                if (totalSize <= MAX_CACHE_SIZE * 0.8) break; // Stop at 80% of limit
                
                const cache = await caches.open(entry.cacheName);
                await cache.delete(entry.request);
                totalSize -= entry.size;
                console.log('Removed cached entry:', entry.request.url);
            }
        }
    } catch (error) {
        console.error('Error enforcing cache size limit:', error);
    }
}

// Background sync for offline uploads
self.addEventListener('sync', (event) => {
    if (event.tag === 'document-upload') {
        event.waitUntil(syncDocumentUpload());
    }
});

// Push notifications
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : 'New notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-96x96.png',
        vibrate: [200, 100, 200],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View',
                icon: '/static/icons/icon-96x96.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/icons/icon-96x96.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Enterprise DMS', options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/dashboard')
        );
    }
});

// Sync offline uploads
async function syncDocumentUpload() {
    // Implement offline upload sync logic
    // This would queue uploads and retry when online
    console.log('Syncing offline document uploads...');
}

// Handle message from client
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});