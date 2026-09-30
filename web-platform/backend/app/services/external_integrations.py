"""
External System Integrations Service
Provides integration with ERP, CRM, and other external systems
"""
import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class IntegrationType(Enum):
    """Integration types"""
    ERP = "erp"
    CRM = "crm"
    ACCOUNTING = "accounting"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class IntegrationStatus(Enum):
    """Integration status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"


@dataclass
class IntegrationConfig:
    """Integration configuration"""
    id: str
    name: str
    type: IntegrationType
    status: IntegrationStatus
    config: Dict[str, Any]
    webhooks: List[str]
    last_sync: Optional[datetime] = None
    created_at: datetime = None


class ExternalIntegrationService:
    """Service for external system integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    def create_integration(
        self,
        name: str,
        integration_type: IntegrationType,
        config: Dict[str, Any],
        webhooks: List[str] = None
    ) -> IntegrationConfig:
        """Create new integration"""
        try:
            import uuid
            integration_id = str(uuid.uuid4())
            
            integration = IntegrationConfig(
                id=integration_id,
                name=name,
                type=integration_type,
                status=IntegrationStatus.INACTIVE,
                config=config,
                webhooks=webhooks or [],
                created_at=datetime.utcnow()
            )
            
            self.integrations[integration_id] = integration
            
            logger.info(f"Created integration {integration_id}: {name}")
            return integration
            
        except Exception as e:
            logger.error(f"Failed to create integration: {e}")
            raise
    
    def activate_integration(self, integration_id: str) -> Dict[str, Any]:
        """Activate integration"""
        try:
            if integration_id not in self.integrations:
                return {"success": False, "error": "Integration not found"}
            
            integration = self.integrations[integration_id]
            integration.status = IntegrationStatus.ACTIVE
            
            logger.info(f"Activated integration {integration_id}")
            return {"success": True, "message": "Integration activated"}
            
        except Exception as e:
            logger.error(f"Failed to activate integration: {e}")
            return {"success": False, "error": str(e)}
    
    def deactivate_integration(self, integration_id: str) -> Dict[str, Any]:
        """Deactivate integration"""
        try:
            if integration_id not in self.integrations:
                return {"success": False, "error": "Integration not found"}
            
            integration = self.integrations[integration_id]
            integration.status = IntegrationStatus.INACTIVE
            
            logger.info(f"Deactivated integration {integration_id}")
            return {"success": True, "message": "Integration deactivated"}
            
        except Exception as e:
            logger.error(f"Failed to deactivate integration: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_document_to_erp(
        self,
        integration_id: str,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to ERP system"""
        try:
            integration = self.integrations.get(integration_id)
            
            if not integration or integration.type != IntegrationType.ERP:
                return {"success": False, "error": "Invalid ERP integration"}
            
            if integration.status != IntegrationStatus.ACTIVE:
                return {"success": False, "error": "Integration not active"}
            
            # Configure API endpoint based on ERP type
            erp_type = integration.config.get("erp_type", "generic")
            
            if erp_type == "sap":
                result = await self._sync_to_sap(integration, document_data)
            elif erp_type == "oracle":
                result = await self._sync_to_oracle(integration, document_data)
            elif erp_type == "microsoft_dynamics":
                result = await self._sync_to_dynamics(integration, document_data)
            else:
                result = await self._sync_to_generic_erp(integration, document_data)
            
            # Update last sync time
            integration.last_sync = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync document to ERP: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_document_to_crm(
        self,
        integration_id: str,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to CRM system"""
        try:
            integration = self.integrations.get(integration_id)
            
            if not integration or integration.type != IntegrationType.CRM:
                return {"success": False, "error": "Invalid CRM integration"}
            
            if integration.status != IntegrationStatus.ACTIVE:
                return {"success": False, "error": "Integration not active"}
            
            # Configure API endpoint based on CRM type
            crm_type = integration.config.get("crm_type", "generic")
            
            if crm_type == "salesforce":
                result = await self._sync_to_salesforce(integration, document_data)
            elif crm_type == "hubspot":
                result = await self._sync_to_hubspot(integration, document_data)
            elif crm_type == "microsoft_dynamics_365":
                result = await self._sync_to_dynamics_365(integration, document_data)
            else:
                result = await self._sync_to_generic_crm(integration, document_data)
            
            # Update last sync time
            integration.last_sync = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync document to CRM: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_document_to_accounting(
        self,
        integration_id: str,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to accounting system"""
        try:
            integration = self.integrations.get(integration_id)
            
            if not integration or integration.type != IntegrationType.ACCOUNTING:
                return {"success": False, "error": "Invalid accounting integration"}
            
            if integration.status != IntegrationStatus.ACTIVE:
                return {"success": False, "error": "Integration not active"}
            
            # Configure API endpoint based on accounting type
            accounting_type = integration.config.get("accounting_type", "generic")
            
            if accounting_type == "quickbooks":
                result = await self._sync_to_quickbooks(integration, document_data)
            elif accounting_type == "xero":
                result = await self._sync_to_xero(integration, document_data)
            elif accounting_type == "sage":
                result = await self._sync_to_sage(integration, document_data)
            else:
                result = await self._sync_to_generic_accounting(integration, document_data)
            
            # Update last sync time
            integration.last_sync = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync document to accounting: {e}")
            return {"success": False, "error": str(e)}
    
    async def trigger_webhook(
        self,
        integration_id: str,
        webhook_url: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger webhook integration"""
        try:
            integration = self.integrations.get(integration_id)
            
            if not integration:
                return {"success": False, "error": "Integration not found"}
            
            if integration.status != IntegrationStatus.ACTIVE:
                return {"success": False, "error": "Integration not active"}
            
            # Send webhook
            headers = {
                "Content-Type": "application/json",
                "X-Integration-ID": integration_id,
                "X-Timestamp": datetime.utcnow().isoformat()
            }
            
            # Add custom headers from config
            custom_headers = integration.config.get("webhook_headers", {})
            headers.update(custom_headers)
            
            response = await self.http_client.post(
                webhook_url,
                json=data,
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook triggered successfully: {webhook_url}")
                return {"success": True, "status_code": response.status_code}
            else:
                logger.error(f"Webhook failed: {response.status_code}")
                return {"success": False, "status_code": response.status_code, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to trigger webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_sap(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to SAP ERP system"""
        try:
            # SAP-specific integration logic
            sap_config = integration.config
            api_url = sap_config.get("api_url")
            api_key = sap_config.get("api_key")
            
            # Transform document data to SAP format
            sap_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "metadata": document_data.get("extracted_metadata", {}),
                "content": document_data.get("ocr_text", "")
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/documents",
                json=sap_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "sap_document_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to SAP: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_oracle(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Oracle ERP system"""
        try:
            # Oracle-specific integration logic
            oracle_config = integration.config
            api_url = oracle_config.get("api_url")
            api_key = oracle_config.get("api_key")
            
            # Transform document data to Oracle format
            oracle_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "metadata": document_data.get("extracted_metadata", {})
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/rest/documents",
                json=oracle_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "oracle_document_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Oracle: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_dynamics(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Microsoft Dynamics ERP system"""
        try:
            # Dynamics-specific integration logic
            dynamics_config = integration.config
            api_url = dynamics_config.get("api_url")
            api_key = dynamics_config.get("api_key")
            
            # Transform document data to Dynamics format
            dynamics_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "metadata": document_data.get("extracted_metadata", {})
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/data/v9.0/dms_documents",
                json=dynamics_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "dynamics_document_id": response.json().get("dms_documentid")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Dynamics: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_generic_erp(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to generic ERP system"""
        try:
            # Generic ERP integration logic
            erp_config = integration.config
            api_url = erp_config.get("api_url")
            api_key = erp_config.get("api_key")
            
            # Transform document data to generic format
            generic_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "metadata": document_data.get("extracted_metadata", {}),
                "content": document_data.get("ocr_text", "")
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/documents",
                json=generic_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "external_document_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to generic ERP: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_salesforce(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Salesforce CRM"""
        try:
            # Salesforce-specific integration logic
            salesforce_config = integration.config
            api_url = salesforce_config.get("api_url")
            access_token = salesforce_config.get("access_token")
            
            # Transform document data to Salesforce format
            salesforce_data = {
                "Name": document_data.get("original_filename"),
                "Document_Type__c": document_data.get("function_type"),
                "Content_Version__c": document_data.get("ocr_text", ""),
                "Metadata__c": json.dumps(document_data.get("extracted_metadata", {}))
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/services/data/v57.0/sobjects/ContentDocument",
                json=salesforce_data,
                headers=headers
            )
            
            if response.status_code == 201:
                return {"success": True, "salesforce_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Salesforce: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_hubspot(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to HubSpot CRM"""
        try:
            # HubSpot-specific integration logic
            hubspot_config = integration.config
            api_url = hubspot_config.get("api_url")
            api_key = hubspot_config.get("api_key")
            
            # Transform document data to HubSpot format
            hubspot_data = {
                "properties": {
                    "document_type": document_data.get("function_type"),
                    "file_name": document_data.get("original_filename"),
                    "content": document_data.get("ocr_text", "")[:5000]
                }
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/crm/v3/objects/documents",
                json=hubspot_data,
                headers=headers
            )
            
            if response.status_code == 201:
                return {"success": True, "hubspot_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to HubSpot: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_dynamics_365(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Microsoft Dynamics 365 CRM"""
        try:
            # Dynamics 365-specific integration logic
            dynamics_config = integration.config
            api_url = dynamics_config.get("api_url")
            api_key = dynamics_config.get("api_key")
            
            # Transform document data to Dynamics 365 format
            dynamics_data = {
                "documentname": document_data.get("original_filename"),
                "documenttype": document_data.get("function_type"),
                "content": document_data.get("ocr_text", "")
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/data/v9.2/dms_documents",
                json=dynamics_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "dynamics_id": response.json().get("dms_documentid")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Dynamics 365: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_generic_crm(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to generic CRM system"""
        try:
            # Generic CRM integration logic
            crm_config = integration.config
            api_url = crm_config.get("api_url")
            api_key = crm_config.get("api_key")
            
            # Transform document data to generic format
            generic_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "metadata": document_data.get("extracted_metadata", {}),
                "content": document_data.get("ocr_text", "")
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/documents",
                json=generic_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "external_document_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to generic CRM: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_quickbooks(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to QuickBooks accounting"""
        try:
            # QuickBooks-specific integration logic
            quickbooks_config = integration.config
            api_url = quickbooks_config.get("api_url")
            access_token = quickbooks_config.get("access_token")
            
            # Transform document data to QuickBooks format
            quickbooks_data = {
                "Type": "Invoice",
                "DocNumber": document_data.get("id"),
                "Line": [
                    {
                        "Description": document_data.get("original_filename"),
                        "Amount": document_data.get("extracted_metadata", {}).get("amount", 0)
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/v3/company/123456789/invoice",
                json=quickbooks_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "quickbooks_id": response.json().get("Invoice").get("Id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to QuickBooks: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_xero(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Xero accounting"""
        try:
            # Xero-specific integration logic
            xero_config = integration.config
            api_url = xero_config.get("api_url")
            api_key = xero_config.get("api_key")
            
            # Transform document data to Xero format
            xero_data = {
                "Type": "ACCREC",
                "Contact": {
                    "Name": document_data.get("extracted_metadata", {}).get("vendor", "Unknown")
                },
                "LineItems": [
                    {
                        "Description": document_data.get("original_filename"),
                        "Quantity": 1,
                        "UnitAmount": document_data.get("extracted_metadata", {}).get("amount", 0)
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/Invoices",
                json=xero_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "xero_id": response.json().get("Invoices")[0].get("InvoiceID")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Xero: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_sage(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to Sage accounting"""
        try:
            # Sage-specific integration logic
            sage_config = integration.config
            api_url = sage_config.get("api_url")
            api_key = sage_config.get("api_key")
            
            # Transform document data to Sage format
            sage_data = {
                "invoice_type": "SALES",
                "document_id": document_data.get("id"),
                "amount": document_data.get("extracted_metadata", {}).get("amount", 0),
                "description": document_data.get("original_filename")
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/invoices",
                json=sage_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "sage_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to Sage: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_to_generic_accounting(
        self,
        integration: IntegrationConfig,
        document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync to generic accounting system"""
        try:
            # Generic accounting integration logic
            accounting_config = integration.config
            api_url = accounting_config.get("api_url")
            api_key = accounting_config.get("api_key")
            
            # Transform document data to generic format
            generic_data = {
                "document_type": document_data.get("function_type"),
                "document_id": document_data.get("id"),
                "amount": document_data.get("extracted_metadata", {}).get("amount", 0),
                "metadata": document_data.get("extracted_metadata", {})
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(
                f"{api_url}/api/documents",
                json=generic_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "external_document_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}
            
        except Exception as e:
            logger.error(f"Failed to sync to generic accounting: {e}")
            return {"success": False, "error": str(e)}
    
    def get_integrations(self) -> List[IntegrationConfig]:
        """Get all integrations"""
        return list(self.integrations.values())
    
    def get_integration(self, integration_id: str) -> Optional[IntegrationConfig]:
        """Get specific integration"""
        return self.integrations.get(integration_id)
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Singleton instance
_integration_service: Optional[ExternalIntegrationService] = None


def get_integration_service() -> ExternalIntegrationService:
    """Get singleton integration service"""
    global _integration_service
    if _integration_service is None:
        _integration_service = ExternalIntegrationService()
    return _integration_service