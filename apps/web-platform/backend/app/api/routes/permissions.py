"""
Permission Management Routes
Handles folder-level access control and user permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.core.logging import log_audit, get_client_info
from app.models.database import User
from app.models.schemas import (
    FolderPermissionCreate, FolderPermissionResponse, UserFolderPermissionAssign,
    UserFolderPermissionRemove, UserFolderPermissionsResponse, FolderAccessCheck,
    FolderAccessResponse, PermissionLevel
)
from app.services.permission_service import permission_service

router = APIRouter()


@router.get("/my-permissions", response_model=UserFolderPermissionsResponse)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's folder permissions.
    
    Returns all folders the current user has access to along with
    their permission levels.
    """
    try:
        accessible_folders = permission_service.get_user_folder_permissions(current_user.id, db)
        
        # Convert to permission response format
        permissions = []
        for folder_path in accessible_folders:
            # Determine permission level based on user role
            if folder_path == "*":
                perm_level = PermissionLevel.ADMIN
            elif current_user.role == "admin":
                perm_level = PermissionLevel.ADMIN
            elif current_user.role == "staff":
                perm_level = PermissionLevel.WRITE
            else:
                perm_level = PermissionLevel.READ
            
            permissions.append(FolderPermissionResponse(
                id=0,  # Placeholder for ID
                folder_path=folder_path,
                role=current_user.role,
                permission=perm_level.value,
                created_at=current_user.created_at
            ))
        
        return UserFolderPermissionsResponse(
            user_id=current_user.id,
            username=current_user.username,
            permissions=permissions
        )
        
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions"
        )


