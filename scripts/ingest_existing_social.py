"""
Office DMS - Retroactive Social Media Ingestion Script
Processes existing social media files and organizes them by date.
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.database import SessionLocal, init_database
from app.core.logging import get_logger
from app.services.social_ingestor import social_ingestor
from app.models.database import User

logger = get_logger(__name__)


def get_existing_files(source_path: Path, extensions=None):
    """
    Get all existing files from a source directory.

    Args:
        source_path: Path to the source directory
        extensions: List of file extensions to include (None for all)

    Returns:
        List of Path objects
    """
    if not source_path.exists():
        logger.warning(f"Source path does not exist: {source_path}")
        return []

    if extensions is None:
        extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.xls', '.xlsx']

    files = []
    for ext in extensions:
        files.extend(source_path.glob(f"*{ext}"))
        files.extend(source_path.glob(f"*{ext.upper()}"))

    # Filter out directories
    files = [f for f in files if f.is_file()]

    logger.info(f"Found {len(files)} files in {source_path}")
    return files


async def process_existing_files(source_name: str, dry_run: bool = False):
    """
    Process existing files from a social media source.

    Args:
        source_name: Name of the source (Viber, WhatsApp, etc.)
        dry_run: If True, only simulate without making changes
    """
    source_config = social_ingestor.get_source_config(source_name)
    if not source_config:
        logger.error(f"Source configuration not found for: {source_name}")
        return

    source_path = Path(source_config.get('path', ''))
    if not source_path.exists():
        logger.error(f"Source path does not exist: {source_path}")
        return

    logger.info(f"Processing existing files from {source_name} at {source_path}")
    logger.info(f"Auto-rename: {source_config.get('auto_rename', True)}")
    logger.info(f"Preserve original: {source_config.get('preserve_original', True)}")
    logger.info(f"Dry run: {dry_run}")

    # Get existing files
    files = get_existing_files(source_path)
    if not files:
        logger.info("No files to process")
        return

    # Get default user
    db = SessionLocal()
    try:
        default_user = db.query(User).filter(User.username == "system").first()
        if not default_user:
            default_user = db.query(User).filter(User.role == "admin").first()
            if not default_user:
                logger.error("No admin user found. Cannot process files.")
                return

        # Process files
        processed = 0
        skipped = 0
        failed = 0

        for file_path in files:
            try:
                logger.info(f"Processing: {file_path.name}")

                if dry_run:
                    # Simulate processing
                    daily_folder = social_ingestor.get_daily_folder()
                    new_filename = social_ingestor.generate_filename(
                        source=source_name,
                        category="Unknown",  # We don't know without OCR
                        original_filename=file_path.name
                    )
                    target_path = daily_folder / new_filename

                    logger.info(f"  [DRY RUN] Would move to: {target_path}")
                    processed += 1
                else:
                    # Actual processing
                    document = await social_ingestor.process_social_file(
                        source_path=file_path,
                        source_name=source_name,
                        uploaded_by=default_user.id,
                        db=db
                    )

                    if document:
                        logger.info(f"  ✓ Processed successfully: {file_path.name}")
                        processed += 1
                    else:
                        logger.warning(f"  ✗ Skipped: {file_path.name}")
                        skipped += 1

            except Exception as e:
                logger.error(f"  ✗ Failed to process {file_path.name}: {e}")
                failed += 1

        logger.info(f"\nSummary for {source_name}:")
        logger.info(f"  Processed: {processed}")
        logger.info(f"  Skipped: {skipped}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total: {len(files)}")

    finally:
        db.close()


def main():
    """Main entry point for retroactive ingestion."""
    import argparse

    parser = argparse.ArgumentParser(description='Retroactively process existing social media files')
    parser.add_argument('--source', type=str, help='Source name (Viber, WhatsApp, Facebook, Telegram)')
    parser.add_argument('--all', action='store_true', help='Process all enabled sources')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')

    args = parser.parse_args()

    # Initialize database
    init_database()

    # Process sources
    sources_to_process = []

    if args.source:
        sources_to_process = [args.source]
    elif args.all:
        watch_sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        sources_to_process = [s.get('name') for s in watch_sources if s.get('enabled', False)]
    else:
        # If no source specified, ask user
        watch_sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        enabled_sources = [s.get('name') for s in watch_sources if s.get('enabled', False)]

        if not enabled_sources:
            logger.error("No enabled watch sources found in config.yaml")
            return

        print("Available sources:")
        for i, source in enumerate(enabled_sources, 1):
            print(f"  {i}. {source}")

        choice = input("\nSelect source (number or name, or 'all'): ").strip()

        if choice.lower() == 'all':
            sources_to_process = enabled_sources
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(enabled_sources):
                sources_to_process = [enabled_sources[idx]]
            else:
                logger.error("Invalid selection")
                return
        else:
            if choice in enabled_sources:
                sources_to_process = [choice]
            else:
                logger.error(f"Invalid source: {choice}")
                return

    # Process each source
    for source_name in sources_to_process:
        print(f"\n{'='*60}")
        print(f"Processing source: {source_name}")
        print(f"{'='*60}\n")

        asyncio.run(process_existing_files(source_name, dry_run=args.dry_run))

    print(f"\n{'='*60}")
    print("Retroactive ingestion completed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()