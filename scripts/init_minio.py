"""
Office DMS - MinIO Initialization Script
Automatically creates buckets and sets policies for document storage.
"""
import os
import sys
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.storage import storage_manager


def init_minio():
    """Initialize MinIO buckets and policies."""
    logger.info("Starting MinIO initialization...")
    
    try:
        # Connect to MinIO
        logger.info(f"Connecting to MinIO at {settings.MINIO_ENDPOINT}")
        
        # Create main documents bucket
        bucket_name = settings.MINIO_BUCKET_NAME
        logger.info(f"Creating bucket: {bucket_name}")
        
        try:
            storage_manager.client.create_bucket(bucket_name)
            logger.info(f"✓ Bucket '{bucket_name}' created successfully")
        except Exception as e:
            if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                logger.info(f"✓ Bucket '{bucket_name}' already exists")
            else:
                logger.error(f"Failed to create bucket: {e}")
                raise
        
        # Set bucket policy for public read (optional, adjust as needed)
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            storage_manager.client.set_bucket_policy(bucket_name, policy)
            logger.info(f"✓ Bucket policy set for '{bucket_name}'")
        except Exception as e:
            logger.warning(f"Could not set bucket policy: {e}")
        
        # Create additional buckets if needed
        additional_buckets = [
            "dms-backups",
            "dms-temp",
            "dms-archived"
        ]
        
        for bucket in additional_buckets:
            try:
                storage_manager.client.create_bucket(bucket)
                logger.info(f"✓ Bucket '{bucket}' created successfully")
            except Exception as e:
                if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                    logger.info(f"✓ Bucket '{bucket}' already exists")
                else:
                    logger.warning(f"Failed to create bucket '{bucket}': {e}")
        
        logger.info("✓ MinIO initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ MinIO initialization failed: {e}")
        return False


def main():
    """Main entry point."""
    success = init_minio()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
