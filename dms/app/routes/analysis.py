"""
API Routes for Function and Fracture Detection
Provides endpoints for document analysis and quality control
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from loguru import logger
import io

from app.core.database import get_db
from app.models.database import User, Document
from app.core.security import get_current_user
from app.services.function_detection import (
    FunctionDetectionService,
    FractureDetectionService,
    get_function_detection_service,
    get_fracture_detection_service,
    FunctionDetectionResult,
    FractureDetectionResult
)
from app.services.unified_ai_service import UnifiedAIService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/detect-function")
async def detect_document_function(
    text: str = Form(...),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Detect document function using AI and keyword analysis
    
    Analyzes document text to determine its function (invoice, bill of lading, etc.)
    """
    try:
        function_service = get_function_detection_service()
        
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            import json
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON: {metadata}")
        
        # Detect function
        result = function_service.detect_function(text, parsed_metadata)
        
        return {
            "success": True,
            "data": {
                "primary_function": result.primary_function.value,
                "confidence": result.confidence,
                "alternative_functions": [
                    {"function": func.value, "confidence": conf}
                    for func, conf in result.alternative_functions
                ],
                "detected_keywords": result.detected_keywords,
                "detected_patterns": result.detected_patterns,
                "analysis_metadata": result.analysis_metadata
            }
        }
    except Exception as e:
        logger.error(f"Function detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-fracture")
