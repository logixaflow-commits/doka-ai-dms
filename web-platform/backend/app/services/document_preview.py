"""
Document Preview & Annotation Service
Provides document preview, annotation, and comparison features
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import json
from loguru import logger


class AnnotationType(Enum):
    """Types of document annotations"""
    HIGHLIGHT = "highlight"
    NOTE = "note"
    COMMENT = "comment"
    BOOKMARK = "bookmark"
    REDACTION = "redaction"
    SIGNATURE = "signature"
    STAMP = "stamp"


@dataclass
class Annotation:
    """Document annotation data"""
    id: str
    type: AnnotationType
    user_id: int
    document_id: int
    page_number: int
    position: Dict[str, Any]  # x, y, width, height
    content: str
    color: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentPreviewService:
    """Service for document preview and annotation"""
    
    def __init__(self):
        self.annotation_storage_path = Path("storage/annotations")
        self.annotation_storage_path.mkdir(parents=True, exist_ok=True)
        
    def _safe_document_dir(self, document_id: int) -> Path:
        """Resolve a document preview directory strictly beneath the preview root."""
        if not isinstance(document_id, int) or document_id < 1:
            raise ValueError("Invalid document id.")
        if self.annotation_storage_path.is_symlink():
            raise ValueError("Preview storage root cannot be a symlink.")
        root = self.annotation_storage_path.resolve()
        raw_candidate = root / str(document_id)
        if raw_candidate.is_symlink():
            raise ValueError("Document preview directory cannot be a symlink.")
        candidate = raw_candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("Document preview path escaped its safe root.") from exc
        return candidate

    def generate_preview(
        self, 
        document_path: str, 
        document_id: int,
        max_pages: int = 10,
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate document preview
        
        Args:
            document_path: Path to document file
            document_id: Document ID
            max_pages: Maximum number of pages to preview
            quality: Preview quality (low, medium, high)
            
        Returns:
            Dictionary with preview data
        """
        try:
            source_root = settings.PROCESSING_WORKSPACE.resolve()
            file_path = Path(document_path).resolve()
            try:
                file_path.relative_to(source_root)
            except ValueError as exc:
                raise ValueError("Preview source is outside the processing workspace.") from exc
            if file_path.is_symlink() or not file_path.is_file():
                raise ValueError("Preview source is not a regular file.")
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": "Document not found"
                }
            
            # Determine file type and generate appropriate preview
            if file_path.suffix.lower() == '.pdf':
                return self._generate_pdf_preview(file_path, document_id, max_pages, quality)
            elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return self._generate_image_preview(file_path, document_id, quality)
            else:
                return {
                    "success": False,
                    "error": "Unsupported file type for preview"
                }
                
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def _generate_pdf_preview(
        self, 
        pdf_path: Path, 
        document_id: int,
        max_pages: int,
        quality: str
    ) -> Dict[str, Any]:
        """Generate PDF preview"""
        try:
            from pdf2image import convert_from_path
            from PIL import Image
            import io
            
            # Determine DPI based on quality
            dpi_map = {
                "low": 100,
                "medium": 150,
                "high": 200
            }
            dpi = dpi_map.get(quality, 150)
            
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=dpi)
            
            # Limit number of pages
            images = images[:max_pages]
            
            # Generate preview data
            preview_data = {
                "success": True,
                "document_id": document_id,
                "type": "pdf",
                "total_pages": len(images),
                "quality": quality,
                "pages": []
            }
            
            # Create preview storage directory
            preview_dir = self._safe_document_dir(document_id) / "previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            for i, image in enumerate(images):
                # Resize image for preview
                max_width = 800
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Save preview image
                preview_path = preview_dir / f"page_{i+1}.jpg"
                image.save(preview_path, "JPEG", quality=85)
                
                # Add page data
                preview_data["pages"].append({
                    "page_number": i + 1,
                    "preview_url": f"/api/preview/{document_id}/page/{i+1}",
                    "width": image.width,
                    "height": image.height
                })
            
            return preview_data
            
        except ImportError:
            logger.warning("pdf2image not available")
            return {
                "success": False,
                "error": "PDF preview requires pdf2image library"
            }
        except Exception as e:
            logger.error(f"PDF preview generation failed: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def _generate_image_preview(
        self, 
        image_path: Path, 
        document_id: int,
        quality: str
    ) -> Dict[str, Any]:
        """Generate image preview"""
        try:
            from PIL import Image
            
            image = Image.open(image_path)
            
            # Resize for preview
            max_width = 800
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save preview
            preview_dir = self._safe_document_dir(document_id) / "previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            preview_path = preview_dir / "preview.jpg"
            image.save(preview_path, "JPEG", quality=85)
            
            return {
                "success": True,
                "document_id": document_id,
                "type": "image",
                "total_pages": 1,
                "quality": quality,
                "pages": [{
                    "page_number": 1,
                    "preview_url": f"/api/preview/{document_id}/page/1",
                    "width": image.width,
                    "height": image.height
                }]
            }
            
        except Exception as e:
            logger.error(f"Image preview generation failed: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def add_annotation(
        self,
        annotation: Annotation
    ) -> Dict[str, Any]:
        """Add annotation to document"""
        try:
            # Load existing annotations
            annotations_file = self.annotation_storage_path / f"{annotation.document_id}.json"
            
            if annotations_file.exists():
                with open(annotations_file, 'r') as f:
                    annotations_data = json.load(f)
            else:
                annotations_data = {"annotations": []}
            
            # Add new annotation
            annotation_data = {
                "id": annotation.id,
                "type": annotation.type.value,
                "user_id": annotation.user_id,
                "document_id": annotation.document_id,
                "page_number": annotation.page_number,
                "position": annotation.position,
                "content": annotation.content,
                "color": annotation.color,
                "created_at": annotation.created_at.isoformat(),
                "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None
            }
            
            annotations_data["annotations"].append(annotation_data)
            
            # Save annotations
            with open(annotations_file, 'w') as f:
                json.dump(annotations_data, f, indent=2)
            
            return {
                "success": True,
                "annotation": annotation_data
            }
            
        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def get_annotations(
        self,
        document_id: int,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get annotations for document"""
        try:
            annotations_file = self._safe_document_dir(document_id).with_suffix(".json")
            
            if not annotations_file.exists():
                return []
            
            with open(annotations_file, 'r') as f:
                annotations_data = json.load(f)
            
            annotations = annotations_data.get("annotations", [])
            
            # Filter by user if specified
            if user_id:
                annotations = [a for a in annotations if a["user_id"] == user_id]
            
            return annotations
            
        except Exception as e:
            logger.error(f"Failed to get annotations: {e}")
            return []
    
    def delete_annotation(
        self,
        document_id: int,
        annotation_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Delete annotation"""
        try:
            annotations_file = self.annotation_storage_path / f"{document_id}.json"
            
            if not annotations_file.exists():
                return {
                    "success": False,
                    "error": "Annotations file not found"
                }
            
            with open(annotations_file, 'r') as f:
                annotations_data = json.load(f)
            
            # Find and remove annotation
            annotations = annotations_data.get("annotations", [])
            annotation_found = False
            
            for i, annotation in enumerate(annotations):
                if annotation["id"] == annotation_id and annotation["user_id"] == user_id:
                    annotations.pop(i)
                    annotation_found = True
                    break
            
            if not annotation_found:
                return {
                    "success": False,
                    "error": "Annotation not found or access denied"
                }
            
            # Save updated annotations
            annotations_data["annotations"] = annotations
            with open(annotations_file, 'w') as f:
                json.dump(annotations_data, f, indent=2)
            
            return {
                "success": True,
                "message": "Annotation deleted"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete annotation: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def compare_documents(
        self,
        document_id_1: int,
        document_id_2: int
    ) -> Dict[str, Any]:
        """Compare two documents"""
        try:
            # This is a simplified comparison
            # Full implementation would use diff algorithms
            
            return {
                "success": True,
                "document_id_1": document_id_1,
                "document_id_2": document_id_2,
                "similar": False,
                "differences": [
                    "Document comparison feature requires additional implementation"
                ]
            }
            
        except Exception as e:
            logger.error(f"Document comparison failed: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }
    
    def get_print_view(
        self,
        document_id: int
    ) -> Dict[str, Any]:
        """Get print-friendly view of document"""
        try:
            preview_dir = self.annotation_storage_path / f"previews/{document_id}"
            
            if not preview_dir.exists():
                return {
                    "success": False,
                    "error": "Preview not available"
                }
            
            # Get all preview pages
            pages = sorted(preview_dir.glob("page_*.jpg"))
            
            return {
                "success": True,
                "document_id": document_id,
                "total_pages": len(pages),
                "pages": [
                    {
                        "page_number": i + 1,
                        "url": f"/api/preview/{document_id}/page/{i+1}/print"
                    }
                    for i in range(len(pages))
                ]
            }
            
        except Exception as e:
            logger.error(f"Print view generation failed: {e}")
            return {
                "success": False,
                "error": "Preview operation failed."
            }


# Singleton instance
_preview_service: Optional[DocumentPreviewService] = None


def get_preview_service() -> DocumentPreviewService:
    """Get singleton preview service"""
    global _preview_service
    if _preview_service is None:
        _preview_service = DocumentPreviewService()
    return _preview_service