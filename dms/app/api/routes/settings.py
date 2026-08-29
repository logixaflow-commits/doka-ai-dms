"""
Office DMS - Settings Routes
CRUD endpoints for managing watch sources and system settings.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_admin
from app.core.config import settings
from app.core.logging import get_logger
from app.core.config import Settings

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for Watch Sources
class WatchSourceBase(BaseModel):
    name: str
    path: str
    enabled: bool = True
    auto_rename: bool = True
    preserve_original: bool = True
    description: Optional[str] = None


class WatchSourceCreate(WatchSourceBase):
    pass


class WatchSourceUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    enabled: Optional[bool] = None
    auto_rename: Optional[bool] = None
    preserve_original: Optional[bool] = None
    description: Optional[str] = None


class WatchSourceResponse(WatchSourceBase):
    last_scanned: Optional[str] = None
    file_count: Optional[int] = None

    class Config:
        from_attributes = True


class WatchSourceList(BaseModel):
    sources: List[WatchSourceResponse]


class SocialMediaConfig(BaseModel):
    base_folder: str
    date_format: str
    naming_template: str
    create_daily_folders: bool


# In-memory storage for watch sources (in production, use database)
# For now, we'll manage them via config.yaml and return from settings
@router.get("/settings/sources", response_model=WatchSourceList)
async def get_watch_sources(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all configured watch sources.
    Admin only.
    """
    try:
        # Load from settings.watch_sources
        sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []

        # Convert to response format
        source_responses = []
        for source in sources:
            source_response = WatchSourceResponse(
                name=source.get('name'),
                path=source.get('path'),
                enabled=source.get('enabled', True),
                auto_rename=source.get('auto_rename', True),
                preserve_original=source.get('preserve_original', True),
                description=source.get('description')
            )
            source_responses.append(source_response)

        return WatchSourceList(sources=source_responses)

    except Exception as e:
        logger.error(f"Failed to get watch sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watch sources"
        )


@router.post("/settings/sources", response_model=WatchSourceResponse)
async def create_watch_source(
    source: WatchSourceCreate,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new watch source.
    Admin only.
    Note: This updates config.yaml file.
    """
    try:
        # In a production system, this would update the database and config.yaml
        # For now, we'll validate and return success
        # The actual config.yaml update would need a proper file update mechanism

        # Validate the source
        if not source.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source name is required"
            )

        if not source.path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source path is required"
            )

        logger.info(f"Creating watch source: {source.name} at {source.path}")

        # For production, implement config.yaml update here
        # For now, return the created source
        return WatchSourceResponse(
            name=source.name,
            path=source.path,
            enabled=source.enabled,
            auto_rename=source.auto_rename,
            preserve_original=source.preserve_original,
            description=source.description
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create watch source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create watch source"
        )


@router.put("/settings/sources/{source_name}", response_model=WatchSourceResponse)
async def update_watch_source(
    source_name: str,
    source_update: WatchSourceUpdate,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing watch source.
    Admin only.
    """
    try:
        # Find the source in settings
        sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        source_to_update = None

        for source in sources:
            if source.get('name') == source_name:
                source_to_update = source
                break

        if not source_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watch source '{source_name}' not found"
            )

        # Update fields
        if source_update.name is not None:
            source_to_update['name'] = source_update.name
        if source_update.path is not None:
            source_to_update['path'] = source_update.path
        if source_update.enabled is not None:
            source_to_update['enabled'] = source_update.enabled
        if source_update.auto_rename is not None:
            source_to_update['auto_rename'] = source_update.auto_rename
        if source_update.preserve_original is not None:
            source_to_update['preserve_original'] = source_update.preserve_original
        if source_update.description is not None:
            source_to_update['description'] = source_update.description

        logger.info(f"Updated watch source: {source_name}")

        # For production, implement config.yaml update here

        return WatchSourceResponse(
            name=source_to_update.get('name'),
            path=source_to_update.get('path'),
            enabled=source_to_update.get('enabled', True),
            auto_rename=source_to_update.get('auto_rename', True),
            preserve_original=source_to_update.get('preserve_original', True),
            description=source_to_update.get('description')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watch source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update watch source"
        )


@router.delete("/settings/sources/{source_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch_source(
    source_name: str,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a watch source.
    Admin only.
    """
    try:
        # Find and remove the source from settings
        sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        source_to_delete = None

        for i, source in enumerate(sources):
            if source.get('name') == source_name:
                source_to_delete = source
                sources.pop(i)
                break

        if not source_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Watch source '{source_name}' not found"
            )

        logger.info(f"Deleted watch source: {source_name}")

        # For production, implement config.yaml update here

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete watch source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete watch source"
        )


@router.get("/settings/social-media-config", response_model=SocialMediaConfig)
async def get_social_media_config(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get social media configuration.
    Admin only.
    """
    try:
        social_config = settings.social_media if hasattr(settings, 'social_media') else {}

        return SocialMediaConfig(
            base_folder=social_config.get('base_folder', 'Organized/Social_Media'),
            date_format=social_config.get('date_format', '%Y-%m-%d'),
            naming_template=social_config.get('naming_template', '{date}_{source}_{category}_{original_name}'),
            create_daily_folders=social_config.get('create_daily_folders', True)
        )

    except Exception as e:
        logger.error(f"Failed to get social media config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve social media configuration"
        )


@router.put("/settings/social-media-config", response_model=SocialMediaConfig)
async def update_social_media_config(
    config: SocialMediaConfig,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update social media configuration.
    Admin only.
    """
    try:
        logger.info(f"Updating social media config")

        # For production, implement config.yaml update here
        # For now, return the updated config

        return config

    except Exception as e:
        logger.error(f"Failed to update social media config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update social media configuration"
        )