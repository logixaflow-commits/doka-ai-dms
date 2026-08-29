"""
PWA Service - Progressive Web App generation and configuration
"""
from typing import Dict, Any
import json
from loguru import logger


class PWAService:
    """Service for generating PWA manifest and service worker configuration."""

    def __init__(self):
        self.app_name = "Enterprise DMS"
        self.short_name = "DMS"
        self.theme_color = "#2563eb"
        self.background_color = "#ffffff"
        self.display = "standalone"

    def generate_manifest(self) -> Dict[str, Any]:
        """
        Generate PWA manifest.json content.
        
        Returns:
            Manifest dictionary
        """
        manifest = {
            "name": self.app_name,
            "short_name": self.short_name,
            "description": "Enterprise Document Management System",
            "start_url": "/dashboard",
            "display": self.display,
            "background_color": self.background_color,
            "theme_color": self.theme_color,
            "orientation": "portrait-primary",
            "icons": [
                {
                    "src": "/static/icons/icon-72x72.png",
                    "sizes": "72x72",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-96x96.png",
                    "sizes": "96x96",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-128x128.png",
                    "sizes": "128x128",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-144x144.png",
                    "sizes": "144x144",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-152x152.png",
                    "sizes": "152x152",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-384x384.png",
                    "sizes": "384x384",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ],
            "categories": ["business", "productivity"],
            "screenshots": [],
            "related_applications": []
        }

        return manifest

    def generate_service_worker(self) -> str:
        """
        Generate service worker JavaScript code.
        
        Returns:
            Service worker code string
        """
        sw_code = f'''
// Enterprise DMS Service Worker
const CACHE_NAME = 'dms-v1';
const STATIC_CACHE = 'dms-static-v1';
const API_CACHE = 'dms-api-v1';

// Files to cache on install
const STATIC_ASSETS = [
    '/',
    '/dashboard',
    '/offline',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {{
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {{
            return cache.addAll(STATIC_ASSETS);
        }})
    );
    self.skipWaiting();
}});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {{
    event.waitUntil(
        caches.keys().then((cacheNames) => {{
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName.startsWith('dms-'))
                    .filter((cacheName) => cacheName !== STATIC_CACHE && cacheName !== API_CACHE)
                    .map((cacheName) => caches.delete(cacheName))
            );
        }})
    );
    self.clients.claim();
}});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {{
    const url = new URL(event.request.url);
    
    // Handle API requests - network first, then cache
    if (url.pathname.startsWith('/api/')) {{
        event.respondWith(
            fetch(event.request)
                .then((response) => {{
                    // Cache successful API responses
                    if (response.ok) {{
                        const responseClone = response.clone();
                        caches.open(API_CACHE).then((cache) => {{
                            cache.put(event.request, responseClone);
                        }});
                    }}
                    return response;
                }})
                .catch(() => {{
                    // Fall back to cache if network fails
                    return caches.match(event.request);
                }})
        );
        return;
    }}
    
    // Handle static assets - cache first, then network
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {{
            if (cachedResponse) {{
                return cachedResponse;
            }}
            return fetch(event.request).then((response) => {{
                if (response.ok) {{
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE).then((cache) => {{
                        cache.put(event.request, responseClone);
                    }});
                }}
                return response;
            }});
        }}).catch(() => {{
            // Return offline page for navigation requests
            if (event.request.mode === 'navigate') {{
                return caches.match('/offline');
            }}
        }})
    );
}});

// Background sync for offline uploads
self.addEventListener('sync', (event) => {{
    if (event.tag === 'document-upload') {{
        event.waitUntil(syncDocumentUpload());
    }}
}});

// Push notifications
self.addEventListener('push', (event) => {{
    const options = {{
        body: event.data ? event.data.text() : 'New notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-96x96.png',
        vibrate: [200, 100, 200],
        data: {{
            dateOfArrival: Date.now(),
            primaryKey: 1
        }},
        actions: [
            {{
                action: 'explore',
                title: 'View',
                icon: '/static/icons/icon-96x96.png'
            }},
            {{
                action: 'close',
                title: 'Close',
                icon: '/static/icons/icon-96x96.png'
            }}
        ]
    }};
    
    event.waitUntil(
        self.registration.showNotification('Enterprise DMS', options)
    );
}});

// Sync offline uploads
async function syncDocumentUpload() {{
    // Implement offline upload sync logic
    // This would queue uploads and retry when online
}}
'''
        return sw_code.strip()

    def cache_strategy(self) -> str:
        """
        Define caching strategy.
        
        Returns:
            Cache strategy description
        """
        return """
        Cache Strategy:
        - Static Assets (CSS, JS, Icons): Cache First
        - API Requests: Network First, then Cache
        - Navigation: Cache First, with Offline Fallback
        - Document Downloads: No Caching (streamed)
        """

    def get_offline_fallback(self) -> str:
        """
        Get offline fallback HTML.
        
        Returns:
            Offline page HTML
        """
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - Enterprise DMS</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f3f4f6;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 400px;
        }
        .icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        h1 {
            color: #1f2937;
            margin: 0 0 1rem 0;
        }
        p {
            color: #6b7280;
            margin: 0 0 1.5rem 0;
        }
        button {
            background: #2563eb;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
        }
        button:hover {
            background: #1d4ed8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📴</div>
        <h1>You're Offline</h1>
        <p>Check your internet connection and try again.</p>
        <button onclick="location.reload()">Retry</button>
    </div>
</body>
</html>
        '''


# Global PWA service instance
pwa_service = PWAService()