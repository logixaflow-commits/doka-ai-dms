"""
Railway startup script - runs web server and Celery worker in same process
"""
import os
import subprocess
import threading
from app.core.config import settings

def start_web():
    """Start FastAPI web server"""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)

def start_worker():
    """Start Celery worker (if enabled)"""
    if os.getenv("RAILWAY_ENABLE_WORKER", "false") == "true":
        subprocess.run([
            "celery", "-A", "app.core.celery_app", 
            "worker", "--loglevel=info", "--concurrency=1"
        ])

if __name__ == "__main__":
    # Start worker in background thread if enabled
    if os.getenv("RAILWAY_ENABLE_WORKER", "false") == "true":
        worker_thread = threading.Thread(target=start_worker, daemon=True)
        worker_thread.start()
    
    # Start web server in main thread
    start_web()
