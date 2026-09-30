"""
Webhook Receiver
Handles incoming webhooks from external API providers.
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from sqlalchemy.orm import Session
from loguru import logger
import json

from app.core.database import get_db
from app.services.external_api_service import get_external_api_service

router = APIRouter()


@router.post("/webhooks/{provider_name}")
async def receive_webhook(
    provider_name: str,
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature"),
    db: Session = Depends(get_db)
):
    """
    Receive webhook from an external API provider.
    Verifies signature and updates document metadata accordingly.
    """
    try:
        # Get raw request body
        body = await request.body()
        payload = body.decode('utf-8')
        
        # Verify webhook signature if signature header provided
        if x_webhook_signature:
            api_service = get_external_api_service(db)
            if not api_service.verify_webhook(provider_name, payload, x_webhook_signature):
                logger.warning(f"Invalid webhook signature for provider: {provider_name}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature"
                )
        
        # Parse webhook payload
        webhook_data = json.loads(payload)
        
        logger.info(f"Received webhook from {provider_name}: {webhook_data}")
        
        # Process webhook based on provider type
        result = await _process_webhook(provider_name, webhook_data, db)
        
        return {
            "message": "Webhook processed successfully",
            "processed": result
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


async def _process_webhook(provider_name: str, webhook_data: dict, db: Session) -> bool:
    """
    Process webhook data and update documents accordingly.
    
    Args:
        provider_name: Provider name (e.g., "DHL", "Myanmar Customs")
        webhook_data: Webhook payload
        db: Database session
        
    Returns:
        True if processed successfully
    """
    try:
        from app.models.database import Document
        from app.services.shipping_integration import get_shipping_integration_service
        
        # Handle different provider types
        if "customs" in provider_name.lower():
            # Customs status update webhook
            declaration_id = webhook_data.get("declaration_id")
            status = webhook_data.get("status")
            
            if declaration_id and status:
                # Find document with this declaration ID
                doc = db.query(Document).filter(
                    Document.extracted_metadata['customs_declaration_id'].astext == str(declaration_id)
                ).first()
                
                if doc:
                    # Update document metadata
                    metadata = doc.extracted_metadata or {}
                    metadata["customs_status"] = status
                    metadata["customs_updated_at"] = webhook_data.get("updated_at")
                    doc.extracted_metadata = metadata
                    db.commit()
                    
                    logger.info(f"Updated document {doc.id} with customs status: {status}")
                    return True
        
        elif "shipping" in provider_name.lower() or "dhl" in provider_name.lower():
            # Shipping status update webhook
            tracking_number = webhook_data.get("tracking_number")
            status = webhook_data.get("status")
            
            if tracking_number and status:
                # Find document with this BL number
                doc = db.query(Document).filter(
                    Document.extracted_metadata['bl_number'].astext == tracking_number
                ).first()
                
                if doc:
                    # Update document metadata
                    metadata = doc.extracted_metadata or {}
                    shipping_tracking = metadata.get("shipping_tracking", {})
                    shipping_tracking["status"] = status
                    shipping_tracking["updated_at"] = webhook_data.get("updated_at")
                    shipping_tracking["current_location"] = webhook_data.get("location")
                    metadata["shipping_tracking"] = shipping_tracking
                    doc.extracted_metadata = metadata
                    db.commit()
                    
                    logger.info(f"Updated document {doc.id} with shipping status: {status}")
                    return True
        
        # Generic webhook handling
        document_id = webhook_data.get("document_id")
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                # Store webhook data in metadata
                metadata = doc.extracted_metadata or {}
                metadata["webhooks"] = metadata.get("webhooks", [])
                metadata["webhooks"].append({
                    "provider": provider_name,
                    "data": webhook_data,
                    "received_at": webhook_data.get("timestamp") or webhook_data.get("received_at")
                })
                doc.extracted_metadata = metadata
                db.commit()
                
                logger.info(f"Updated document {doc.id} with webhook data from {provider_name}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to process webhook data: {e}")
        return False