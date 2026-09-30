#!/usr/bin/env python3
"""
Office DMS - MinIO Initialization Script
Auto-creates buckets and sets policies on first run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_minio():
    """Initialize MinIO buckets and policies."""
    try:
        from minio import Minio
        from minio.error import S3Error

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # Check connectivity
        client.list_buckets()
        logger.info(f"Connected to MinIO at {settings.MINIO_ENDPOINT}")

        # Create main bucket
        bucket = settings.MINIO_BUCKET_NAME
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created MinIO bucket: {bucket}")
        else:
            logger.info(f"Bucket already exists: {bucket}")

        # Create sub-prefixes (MinIO doesn't have real folders, but we can verify access)
        logger.info("MinIO initialization complete.")
        return True

    except ImportError:
        logger.error("minio package not installed. Run: pip install minio")
        return False
    except Exception as e:
        logger.error(f"MinIO initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = init_minio()
    sys.exit(0 if success else 1)
