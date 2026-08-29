"""
API Rate Limiting & Quotas Service
Provides user-based rate limiting, API usage tracking, and quota management
"""
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class RateLimitRule:
    """Rate limit rule definition"""
    id: str
    name: str
    endpoint: str  # * for all endpoints
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    user_roles: List[str]  # empty for all users


@dataclass
class UserQuota:
    """User quota definition"""
    user_id: int
    daily_requests: int
    daily_storage_mb: int
    monthly_requests: int
    monthly_storage_mb: int
    reset_date: datetime


@dataclass
class APIUsage:
    """API usage tracking"""
    user_id: int
    endpoint: str
    timestamp: datetime
    status_code: int
    response_time_ms: float


class RateLimitingService:
    """Service for API rate limiting and quota management"""
    
    def __init__(self):
        self.rules_storage_path = Path("storage/rate_limit_rules")
        self.rules_storage_path.mkdir(parents=True, exist_ok=True)
        self.usage_storage_path = Path("storage/api_usage")
        self.usage_storage_path.mkdir(parents=True, exist_ok=True)
        self.quotas_storage_path = Path("storage/user_quotas")
        self.quotas_storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for rate limiting (production would use Redis)
        self.request_cache: Dict[str, List[datetime]] = {}
        
        # Load default rules
        self._load_default_rules()
        
    def _load_default_rules(self):
        """Load default rate limiting rules"""
        default_rules = [
            RateLimitRule(
                id="default",
                name="Default Rate Limit",
                endpoint="*",
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=10000,
                user_roles=[]
            ),
            RateLimitRule(
                id="admin",
                name="Admin Rate Limit",
                endpoint="*",
                requests_per_minute=120,
                requests_per_hour=2000,
                requests_per_day=20000,
                user_roles=["admin"]
            ),
            RateLimitRule(
                id="api",
                name="API Rate Limit",
                endpoint="/api/*",
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=5000,
                user_roles=[]
            )
        ]
        
        for rule in default_rules:
            self._save_rate_limit_rule(rule)
    
    def check_rate_limit(
        self,
        user_id: int,
        user_role: str,
        endpoint: str
    ) -> Dict[str, Any]:
        """Check if request is within rate limits"""
        try:
            # Get applicable rules
            rules = self._get_applicable_rules(user_role, endpoint)
            
            if not rules:
                return {"allowed": True, "limit": None, "remaining": None}
            
            # Check each rule
            for rule in rules:
                result = self._check_rule(user_id, rule)
                
                if not result["allowed"]:
                    return result
            
            return {"allowed": True, "limit": None, "remaining": None}
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {"allowed": True, "limit": None, "remaining": None}  # Fail open
    
    def _check_rule(self, user_id: int, rule: RateLimitRule) -> Dict[str, Any]:
        """Check specific rate limit rule"""
        cache_key = f"{user_id}:{rule.id}"
        current_time = datetime.utcnow()
        
        # Get request history
        if cache_key not in self.request_cache:
            self.request_cache[cache_key] = []
        
        requests = self.request_cache[cache_key]
        
        # Clean old requests (older than 1 day)
        requests = [req for req in requests if current_time - req < timedelta(days=1)]
        self.request_cache[cache_key] = requests
        
        # Check per-minute limit
        minute_ago = current_time - timedelta(minutes=1)
        minute_requests = [req for req in requests if req > minute_ago]
        
        if len(minute_requests) >= rule.requests_per_minute:
            return {
                "allowed": False,
                "limit": rule.requests_per_minute,
                "remaining": 0,
                "reset": (minute_requests[0] + timedelta(minutes=1)).isoformat(),
                "error": "Rate limit exceeded (per minute)"
            }
        
        # Check per-hour limit
        hour_ago = current_time - timedelta(hours=1)
        hour_requests = [req for req in requests if req > hour_ago]
        
        if len(hour_requests) >= rule.requests_per_hour:
            return {
                "allowed": False,
                "limit": rule.requests_per_hour,
                "remaining": 0,
                "reset": (hour_requests[0] + timedelta(hours=1)).isoformat(),
                "error": "Rate limit exceeded (per hour)"
            }
        
        # Check per-day limit
        day_ago = current_time - timedelta(days=1)
        day_requests = [req for req in requests if req > day_ago]
        
        if len(day_requests) >= rule.requests_per_day:
            return {
                "allowed": False,
                "limit": rule.requests_per_day,
                "remaining": 0,
                "reset": (day_requests[0] + timedelta(days=1)).isoformat(),
                "error": "Rate limit exceeded (per day)"
            }
        
        # Request allowed, add to cache
        self.request_cache[cache_key].append(current_time)
        
        return {
            "allowed": True,
            "limit": rule.requests_per_day,
            "remaining": rule.requests_per_day - len(day_requests)
        }
    
    def _get_applicable_rules(self, user_role: str, endpoint: str) -> List[RateLimitRule]:
        """Get applicable rate limit rules"""
        try:
            rules = []
            
            for rule_file in self.rules_storage_path.glob("*.json"):
                with open(rule_file, 'r') as f:
                    rule_data = json.load(f)
                
                rule = RateLimitRule(
                    id=rule_data["id"],
                    name=rule_data["name"],
                    endpoint=rule_data["endpoint"],
                    requests_per_minute=rule_data["requests_per_minute"],
                    requests_per_hour=rule_data["requests_per_hour"],
                    requests_per_day=rule_data["requests_per_day"],
                    user_roles=rule_data.get("user_roles", [])
                )
                
                # Check if rule applies
                if self._rule_applies(rule, user_role, endpoint):
                    rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to get applicable rules: {e}")
            return []
    
    def _rule_applies(self, rule: RateLimitRule, user_role: str, endpoint: str) -> bool:
        """Check if rule applies to user and endpoint"""
        # Check user role
        if rule.user_roles and user_role not in rule.user_roles:
            return False
        
        # Check endpoint
        if rule.endpoint == "*":
            return True
        
        if rule.endpoint.endswith("*"):
            prefix = rule.endpoint[:-1]
            return endpoint.startswith(prefix)
        
        return endpoint == rule.endpoint
    
    def track_api_usage(
        self,
        user_id: int,
        endpoint: str,
        status_code: int,
        response_time_ms: float
    ):
        """Track API usage"""
        try:
            usage = APIUsage(
                user_id=user_id,
                endpoint=endpoint,
                timestamp=datetime.utcnow(),
                status_code=status_code,
                response_time_ms=response_time_ms
            )
            
            # Save usage
            self._save_api_usage(usage)
            
        except Exception as e:
            logger.error(f"Failed to track API usage: {e}")
    
    def get_user_usage_stats(
        self,
        user_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get user API usage statistics"""
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=7)
            if not date_to:
                date_to = datetime.utcnow()
            
            # Get usage records
            usage_records = self._get_user_usage(user_id, date_from, date_to)
            
            # Calculate statistics
            total_requests = len(usage_records)
            successful_requests = len([u for u in usage_records if u.status_code < 400])
            failed_requests = len([u for u in usage_records if u.status_code >= 400])
            
            avg_response_time = 0
            if usage_records:
                avg_response_time = sum(u.response_time_ms for u in usage_records) / len(usage_records)
            
            # Requests by endpoint
            endpoint_counts = {}
            for usage in usage_records:
                endpoint_counts[usage.endpoint] = endpoint_counts.get(usage.endpoint, 0) + 1
            
            return {
                "success": True,
                "user_id": user_id,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "requests_by_endpoint": endpoint_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get user usage stats: {e}")
            return {"success": False, "error": str(e)}
    
    def set_user_quota(
        self,
        user_id: int,
        daily_requests: int,
        daily_storage_mb: int,
        monthly_requests: int,
        monthly_storage_mb: int
    ) -> UserQuota:
        """Set user quota"""
        try:
            quota = UserQuota(
                user_id=user_id,
                daily_requests=daily_requests,
                daily_storage_mb=daily_storage_mb,
                monthly_requests=monthly_requests,
                monthly_storage_mb=monthly_storage_mb,
                reset_date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            )
            
            self._save_user_quota(quota)
            
            logger.info(f"Set quota for user {user_id}")
            return quota
            
        except Exception as e:
            logger.error(f"Failed to set user quota: {e}")
            raise
    
    def check_user_quota(self, user_id: int) -> Dict[str, Any]:
        """Check if user is within quota"""
        try:
            quota = self.get_user_quota(user_id)
            
            if not quota:
                return {"allowed": True, "quota": None}
            
            # Check if quota needs reset
            if datetime.utcnow() >= quota.reset_date:
                # Reset quota
                quota.reset_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                self._save_user_quota(quota)
            
            # Get current usage
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            usage_records = self._get_user_usage(user_id, today, datetime.utcnow())
            
            daily_requests_used = len(usage_records)
            
            # Check daily request quota
            if daily_requests_used >= quota.daily_requests:
                return {
                    "allowed": False,
                    "quota": {
                        "daily_requests": quota.daily_requests,
                        "daily_requests_used": daily_requests_used,
                        "reset_date": quota.reset_date.isoformat()
                    },
                    "error": "Daily request quota exceeded"
                }
            
            return {
                "allowed": True,
                "quota": {
                    "daily_requests": quota.daily_requests,
                    "daily_requests_used": daily_requests_used,
                    "daily_requests_remaining": quota.daily_requests - daily_requests_used,
                    "reset_date": quota.reset_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to check user quota: {e}")
            return {"allowed": True, "quota": None}  # Fail open
    
    def get_user_quota(self, user_id: int) -> Optional[UserQuota]:
        """Get user quota"""
        try:
            quota_file = self.quotas_storage_path / f"{user_id}.json"
            
            if not quota_file.exists():
                return None
            
            with open(quota_file, 'r') as f:
                quota_data = json.load(f)
            
            quota = UserQuota(
                user_id=quota_data["user_id"],
                daily_requests=quota_data["daily_requests"],
                daily_storage_mb=quota_data["daily_storage_mb"],
                monthly_requests=quota_data["monthly_requests"],
                monthly_storage_mb=quota_data["monthly_storage_mb"],
                reset_date=datetime.fromisoformat(quota_data["reset_date"])
            )
            
            return quota
            
        except Exception as e:
            logger.error(f"Failed to get user quota: {e}")
            return None
    
    def _save_rate_limit_rule(self, rule: RateLimitRule):
        """Save rate limit rule to file"""
        rule_file = self.rules_storage_path / f"{rule.id}.json"
        
        rule_data = {
            "id": rule.id,
            "name": rule.name,
            "endpoint": rule.endpoint,
            "requests_per_minute": rule.requests_per_minute,
            "requests_per_hour": rule.requests_per_hour,
            "requests_per_day": rule.requests_per_day,
            "user_roles": rule.user_roles
        }
        
        with open(rule_file, 'w') as f:
            json.dump(rule_data, f, indent=2)
    
    def _save_api_usage(self, usage: APIUsage):
        """Save API usage to file"""
        usage_file = self.usage_storage_path / f"{usage.user_id}_{usage.timestamp.strftime('%Y%m%d')}.json"
        
        # Load existing usage
        if usage_file.exists():
            with open(usage_file, 'r') as f:
                usage_data = json.load(f)
        else:
            usage_data = []
        
        # Add new usage
        usage_data.append({
            "user_id": usage.user_id,
            "endpoint": usage.endpoint,
            "timestamp": usage.timestamp.isoformat(),
            "status_code": usage.status_code,
            "response_time_ms": usage.response_time_ms
        })
        
        # Save usage
        with open(usage_file, 'w') as f:
            json.dump(usage_data, f, indent=2)
    
    def _get_user_usage(self, user_id: int, date_from: datetime, date_to: datetime) -> List[APIUsage]:
        """Get user API usage records"""
        try:
            usage_records = []
            
            # Get usage files for date range
            current_date = date_from.date()
            end_date = date_to.date()
            
            while current_date <= end_date:
                usage_file = self.usage_storage_path / f"{user_id}_{current_date.strftime('%Y%m%d')}.json"
                
                if usage_file.exists():
                    with open(usage_file, 'r') as f:
                        usage_data = json.load(f)
                    
                    for usage_item in usage_data:
                        usage = APIUsage(
                            user_id=usage_item["user_id"],
                            endpoint=usage_item["endpoint"],
                            timestamp=datetime.fromisoformat(usage_item["timestamp"]),
                            status_code=usage_item["status_code"],
                            response_time_ms=usage_item["response_time_ms"]
                        )
                        
                        if date_from <= usage.timestamp <= date_to:
                            usage_records.append(usage)
                
                current_date += timedelta(days=1)
            
            return usage_records
            
        except Exception as e:
            logger.error(f"Failed to get user usage: {e}")
            return []
    
    def _save_user_quota(self, quota: UserQuota):
        """Save user quota to file"""
        quota_file = self.quotas_storage_path / f"{quota.user_id}.json"
        
        quota_data = {
            "user_id": quota.user_id,
            "daily_requests": quota.daily_requests,
            "daily_storage_mb": quota.daily_storage_mb,
            "monthly_requests": quota.monthly_requests,
            "monthly_storage_mb": quota.monthly_storage_mb,
            "reset_date": quota.reset_date.isoformat()
        }
        
        with open(quota_file, 'w') as f:
            json.dump(quota_data, f, indent=2)


# Singleton instance
_rate_limiting_service: Optional[RateLimitingService] = None


def get_rate_limiting_service() -> RateLimitingService:
    """Get singleton rate limiting service"""
    global _rate_limiting_service
    if _rate_limiting_service is None:
        _rate_limiting_service = RateLimitingService()
    return _rate_limiting_service