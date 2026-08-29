"""
External API Service - Integration with external logistics APIs (Customs, Shipping, etc.)
"""
import requests
import json
import time
import os
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from sqlalchemy.orm import Session
from app.models.database import ExternalAPIProvider, ExternalAPILog
from app.core.config import settings
from app.core.encryption import encryption_manager

# Try to import tenacity for retry logic
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    logger.warning("tenacity not installed - using basic retry logic")
    TENACITY_AVAILABLE = False


class ExternalAPIService:
    """Service for managing external API integrations with retry logic."""

    def __init__(self, db: Session):
        self.db = db
        self.request_timeout = int(os.getenv('EXTERNAL_API_TIMEOUT', '30'))  # seconds
        self.max_retries = int(os.getenv('EXTERNAL_API_RETRY_ATTEMPTS', '3'))
        self.retry_delays = [1, 5, 15]  # Exponential backoff: 1s, 5s, 15s

    def register_api_provider(
        self,
        name: str,
        provider_type: str,
        base_url: str,
        auth_type: str,
        auth_config: Dict[str, Any],
        endpoints: Dict[str, str],
        webhook_secret: Optional[str] = None
    ) -> ExternalAPIProvider:
        """
        Register a new external API provider.
        
        Args:
            name: Provider name (e.g., "Myanmar Customs")
            provider_type: Type (customs, shipping, freight, warehouse)
            base_url: API base URL
            auth_type: Authentication type (api_key, oauth2, basic)
            auth_config: Authentication configuration (encrypted)
            endpoints: Available endpoints
            webhook_secret: Secret for webhook verification (optional)
            
        Returns:
            Created provider
        """
        try:
            # Encrypt sensitive auth config
            encrypted_config = encryption_manager.encrypt(json.dumps(auth_config))
            
            provider = ExternalAPIProvider(
                name=name,
                provider_type=provider_type,
                base_url=base_url,
                auth_type=auth_type,
                auth_config=encrypted_config,
                endpoints=endpoints,
                enabled=True,
                webhook_secret=encryption_manager.encrypt(webhook_secret) if webhook_secret else None,
                created_at=datetime.utcnow(),
                last_used=None
            )
            
            self.db.add(provider)
            self.db.commit()
            self.db.refresh(provider)
            
            logger.info(f"Registered API provider: {name} ({provider_type})")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to register API provider: {e}")
            self.db.rollback()
            raise

    def get_api_provider(self, name: str) -> Optional[ExternalAPIProvider]:
        """Get an API provider by name."""
        return self.db.query(ExternalAPIProvider).filter(
            ExternalAPIProvider.name == name,
            ExternalAPIProvider.enabled == True
        ).first()

    def get_api_provider_by_id(self, provider_id: int) -> Optional[ExternalAPIProvider]:
        """Get an API provider by ID."""
        return self.db.query(ExternalAPIProvider).filter(
            ExternalAPIProvider.id == provider_id
        ).first()

    def update_api_provider(
        self,
        provider_id: int,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_config: Optional[Dict] = None,
        endpoints: Optional[Dict] = None,
        enabled: Optional[bool] = None
    ) -> Optional[ExternalAPIProvider]:
        """Update an existing API provider."""
        try:
            provider = self.get_api_provider_by_id(provider_id)
            if not provider:
                return None

            if name:
                provider.name = name
            if base_url:
                provider.base_url = base_url
            if auth_config:
                provider.auth_config = encryption_manager.encrypt(json.dumps(auth_config))
            if endpoints:
                provider.endpoints = endpoints
            if enabled is not None:
                provider.enabled = enabled

            self.db.commit()
            self.db.refresh(provider)
            
            logger.info(f"Updated API provider: {provider.name}")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to update API provider: {e}")
            self.db.rollback()
            raise

    def delete_api_provider(self, provider_id: int) -> bool:
        """Delete an API provider."""
        try:
            provider = self.get_api_provider_by_id(provider_id)
            if not provider:
                return False

            self.db.delete(provider)
            self.db.commit()
            
            logger.info(f"Deleted API provider: {provider.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete API provider: {e}")
            self.db.rollback()
            raise

    def test_connection(self, provider_id: int) -> Dict[str, Any]:
        """
        Test connection to an API provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Connection test result
        """
        try:
            provider = self.get_api_provider_by_id(provider_id)
            if not provider:
                return {"success": False, "error": "Provider not found"}

            # Try a simple health check or endpoint
            # For now, just test base URL
            try:
                response = requests.get(
                    provider.base_url,
                    timeout=10
                )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except requests.exceptions.RequestException as e:
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logger.error(f"Failed to test connection: {e}")
            return {"success": False, "error": str(e)}

    def call_api(
        self,
        provider_id: int,
        endpoint_key: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a generic API call to a provider with retry logic.
        
        Args:
            provider_id: Provider ID
            endpoint_key: Endpoint key from provider's endpoints config
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            API response
        """
        try:
            provider = self.get_api_provider_by_id(provider_id)
            if not provider:
                return {"success": False, "error": "Provider not found"}

            if not provider.enabled:
                return {"success": False, "error": "Provider is disabled"}

            # Get endpoint URL
            endpoint_template = provider.endpoints.get(endpoint_key)
            if not endpoint_template:
                return {"success": False, "error": f"Endpoint '{endpoint_key}' not found"}

            endpoint_url = provider.base_url + endpoint_template

            # Prepare auth headers
            auth_config = json.loads(encryption_manager.decrypt(provider.auth_config))
            auth_headers = self._prepare_auth_headers(provider.auth_type, auth_config)

            # Merge headers
            final_headers = {**(headers or {}), **auth_headers}

            # Log request
            log_entry = ExternalAPILog(
                provider_id=provider_id,
                document_id=None,  # Can be set if document is associated
                endpoint=endpoint_key,
                request=json.dumps({"method": method, "data": data, "params": params}),
                response=None,
                status_code=None,
                error=None,
                timestamp=datetime.utcnow()
            )
            self.db.add(log_entry)

            # Make API call with retry logic and exponential backoff
            response = None
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    # Calculate retry delay
                    if attempt > 0:
                        delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                        logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {delay}s delay...")
                        time.sleep(delay)

                    if method == "GET":
                        response = requests.get(
                            endpoint_url,
                            params=params,
                            headers=final_headers,
                            timeout=self.request_timeout
                        )
                    elif method == "POST":
                        response = requests.post(
                            endpoint_url,
                            json=data,
                            params=params,
                            headers=final_headers,
                            timeout=self.request_timeout
                        )
                    elif method == "PUT":
                        response = requests.put(
                            endpoint_url,
                            json=data,
                            params=params,
                            headers=final_headers,
                            timeout=self.request_timeout
                        )
                    elif method == "DELETE":
                        response = requests.delete(
                            endpoint_url,
                            params=params,
                            headers=final_headers,
                            timeout=self.request_timeout
                        )
                    
                    # Check for 5xx server errors (retryable)
                    if response.status_code >= 500:
                        if attempt == self.max_retries - 1:
                            raise requests.exceptions.HTTPError(f"Server error: {response.status_code}")
                        logger.warning(f"Server error {response.status_code}, retrying...")
                        last_exception = requests.exceptions.HTTPError(f"Server error: {response.status_code}")
                        continue
                    
                    # Success
                    logger.info(f"API call successful (attempt {attempt + 1})")
                    break
                    
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        log_entry.error = f"Request timeout after {self.max_retries} retries"
                        log_entry.status_code = 408
                        self.db.commit()
                        return {"success": False, "error": f"Request timeout after {self.max_retries} retries"}
                    
                except requests.exceptions.ConnectionError as e:
                    last_exception = e
                    logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        log_entry.error = f"Connection error after {self.max_retries} retries: {e}"
                        log_entry.status_code = 503
                        self.db.commit()
                        return {"success": False, "error": f"Connection error: {e}"}
                    
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    logger.warning(f"Request exception (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        log_entry.error = f"Request failed after {self.max_retries} retries: {e}"
                        self.db.commit()
                        return {"success": False, "error": f"Request failed: {e}"}
                    
                except Exception as e:
                    last_exception = e
                    logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        log_entry.error = f"Unexpected error: {e}"
                        self.db.commit()
                        return {"success": False, "error": f"Unexpected error: {e}"}

            # Update log with response
            log_entry.status_code = response.status_code if response else None
            log_entry.response = json.dumps(response.json()) if response and response.content else None
            provider.last_used = datetime.utcnow()
            self.db.commit()

            return {
                "success": response.status_code < 400 if response else False,
                "status_code": response.status_code if response else None,
                "data": response.json() if response and response.content else None,
                "headers": dict(response.headers) if response else None
            }

        except Exception as e:
            logger.error(f"Failed to call API: {e}")
            return {"success": False, "error": str(e)}

    def verify_webhook(self, provider_name: str, payload: str, signature: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            provider_name: Provider name
            payload: Raw webhook payload
            signature: Webhook signature header
            
        Returns:
            True if signature is valid
        """
        try:
            provider = self.get_api_provider(provider_name)
            if not provider or not provider.webhook_secret:
                return False

            secret = encryption_manager.decrypt(provider.webhook_secret)
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Failed to verify webhook: {e}")
            return False

    def _prepare_auth_headers(self, auth_type: str, auth_config: Dict) -> Dict[str, str]:
        """Prepare authentication headers based on auth type."""
        headers = {}
        
        if auth_type == "api_key":
            # API Key authentication
            api_key = auth_config.get("api_key")
            header_name = auth_config.get("header_name", "X-API-Key")
            headers[header_name] = api_key
            
        elif auth_type == "bearer":
            # Bearer token
            token = auth_config.get("token")
            headers["Authorization"] = f"Bearer {token}"
            
        elif auth_type == "basic":
            # Basic authentication
            username = auth_config.get("username")
            password = auth_config.get("password")
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
            
        return headers

    def list_all_providers(self, enabled_only: bool = False) -> List[ExternalAPIProvider]:
        """List all API providers."""
        query = self.db.query(ExternalAPIProvider)
        if enabled_only:
            query = query.filter(ExternalAPIProvider.enabled == True)
        return query.order_by(ExternalAPIProvider.created_at.desc()).all()

    def get_provider_logs(self, provider_id: int, limit: int = 100) -> List[ExternalAPILog]:
        """Get API call logs for a provider."""
        return self.db.query(ExternalAPILog).filter(
            ExternalAPILog.provider_id == provider_id
        ).order_by(ExternalAPILog.timestamp.desc()).limit(limit).all()


# Global external API service instance (initialized per request)
def get_external_api_service(db: Session) -> ExternalAPIService:
    """Factory function to get ExternalAPIService instance."""
    return ExternalAPIService(db)