"""
Prometheus Metrics Integration for Enterprise AI DMS
Provides application metrics, performance monitoring, and business analytics
"""
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client.exposition import make_asgi_app
from loguru import logger


class PrometheusMetrics:
    """Prometheus metrics for the application"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Application info
        self.app_info = Info(
            'enterprise_ai_dms',
            'Enterprise AI Document Management System',
            registry=self.registry
        )
        self.app_info.info({
            'version': '1.0.0',
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'python_version': '3.14'
        })
        
        # HTTP metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'HTTP requests currently in progress',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Document metrics
        self.documents_total = Counter(
            'documents_total',
            'Total documents processed',
            ['status', 'category'],
            registry=self.registry
        )
        
        self.documents_processing_time = Histogram(
            'documents_processing_time_seconds',
            'Document processing time in seconds',
            ['document_type'],
            registry=self.registry
        )
        
        self.documents_upload_size = Histogram(
            'documents_upload_size_bytes',
            'Document upload size in bytes',
            registry=self.registry
        )
        
        # AI metrics
        self.ocr_operations_total = Counter(
            'ocr_operations_total',
            'Total OCR operations',
            ['language', 'status'],
            registry=self.registry
        )
        
        self.ocr_processing_time = Histogram(
            'ocr_processing_time_seconds',
            'OCR processing time in seconds',
            ['language'],
            registry=self.registry
        )
        
        self.function_detection_operations = Counter(
            'function_detection_operations_total',
            'Total function detection operations',
            ['function_type', 'status'],
            registry=self.registry
        )
        
        self.fracture_detection_operations = Counter(
            'fracture_detection_operations_total',
            'Total fracture detection operations',
            ['quality_level', 'status'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            'database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        # User metrics
        self.users_total = Gauge(
            'users_total',
            'Total users',
            ['role', 'status'],
            registry=self.registry
        )
        
        self.active_sessions = Gauge(
            'active_sessions',
            'Active user sessions',
            registry=self.registry
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.disk_usage = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['path'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['type', 'component'],
            registry=self.registry
        )
        
        # Business metrics
        self.documents_by_status = Gauge(
            'documents_by_status',
            'Documents by status',
            ['status'],
            registry=self.registry
        )
        
        self.documents_by_category = Gauge(
            'documents_by_category',
            'Documents by category',
            ['category'],
            registry=self.registry
        )
        
        self.documents_by_quality = Gauge(
            'documents_by_quality',
            'Documents by quality level',
            ['quality_level'],
            registry=self.registry
        )
        
        logger.info("Prometheus metrics initialized")


# Singleton instance
_prometheus_metrics: Optional[PrometheusMetrics] = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get singleton Prometheus metrics instance"""
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics


def track_http_request(method: str, endpoint: str):
    """Decorator to track HTTP requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_prometheus_metrics()
            
            # Increment in-progress gauge
            metrics.http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).inc()
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record duration
                duration = time.time() - start_time
                metrics.http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                
                # Record success
                metrics.http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                # Record error
                metrics.http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status='error'
                ).inc()
                
                metrics.errors_total.labels(
                    type='http',
                    component=endpoint
                ).inc()
                
                raise
                
            finally:
                # Decrement in-progress gauge
                metrics.http_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()
        
        return wrapper
    return decorator


def track_document_processing(document_type: str):
    """Decorator to track document processing"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_prometheus_metrics()
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record processing time
                duration = time.time() - start_time
                metrics.documents_processing_time.labels(
                    document_type=document_type
                ).observe(duration)
                
                return result
                
            except Exception as e:
                logger.error(f"Document processing error: {e}")
                metrics.errors_total.labels(
                    type='processing',
                    component='document'
                ).inc()
                raise
        
        return wrapper
    return decorator


def track_ocr_operation(language: str):
    """Decorator to track OCR operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_prometheus_metrics()
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Record processing time
                duration = time.time() - start_time
                metrics.ocr_processing_time.labels(
                    language=language
                ).observe(duration)
                
                # Record success
                metrics.ocr_operations_total.labels(
                    language=language,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                logger.error(f"OCR operation error: {e}")
                metrics.ocr_operations_total.labels(
                    language=language,
                    status='error'
                ).inc()
                raise
        
        return wrapper
    return decorator


def update_document_metrics(status: str, category: Optional[str] = None):
    """Update document metrics"""
    metrics = get_prometheus_metrics()
    
    metrics.documents_total.labels(
        status=status,
        category=category or 'unknown'
    ).inc()
    
    metrics.documents_by_status.labels(status=status).inc()
    
    if category:
        metrics.documents_by_category.labels(category=category).inc()


def update_user_metrics(role: str, is_active: bool):
    """Update user metrics"""
    metrics = get_prometheus_metrics()
    
    metrics.users_total.labels(
        role=role,
        status='active' if is_active else 'inactive'
    ).inc()


def update_system_metrics():
    """Update system metrics (CPU, memory, disk)"""
    metrics = get_prometheus_metrics()
    
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        metrics.cpu_usage.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        metrics.memory_usage.set(memory.used)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        metrics.disk_usage.labels(path='/').set(disk.used)
        
    except ImportError:
        logger.warning("psutil not available for system metrics")


def export_metrics():
    """Export all metrics in Prometheus format"""
    metrics = get_prometheus_metrics()
    return generate_latest(metrics.registry)


# ASGI app for metrics endpoint
metrics_app = make_asgi_app(get_prometheus_metrics().registry)