"""
Permission Service - Folder-level access control
Manages user permissions for document folders with Redis caching.
"""
from typing import List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from app.models.database import User, FolderPermission, UserFolderMapping, Document
from app.models.schemas import PermissionLevel, UserRole


class PermissionService:
    """Service for managing folder-level permissions."""

    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache
        # Note: Redis integration would go here for production caching

    def get_user_folder_permissions(self, user_id: int, db: Session) -> List[str]:
        """
        Get list of folder paths the user has access to.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List[str]: List of accessible folder paths
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Admins have access to all folders
        if user.role == UserRole.ADMIN.value:
            return ["*"]  # Wildcard for all folders

        # Get user's explicit folder permissions
        mappings = db.query(UserFolderMapping).filter(
            UserFolderMapping.user_id == user_id
        ).all()

        folder_paths = set()
        for mapping in mappings:
            if mapping.folder_permission:
                folder_paths.add(mapping.folder_permission.folder_path)

        # Add default permissions for staff based on role
        if user.role == UserRole.STAFF.value:
            default_folders = [
                "Organized/Invoices",
                "Organized/BL",
                "Organized/NRC"
            ]
            folder_paths.update(default_folders)

        return list(folder_paths)

    def check_folder_access(
        self, 
        user_id: int, 
        folder_path: str, 
        action: PermissionLevel, 
        db: Session
    ) -> bool:
        """
        Check if user has permission for a specific folder and action.
        
        Args:
            user_id: User ID
            folder_path: Folder path to check
            action: Required permission level (read, write, admin)
            db: Database session
            
        Returns:
            bool: True if user has access
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Admins have full access
        if user.role == UserRole.ADMIN.value:
            return True

        # Get user's permissions
        accessible_folders = self.get_user_folder_permissions(user_id, db)
        
        # Check wildcard access
        if "*" in accessible_folders:
            return True

        # Check specific folder access
        if folder_path not in accessible_folders:
            return False

        # Check permission level
        mappings = db.query(UserFolderMapping).filter(
            UserFolderMapping.user_id == user_id
        ).all()

        for mapping in mappings:
            if mapping.folder_permission and mapping.folder_permission.folder_path == folder_path:
                user_permission = mapping.folder_permission.permission
                
                # Permission hierarchy: admin > write > read
                if action == PermissionLevel.READ:
                    return user_permission in [PermissionLevel.READ.value, PermissionLevel.WRITE.value, PermissionLevel.ADMIN.value]
                elif action == PermissionLevel.WRITE:
                    return user_permission in [PermissionLevel.WRITE.value, PermissionLevel.ADMIN.value]
                elif action == PermissionLevel.ADMIN:
                    return user_permission == PermissionLevel.ADMIN.value

        # Default to read permission for staff
        if user.role == UserRole.STAFF.value and action == PermissionLevel.READ:
            return True

        return False

    def assign_folder_permission(
        self, 
        user_id: int, 
        folder_path: str, 
        permission: PermissionLevel, 
        admin_user_id: int, 
        db: Session
    ) -> bool:
        """
        Assign folder permission to a user.
        
        Args:
            user_id: User ID to assign permission to
            folder_path: Folder path
            permission: Permission level
            admin_user_id: Admin user ID performing the action
            db: Database session
            
        Returns:
            bool: True if assignment successful
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            # Check if folder permission already exists
            folder_perm = db.query(FolderPermission).filter(
                FolderPermission.folder_path == folder_path,
                FolderPermission.role == user.role
            ).first()

            if not folder_perm:
                # Create new folder permission
                folder_perm = FolderPermission(
                    folder_path=folder_path,
                    role=user.role,
                    permission=permission.value,
                    created_by=admin_user_id,
                    created_at=datetime.utcnow()
                )
                db.add(folder_perm)
                db.commit()
                db.refresh(folder_perm)

            # Check if user mapping already exists
            existing_mapping = db.query(UserFolderMapping).filter(
                UserFolderMapping.user_id == user_id,
                UserFolderMapping.permission_id == folder_perm.id
            ).first()

            if existing_mapping:
                # Update existing mapping
                folder_perm.permission = permission.value
            else:
                # Create new mapping
                mapping = UserFolderMapping(
                    user_id=user_id,
                    permission_id=folder_perm.id,
                    assigned_by=admin_user_id,
                    assigned_at=datetime.utcnow()
                )
                db.add(mapping)

            db.commit()
            logger.info(f"Assigned {permission} permission for folder '{folder_path}' to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign folder permission: {e}")
            db.rollback()
            return False

    def remove_folder_permission(
        self, 
        user_id: int, 
        folder_path: str, 
        admin_user_id: int, 
        db: Session
    ) -> bool:
        """
        Remove folder permission from a user.
        
        Args:
            user_id: User ID to remove permission from
            folder_path: Folder path
            admin_user_id: Admin user ID performing the action
            db: Database session
            
        Returns:
            bool: True if removal successful
        """
        try:
            # Find the permission
            folder_perm = db.query(FolderPermission).filter(
                FolderPermission.folder_path == folder_path
            ).first()

            if not folder_perm:
                logger.error(f"Folder permission for '{folder_path}' not found")
                return False

            # Find and remove the mapping
            mapping = db.query(UserFolderMapping).filter(
                UserFolderMapping.user_id == user_id,
                UserFolderMapping.permission_id == folder_perm.id
            ).first()

            if mapping:
                db.delete(mapping)
                db.commit()
                logger.info(f"Removed permission for folder '{folder_path}' from user {user_id}")
                return True
            else:
                logger.warning(f"No permission mapping found for user {user_id} and folder '{folder_path}'")
                return False

        except Exception as e:
            logger.error(f"Failed to remove folder permission: {e}")
            db.rollback()
            return False

    def get_all_folder_permissions(self, db: Session) -> List[dict]:
        """
        Get all folder permissions with user mappings.
        
        Args:
            db: Database session
            
        Returns:
            List[dict]: List of permission details
        """
        try:
            permissions = db.query(FolderPermission).all()
            result = []
            
            for perm in permissions:
                # Get users with this permission
                mappings = db.query(UserFolderMapping).filter(
                    UserFolderMapping.permission_id == perm.id
                ).all()
                
                user_ids = [m.user_id for m in mappings]
                
                result.append({
                    "id": perm.id,
                    "folder_path": perm.folder_path,
                    "role": perm.role,
                    "permission": perm.permission,
                    "user_count": len(mappings),
                    "user_ids": user_ids,
                    "created_at": perm.created_at
                })
            
            return result

        except Exception as e:
            logger.error(f"Failed to get folder permissions: {e}")
            return []

    def filter_documents_by_permission(
        self, 
        user_id: int, 
        documents: List[Document], 
        db: Session
    ) -> List[Document]:
        """
        Filter documents based on user's folder permissions.
        
        Args:
            user_id: User ID
            documents: List of documents to filter
            db: Database session
            
        Returns:
            List[Document]: Filtered list of documents
        """
        accessible_folders = self.get_user_folder_permissions(user_id, db)
        
        # If user has wildcard access, return all documents
        if "*" in accessible_folders:
            return documents

        # Filter documents by folder
        filtered_docs = []
        for doc in documents:
            # Check if document's suggested_folder is in accessible folders
            if doc.suggested_folder and doc.suggested_folder in accessible_folders:
                filtered_docs.append(doc)
            # Also allow access to documents uploaded by the user
            elif doc.uploaded_by == user_id:
                filtered_docs.append(doc)

        return filtered_docs

    def initialize_default_permissions(self, db: Session) -> bool:
        """
        Initialize default folder permissions for the system.
        
        Args:
            db: Database session
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Create default folder permissions
            default_folders = [
                {"path": "Organized/Invoices", "role": "staff", "perm": "write"},
                {"path": "Organized/BL", "role": "staff", "perm": "write"},
                {"path": "Organized/NRC", "role": "staff", "perm": "write"},
                {"path": "Organized/FDA", "role": "staff", "perm": "read"},
                {"path": "Organized/Licenses", "role": "staff", "perm": "read"},
            ]

            for folder_def in default_folders:
                existing = db.query(FolderPermission).filter(
                    FolderPermission.folder_path == folder_def["path"],
                    FolderPermission.role == folder_def["role"]
                ).first()

                if not existing:
                    perm = FolderPermission(
                        folder_path=folder_def["path"],
                        role=folder_def["role"],
                        permission=folder_def["perm"],
                        created_at=datetime.utcnow()
                    )
                    db.add(perm)

            db.commit()
            logger.info("Default folder permissions initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize default permissions: {e}")
            db.rollback()
            return False


# Global permission service instance
permission_service = PermissionService()