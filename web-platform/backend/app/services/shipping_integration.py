"""
Shipping Integration Service - Specific integrations for shipping, customs, and freight APIs
"""
from typing import Dict, Any, Optional
from loguru import logger

from sqlalchemy.orm import Session
from app.services.external_api_service import ExternalAPIService


class ShippingIntegrationService:
    """Service for shipping and customs API integrations."""

    def __init__(self, db: Session):
        self.db = db
        self.api_service = ExternalAPIService(db)

    def track_shipment(self, provider_id: int, bl_number: str) -> Dict[str, Any]:
        """
        Track shipment using Bill of Lading number.
        
        Args:
            provider_id: External API provider ID
            bl_number: Bill of Lading number
            
        Returns:
            Shipment tracking information
        """
        try:
            # Call the provider's tracking endpoint
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="track",
                method="GET",
                params={"tracking_number": bl_number}
            )
            
            if response.get("success"):
                # Parse response and return formatted data
                data = response.get("data", {})
                return {
                    "bl_number": bl_number,
                    "status": data.get("status", "unknown"),
                    "origin": data.get("origin"),
                    "destination": data.get("destination"),
                    "eta": data.get("eta"),
                    "current_location": data.get("current_location"),
                    "tracking_events": data.get("events", [])
                }
            else:
                logger.error(f"Failed to track shipment {bl_number}: {response.get('error')}")
                return {"error": response.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to track shipment: {e}")
            return {"error": str(e)}

    def get_customs_status(self, provider_id: int, declaration_id: str) -> Dict[str, Any]:
        """
        Get customs declaration status.
        
        Args:
            provider_id: External API provider ID
            declaration_id: Customs declaration ID
            
        Returns:
            Customs status information
        """
        try:
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="status",
                method="GET",
                params={"declaration_id": declaration_id}
            )
            
            if response.get("success"):
                data = response.get("data", {})
                return {
                    "declaration_id": declaration_id,
                    "status": data.get("status", "unknown"),
                    "clearance_date": data.get("clearance_date"),
                    "duty_amount": data.get("duty_amount"),
                    "tax_amount": data.get("tax_amount"),
                    "pending_documents": data.get("pending_documents", [])
                }
            else:
                logger.error(f"Failed to get customs status for {declaration_id}: {response.get('error')}")
                return {"error": response.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to get customs status: {e}")
            return {"error": str(e)}

    def submit_customs_declaration(
        self,
        provider_id: int,
        declaration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit customs declaration.
        
        Args:
            provider_id: External API provider ID
            declaration_data: Declaration data
            
        Returns:
            Submission result
        """
        try:
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="submit",
                method="POST",
                data=declaration_data
            )
            
            if response.get("success"):
                data = response.get("data", {})
                return {
                    "success": True,
                    "declaration_id": data.get("declaration_id"),
                    "status": data.get("status", "submitted"),
                    "submitted_at": data.get("submitted_at")
                }
            else:
                logger.error(f"Failed to submit customs declaration: {response.get('error')}")
                return {"success": False, "error": response.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to submit customs declaration: {e}")
            return {"success": False, "error": str(e)}

    def get_eta(self, provider_id: int, bl_number: str) -> Optional[str]:
        """
        Get Estimated Time of Arrival for a shipment.
        
        Args:
            provider_id: External API provider ID
            bl_number: Bill of Lading number
            
        Returns:
            ETA date string or None
        """
        try:
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="track",
                method="GET",
                params={"tracking_number": bl_number}
            )
            
            if response.get("success"):
                data = response.get("data", {})
                return data.get("eta")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ETA: {e}")
            return None

    def get_freight_rates(
        self,
        provider_id: int,
        origin: str,
        destination: str,
        weight: float,
        dimensions: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Get freight rates from provider.
        
        Args:
            provider_id: External API provider ID
            origin: Origin port/code
            destination: Destination port/code
            weight: Weight in kg
            dimensions: Dimensions (length, width, height in cm)
            
        Returns:
            Freight rate information
        """
        try:
            params = {
                "origin": origin,
                "destination": destination,
                "weight": weight
            }
            
            if dimensions:
                params.update(dimensions)
            
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="rates",
                method="GET",
                params=params
            )
            
            if response.get("success"):
                data = response.get("data", {})
                return {
                    "rates": data.get("rates", []),
                    "currency": data.get("currency", "USD"),
                    "valid_until": data.get("valid_until")
                }
            else:
                logger.error(f"Failed to get freight rates: {response.get('error')}")
                return {"error": response.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to get freight rates: {e}")
            return {"error": str(e)}

    def get_inventory_status(
        self,
        provider_id: int,
        warehouse_id: str,
        sku: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get inventory status from warehouse.
        
        Args:
            provider_id: External API provider ID
            warehouse_id: Warehouse ID
            sku: Optional SKU to check specific item
            
        Returns:
            Inventory status
        """
        try:
            params = {"warehouse_id": warehouse_id}
            if sku:
                params["sku"] = sku
            
            response = self.api_service.call_api(
                provider_id=provider_id,
                endpoint_key="inventory",
                method="GET",
                params=params
            )
            
            if response.get("success"):
                data = response.get("data", {})
                return {
                    "warehouse_id": warehouse_id,
                    "total_items": data.get("total_items", 0),
                    "available_items": data.get("available_items", 0),
                    "items": data.get("items", []),
                    "last_updated": data.get("last_updated")
                }
            else:
                logger.error(f"Failed to get inventory status: {response.get('error')}")
                return {"error": response.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to get inventory status: {e}")
            return {"error": str(e)}

    def update_document_metadata_from_api(
        self,
        document_id: int,
        provider_id: int,
        bl_number: str
    ) -> bool:
        """
        Update document metadata from shipping API.
        
        Args:
            document_id: Document ID to update
            provider_id: External API provider ID
            bl_number: Bill of Lading number
            
        Returns:
            True if successful
        """
        try:
            from app.models.database import Document
            
            # Get tracking info
            tracking_info = self.track_shipment(provider_id, bl_number)
            if "error" in tracking_info:
                return False

            # Get ETA
            eta = self.get_eta(provider_id, bl_number)

            # Update document metadata
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return False

            metadata = doc.extracted_metadata or {}
            metadata["shipping_tracking"] = tracking_info
            metadata["eta"] = eta
            doc.extracted_metadata = metadata
            doc.updated_at = None  # Will be set by onupdate

            self.db.commit()
            
            logger.info(f"Updated document {document_id} with shipping data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document metadata: {e}")
            self.db.rollback()
            return False


# Global shipping integration service instance (initialized per request)
def get_shipping_integration_service(db: Session) -> ShippingIntegrationService:
    """Factory function to get ShippingIntegrationService instance."""
    return ShippingIntegrationService(db)