@router.get("/user/{user_id}", response_model=UserFolderPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific user's folder permissions (admin only).
    
    Admins can view any user's folder permissions.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        accessible_folders = permission_service.get_user_folder_permissions(user_id, db)
        
        # Convert to permission response format
        permissions = []
        for folder_path in accessible_folders:
            if folder_path == "*":
                perm_level = PermissionLevel.ADMIN
            elif user.role == "admin":
                perm_level = PermissionLevel.ADMIN
            elif user.role == "staff":
                perm_level = PermissionLevel.WRITE
            else:
                perm_level = PermissionLevel.READ
            
            permissions.append(FolderPermissionResponse(
                id=0,
                folder_path=folder_path,
                role=user.role,
                permission=perm_level.value,
                created_at=user.created_at
            ))
        
        return UserFolderPermissionsResponse(
            user_id=user.id,
            username=user.username,
            permissions=permissions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user permissions"
        )


@router.post("/check-access", response_model=FolderAccessResponse)
async def check_folder_access(
    access_check: FolderAccessCheck,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has access to a specific folder and action.
    
    This endpoint can be used to validate access before performing
    document operations.
    """
    try:
        has_access = permission_service.check_folder_access(
            current_user.id,
            access_check.folder_path,
            access_check.action,
            db
        )
        
        # Determine the actual permission level
        permission_level = None
        if has_access:
            if current_user.role == "admin" or access_check.folder_path == "*":
                permission_level = PermissionLevel.ADMIN
            elif current_user.role == "staff":
                permission_level = PermissionLevel.WRITE
            else:
                permission_level = PermissionLevel.READ
        
        return FolderAccessResponse(
            has_access=has_access,
            permission_level=permission_level
        )
        
    except Exception as e:
        logger.error(f"Failed to check folder access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check folder access"
        )


@router.post("/assign", response_model=FolderPermissionResponse)
async def assign_permission(
    request: Request,
    assignment: UserFolderPermissionAssign,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Assign folder permission to a user (admin only).
    
    Admins can grant folder access to users with specific permission levels.
    """
    try:
        target_user = db.query(User).filter(User.id == assignment.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get folder permission details
        from app.models.database import FolderPermission
        folder_perm = db.query(FolderPermission).filter(
            FolderPermission.id == assignment.permission_id
        ).first()
        
        if not folder_perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder permission not found"
            )

        # Assign permission
        success = permission_service.assign_folder_permission(
            assignment.user_id,
            folder_perm.folder_path,
            PermissionLevel(folder_perm.permission),
            current_user.id,
            db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign permission"
            )
        
        client = get_client_info(request)
        log_audit(
            "PERMISSION_ASSIGNED",
            current_user.id,
            {
                "target_user": assignment.user_id,
                "folder_path": folder_perm.folder_path,
                "permission": folder_perm.permission,
                "ip": client["ip_address"]
            }
        )
        
        return FolderPermissionResponse(
            id=folder_perm.id,
            folder_path=folder_perm.folder_path,
            role=folder_perm.role,
            permission=folder_perm.permission,
            created_at=folder_perm.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permission"
        )


@router.post("/remove")
async def remove_permission(
    request: Request,
    removal: UserFolderPermissionRemove,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Remove folder permission from a user (admin only).
    
    Admins can revoke folder access from users.
    """
    try:
        target_user = db.query(User).filter(User.id == removal.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get folder permission details
        from app.models.database import FolderPermission
        folder_perm = db.query(FolderPermission).filter(
            FolderPermission.id == removal.permission_id
        ).first()
        
        if not folder_perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder permission not found"
            )

        # Remove permission
        success = permission_service.remove_folder_permission(
            removal.user_id,
            folder_perm.folder_path,
            current_user.id,
            db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove permission"
            )
        
        client = get_client_info(request)
        log_audit(
            "PERMISSION_REMOVED",
            current_user.id,
            {
                "target_user": removal.user_id,
                "folder_path": folder_perm.folder_path,
                "ip": client["ip_address"]
            }
        )
        
        return {"message": "Permission removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove permission"
        )


@router.post("/folders")
async def create_folder_permission(
    request: Request,
    folder_perm: FolderPermissionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new folder permission definition (admin only).
    
    This creates the base permission definition that can then be assigned to users.
    """
    try:
        from app.models.database import FolderPermission
        
        # Check if permission already exists
        existing = db.query(FolderPermission).filter(
            FolderPermission.folder_path == folder_perm.folder_path,
            FolderPermission.role == folder_perm.role.value
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder permission already exists for this role"
            )
        
        # Create new permission
        new_perm = FolderPermission(
            folder_path=folder_perm.folder_path,
            role=folder_perm.role.value,
            permission=folder_perm.permission.value,
            created_by=current_user.id,
            created_at=current_user.created_at
        )
        
        db.add(new_perm)
        db.commit()
        db.refresh(new_perm)
        
        client = get_client_info(request)
        log_audit(
            "FOLDER_PERMISSION_CREATED",
            current_user.id,
            {
                "folder_path": folder_perm.folder_path,
                "role": folder_perm.role.value,
                "permission": folder_perm.permission.value,
                "ip": client["ip_address"]
            }
        )
        
        return FolderPermissionResponse(
            id=new_perm.id,
            folder_path=new_perm.folder_path,
            role=new_perm.role,
            permission=new_perm.permission,
            created_at=new_perm.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create folder permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create folder permission"
        )


@router.get("/folders")
async def get_all_folder_permissions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all folder permissions (admin only).
    
    Returns all folder permission definitions with user mapping counts.
    """
    try:
        permissions = permission_service.get_all_folder_permissions(db)
        return {"permissions": permissions}
        
    except Exception as e:
        logger.error(f"Failed to get folder permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve folder permissions"
        )


@router.post("/initialize-defaults")
async def initialize_default_permissions(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Initialize default folder permissions for the system (admin only).
    
    This creates the standard folder permissions for staff roles.
    """
    try:
        success = permission_service.initialize_default_permissions(db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize default permissions"
            )
        
        client = get_client_info(request)
        log_audit(
            "DEFAULT_PERMISSIONS_INITIALIZED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return {"message": "Default permissions initialized successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize default permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default permissions"
        )