async def detect_document_fracture(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Detect document fractures, damage, and quality issues
    
    Analyzes document text and/or image to detect damage and quality issues
    """
    try:
        fracture_service = get_fracture_detection_service()
        
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            import json
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON: {metadata}")
        
        # Read image data if file provided
        image_data = None
        if file:
            image_data = await file.read()
        
        # Detect fracture
        result = fracture_service.detect_fracture(text, image_data, parsed_metadata)
        
        return {
            "success": True,
            "data": {
                "quality_level": result.quality_level.value,
                "damage_detected": result.damage_detected,
                "damage_type": result.damage_type,
                "damage_severity": result.damage_severity,
                "affected_areas": result.affected_areas,
                "confidence": result.confidence,
                "recommended_actions": result.recommended_actions,
                "analysis_metadata": result.analysis_metadata
            }
        }
    except Exception as e:
        logger.error(f"Fracture detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-document")
async def analyze_document_comprehensive(
    file: UploadFile = File(...),
    perform_ocr: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Comprehensive document analysis including function and fracture detection
    
    Performs full analysis: OCR, function detection, fracture detection, and quality assessment
    """
    try:
        # Read file
        file_content = await file.read()
        
        # Extract text (OCR if enabled)
        text = ""
        if perform_ocr:
            try:
                from app.services.ocr_service import OCRService
                ocr_service = OCRService()
                text = ocr_service.extract_text(file_content, file.filename)
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                text = str(file_content)
        else:
            text = str(file_content)
        
        # Perform function detection
        function_service = get_function_detection_service()
        function_result = function_service.detect_function(text)
        
        # Perform fracture detection
        fracture_service = get_fracture_detection_service()
        fracture_result = fracture_service.detect_fracture(text, file_content)
        
        # Return comprehensive results
        return {
            "success": True,
            "data": {
                "function_detection": {
                    "primary_function": function_result.primary_function.value,
                    "confidence": function_result.confidence,
                    "alternative_functions": [
                        {"function": func.value, "confidence": conf}
                        for func, conf in function_result.alternative_functions
                    ],
                    "detected_keywords": function_result.detected_keywords
                },
                "fracture_detection": {
                    "quality_level": fracture_result.quality_level.value,
                    "damage_detected": fracture_result.damage_detected,
                    "damage_type": fracture_result.damage_type,
                    "damage_severity": fracture_result.damage_severity,
                    "confidence": fracture_result.confidence,
                    "recommended_actions": fracture_result.recommended_actions
                },
                "text_extracted": len(text) > 0,
                "text_length": len(text)
            }
        }
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-document/{document_id}")
async def analyze_existing_document(
    document_id: int,
    perform_ocr: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze an existing document in the database
    
    Performs function and fracture detection on an already uploaded document
    """
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Extract text
        text = ""
        if perform_ocr:
            try:
                from app.services.ocr_service import OCRService
                ocr_service = OCRService()
                text = ocr_service.extract_text(document.file_path, document.filename)
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                text = ""
        
        # Perform function detection
        function_service = get_function_detection_service()
        function_result = function_service.detect_function(text)
        
        # Perform fracture detection
        fracture_service = get_fracture_detection_service()
        fracture_result = fracture_service.detect_fracture(text)
        
        # Update document with analysis results
        document.function_type = function_result.primary_function.value
        document.quality_level = fracture_result.quality_level.value
        document.has_damage = fracture_result.damage_detected
        document.damage_type = fracture_result.damage_type
        document.damage_severity = fracture_result.damage_severity
        db.commit()
        
        return {
            "success": True,
            "data": {
                "document_id": document.id,
                "function_detection": {
                    "primary_function": function_result.primary_function.value,
                    "confidence": function_result.confidence,
                    "alternative_functions": [
                        {"function": func.value, "confidence": conf}
                        for func, conf in function_result.alternative_functions
                    ]
                },
                "fracture_detection": {
                    "quality_level": fracture_result.quality_level.value,
                    "damage_detected": fracture_result.damage_detected,
                    "damage_type": fracture_result.damage_type,
                    "damage_severity": fracture_result.damage_severity,
                    "recommended_actions": fracture_result.recommended_actions
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/functions")
async def get_supported_functions(current_user: User = Depends(get_current_user)):
    """
    Get list of supported document functions
    """
    from app.services.function_detection import DocumentFunction
    
    return {
        "success": True,
        "data": {
            "functions": [
                {
                    "value": func.value,
                    "name": func.value.replace("_", " ").title()
                }
                for func in DocumentFunction
            ]
        }
    }


@router.get("/quality-levels")
async def get_quality_levels(current_user: User = Depends(get_current_user)):
    """
    Get list of quality levels
    """
    from app.services.function_detection import DocumentQuality
    
    return {
        "success": True,
        "data": {
            "quality_levels": [
                {
                    "value": quality.value,
                    "name": quality.value.replace("_", " ").title()
                }
                for quality in DocumentQuality
            ]
        }
    }


@router.post("/batch-analyze")
async def batch_analyze_documents(
    document_ids: list[int],
    perform_ocr: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch analyze multiple documents
    
    Performs function and fracture detection on multiple documents
    """
    try:
        results = []
        
        for document_id in document_ids:
            try:
                # Get document
                document = db.query(Document).filter(
                    Document.id == document_id,
                    Document.deleted == False
                ).first()
                
                if not document:
                    results.append({
                        "document_id": document_id,
                        "success": False,
                        "error": "Document not found"
                    })
                    continue
                
                # Check permission
                if document.user_id != current_user.id and not current_user.is_admin:
                    results.append({
                        "document_id": document_id,
                        "success": False,
                        "error": "No permission"
                    })
                    continue
                
                # Extract text
                text = ""
                if perform_ocr:
                    try:
                        from app.services.ocr_service import OCRService
                        ocr_service = OCRService()
                        text = ocr_service.extract_text(document.file_path, document.filename)
                    except Exception as e:
                        logger.warning(f"OCR failed for document {document_id}: {e}")
                
                # Perform analysis
                function_service = get_function_detection_service()
                function_result = function_service.detect_function(text)
                
                fracture_service = get_fracture_detection_service()
                fracture_result = fracture_service.detect_fracture(text)
                
                # Update document
                document.function_type = function_result.primary_function.value
                document.quality_level = fracture_result.quality_level.value
                document.has_damage = fracture_result.damage_detected
                document.damage_type = fracture_result.damage_type
                document.damage_severity = fracture_result.damage_severity
                
                results.append({
                    "document_id": document_id,
                    "success": True,
                    "function_type": function_result.primary_function.value,
                    "quality_level": fracture_result.quality_level.value,
                    "damage_detected": fracture_result.damage_detected
                })
                
            except Exception as e:
                logger.error(f"Analysis failed for document {document_id}: {e}")
                results.append({
                    "document_id": document_id,
                    "success": False,
                    "error": str(e)
                })
        
        db.commit()
        
        return {
            "success": True,
            "data": {
                "results": results,
                "total": len(document_ids),
                "successful": sum(1 for r in results if r["success"]),
                "failed": sum(1 for r in results if not r["success"])
            }
        }
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))