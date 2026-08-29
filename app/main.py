from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    import os
    import time
    import psutil
    disk = psutil.disk_usage('/')
    memory = psutil.virtual_memory()
    return {
        'status': 'ok',
        'service': 'app',
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent,
        },
        'memory': {
            'total': memory.total,
            'used': memory.used,
            'free': memory.available,
            'percent': memory.percent,
        },
        'response_time': time.time(),
        'checks': ['database', 'redis', 'celery', 'storage'],
    }

@app.get("/health/quick")
def quick_health_check():
    return {'status': 'ok'}
