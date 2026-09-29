"""
Office DMS - Configuration Loader
Loads and merges .env and config.yaml into a unified settings object.
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from loguru import logger

# Load .env file if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Import config validator
try:
    from .config_validator import validate_config
    CONFIG_VALIDATOR_AVAILABLE = True
except ImportError:
    logger.warning("config_validator not available - skipping validation")
    CONFIG_VALIDATOR_AVAILABLE = False


@dataclass
class SupplierConfig:
    name: str
    aliases: List[str]
    folder: str
    contact_email: Optional[str] = None


@dataclass
class KeywordConfig:
    keywords: List[str]
    category: str
    confidence_boost: float = 0.0
    sensitive: bool = False


@dataclass
class ThresholdConfig:
    unknown: float = 0.4
    review: float = 0.7
    approved: float = 0.85


@dataclass
class OCRConfig:
    tesseract_cmd: str = "tesseract"
    myanmar_lang: str = "mya"
    eng_lang: str = "eng"
    preprocessing: bool = True
    dpi: int = 300
    oem: int = 3
    psm: int = 6


@dataclass
class DuplicateConfig:
    similarity_threshold: float = 0.85
    near_duplicate_threshold: float = 0.75
    recent_docs_limit: int = 500
    hash_algorithm: str = "sha256"
    min_text_length: int = 50


@dataclass
class SOPStepConfig:
    name: str
    description: Optional[str]
    required_doc_types: List[str]
    duration_days: int
    order: int


@dataclass
class SOPTemplateConfig:
    name: str
    description: Optional[str]
    document_types: List[str]
    steps: List[SOPStepConfig]


class Settings:
    """Unified application settings from .env and config.yaml."""

    def __init__(self):
        self._validate_config_yaml()  # Validate config.yaml structure
        self._load_env()
        self._load_yaml()
        self._validate()

    def _validate_config_yaml(self):
        """Validate config.yaml structure using Pydantic validator."""
        if CONFIG_VALIDATOR_AVAILABLE:
            try:
                config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
                validate_config(config_path)
            except SystemExit:
                # Validator will exit on error, but we catch it to provide cleaner error
                raise
            except Exception as e:
                logger.warning(f"Config validation warning: {e}")
        else:
            logger.warning("Config validation skipped - validator not available")

    def _load_env(self):
        """Load configuration from environment variables."""
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "False" if os.getenv("ENVIRONMENT", "development") == "production" else "True").lower() == "true"
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

        # Database
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL", "sqlite:///./Office_DMS/database/dms.db"
        )
        self.DATABASE_URL = self.DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg2://"
        ) if self.DATABASE_URL.startswith("postgresql://") else self.DATABASE_URL

        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # MinIO
        self.MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
        self.MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "logistics-documents")

        # Paths
        base_path = Path(__file__).resolve().parent.parent.parent
        # Personal/local safety model: the original source is read-only; all write operations
        # are expected to stay inside the working workspace. The future D: drive scanner will
        # copy the source into SOURCE_ROOT/WORKING_ROOT before any organization step.
        self.SOURCE_ROOT = Path(os.getenv("SOURCE_ROOT", "")) if os.getenv("SOURCE_ROOT") else None
        self.WORKING_ROOT = Path(os.getenv("WORKING_ROOT", str(base_path / "Office_DMS" / "Workspace")))
        self.FINAL_ROOT = Path(os.getenv("FINAL_ROOT", str(self.WORKING_ROOT / "Final")))
        self.QUARANTINE_ROOT = Path(os.getenv("QUARANTINE_ROOT", str(self.WORKING_ROOT / "Quarantine")))
        self.BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT", str(base_path / "Office_DMS" / "Backups")))
        self.ORIGINAL_READ_ONLY = os.getenv("ORIGINAL_READ_ONLY", "true").lower() == "true"
        self.ALLOW_SOURCE_WRITE = os.getenv("ALLOW_SOURCE_WRITE", "false").lower() == "true"

        # Backward-compatible aliases used by existing services.
        self.WATCH_FOLDER = Path(os.getenv("WATCH_FOLDER", str(self.WORKING_ROOT / "Watch_Folder")))
        self.PROCESSING_WORKSPACE = Path(os.getenv("PROCESSING_WORKSPACE", str(self.WORKING_ROOT / "Processing_Workspace")))
        self.ORGANIZED_ROOT = Path(os.getenv("ORGANIZED_ROOT", str(self.FINAL_ROOT)))
        self.DUPLICATE_FOLDER = Path(os.getenv("DUPLICATE_FOLDER", str(self.WORKING_ROOT / "Duplicates")))
        self.SUSPICIOUS_FOLDER = Path(os.getenv("SUSPICIOUS_FOLDER", str(self.QUARANTINE_ROOT / "Suspicious")))
        self.LOG_DIR = Path(os.getenv("LOG_DIR", str(base_path / "logs")))

        # Social Media Watch Paths (Optional overrides)
        self.VIBER_WATCH_PATH = os.getenv("VIBER_WATCH_PATH", None)
        self.WHATSAPP_WATCH_PATH = os.getenv("WHATSAPP_WATCH_PATH", None)
        self.FACEBOOK_WATCH_PATH = os.getenv("FACEBOOK_WATCH_PATH", None)
        self.TELEGRAM_WATCH_PATH = os.getenv("TELEGRAM_WATCH_PATH", None)
        self.SOCIAL_MEDIA_BASE_FOLDER = Path(os.getenv("SOCIAL_MEDIA_BASE_FOLDER", str(base_path / "Office_DMS" / "Organized" / "Social_Media")))

        # OCR
        self.TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")
        self.MYANMAR_LANG = os.getenv("MYANMAR_LANG", "mya")
        self.OCR_DPI = int(os.getenv("OCR_DPI", "300"))
        self.OCR_PREPROCESSING = os.getenv("OCR_PREPROCESSING", "true").lower() == "true"

        # Security
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self.MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))

        # Monitoring
        self.SENTRY_DSN = os.getenv("SENTRY_DSN", "")

        # Backup
        self.BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

        # SMTP Email Configuration (Enterprise Feature)
        self.SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@enterprise-dms.local")
        self.SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Enterprise DMS")
        self.ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@enterprise-dms.local")
        # Optional one-time bootstrap. Never ship a usable default password.
        self.BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")

        # AI Services Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
        self.HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
        self.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
        self.AI_ENHANCED_DUPLICATE_DETECTION = os.getenv("AI_ENHANCED_DUPLICATE_DETECTION", "false").lower() == "true"
        self.AI_CLASSIFICATION_ENABLED = os.getenv("AI_CLASSIFICATION_ENABLED", "false").lower() == "true"
        self.AI_PROVIDER_ORDER = [
            p.strip().lower() for p in os.getenv(
                "AI_PROVIDER_ORDER", "gemini,openrouter,groq,openai"
            ).split(",") if p.strip()
        ]
        self.AI_PROVIDER_MAX_ATTEMPTS = int(os.getenv("AI_PROVIDER_MAX_ATTEMPTS", "0"))
        self.AI_PROVIDER_TIMEOUT_SECONDS = float(os.getenv("AI_PROVIDER_TIMEOUT_SECONDS", "30"))

        # Railway-specific settings
        self.MINIO_ENABLED = os.getenv("MINIO_ENABLED", "false").lower() == "true"
        self.STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # "minio" or "local"
        self.RAILWAY_ENABLE_WORKER = os.getenv("RAILWAY_ENABLE_WORKER", "false").lower() == "true"

    def _load_yaml(self):
        """Load configuration from config.yaml."""
        config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"

        default_config = {
            "watch_sources": [],
            "social_media": {
                "base_folder": "Organized/Social_Media",
                "date_format": "%Y-%m-%d",
                "naming_template": "{date}_{source}_{category}_{original_name}",
                "create_daily_folders": True,
            },
            "suppliers": [],
            "keyword_mapping": {},
            "folder_mapping": {},
            "patterns": {},
            "thresholds": {"unknown": 0.4, "review": 0.7, "approved": 0.85},
            "ocr": {
                "tesseract_cmd": self.TESSERACT_CMD,
                "myanmar_lang": self.MYANMAR_LANG,
                "eng_lang": "eng",
                "preprocessing": self.OCR_PREPROCESSING,
                "dpi": self.OCR_DPI,
                "oem": 3,
                "psm": 6,
            },
            "duplicate": {
                "similarity_threshold": 0.85,
                "near_duplicate_threshold": 0.75,
                "recent_docs_limit": 500,
                "hash_algorithm": "sha256",
                "min_text_length": 50,
            },
            "sop_defaults": {},
            "notifications": {
                "eta_warning_days": 3,
                "overdue_alert_days": 1,
                "reminder_check_interval_hours": 6,
            },
            "cleanup": {
                "processing_workspace_max_age_hours": 24,
                "log_retention_days": 90,
                "audit_log_retention_days": 2555,
                "backup_retention_days": 30,
            },
        }

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        default_config.update(yaml_config)
            except Exception as e:
                logger.warning(f"Failed to load config.yaml: {e}. Using defaults.")

        self.yaml_config = default_config

        # Parse suppliers
        self.suppliers: List[SupplierConfig] = []
        for sup in self.yaml_config.get("suppliers", []):
            self.suppliers.append(SupplierConfig(
                name=sup["name"],
                aliases=sup.get("aliases", []),
                folder=sup.get("folder", "Other"),
                contact_email=sup.get("contact_email"),
            ))

        # Parse keyword mapping
        self.keyword_mapping: Dict[str, KeywordConfig] = {}
        for key, val in self.yaml_config.get("keyword_mapping", {}).items():
            self.keyword_mapping[key] = KeywordConfig(
                keywords=val.get("keywords", []),
                category=val.get("category", "Other"),
                confidence_boost=val.get("confidence_boost", 0.0),
                sensitive=val.get("sensitive", False),
            )

        # Folder mapping
        self.folder_mapping: Dict[str, str] = self.yaml_config.get("folder_mapping", {})

        # Regex patterns
        self.patterns: Dict[str, str] = self.yaml_config.get("patterns", {})

        # Thresholds
        t = self.yaml_config.get("thresholds", {})
        self.thresholds = ThresholdConfig(
            unknown=t.get("unknown", 0.4),
            review=t.get("review", 0.7),
            approved=t.get("approved", 0.85),
        )

        # OCR config
        o = self.yaml_config.get("ocr", {})
        self.ocr = OCRConfig(
            tesseract_cmd=o.get("tesseract_cmd", self.TESSERACT_CMD),
            myanmar_lang=o.get("myanmar_lang", self.MYANMAR_LANG),
            eng_lang=o.get("eng_lang", "eng"),
            preprocessing=o.get("preprocessing", True),
            dpi=o.get("dpi", 300),
            oem=o.get("oem", 3),
            psm=o.get("psm", 6),
        )

        # Duplicate config
        d = self.yaml_config.get("duplicate", {})
        self.duplicate = DuplicateConfig(
            similarity_threshold=d.get("similarity_threshold", 0.85),
            near_duplicate_threshold=d.get("near_duplicate_threshold", 0.75),
            recent_docs_limit=d.get("recent_docs_limit", 500),
            hash_algorithm=d.get("hash_algorithm", "sha256"),
            min_text_length=d.get("min_text_length", 50),
        )

        # SOP templates
        self.sop_defaults: Dict[str, SOPTemplateConfig] = {}
        for key, val in self.yaml_config.get("sop_defaults", {}).items():
            steps = []
            for s in val.get("steps", []):
                steps.append(SOPStepConfig(
                    name=s["name"],
                    description=s.get("description"),
                    required_doc_types=s.get("required_doc_types", []),
                    duration_days=s.get("duration_days", 1),
                    order=s.get("order", 1),
                ))
            self.sop_defaults[key] = SOPTemplateConfig(
                name=val["name"],
                description=val.get("description"),
                document_types=val.get("document_types", []),
                steps=steps,
            )

        # Notifications
        self.notifications = self.yaml_config.get("notifications", {})

        # Cleanup
        self.cleanup = self.yaml_config.get("cleanup", {})

    def _validate(self):
        """Validate critical configuration."""
        if not self.ENCRYPTION_KEY and self.ENVIRONMENT == "production":
            logger.warning("ENCRYPTION_KEY not set in production. Sensitive documents will NOT be encrypted.")

        if self.SECRET_KEY == "dev-secret-key-change-in-production" and self.ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY must be changed before starting in production.")
        if self.BOOTSTRAP_ADMIN_PASSWORD and len(self.BOOTSTRAP_ADMIN_PASSWORD) < 12:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters.")

        # Validate storage configuration
        if self.STORAGE_TYPE == "local" and not self.MINIO_ENABLED:
            logger.info("Using local storage (MinIO disabled)")

        # Personal mode safety boundary: SOURCE_ROOT is always treated as read-only,
        # and every writable organization/quarantine path must stay inside WORKING_ROOT.
        if self.SOURCE_ROOT:
            source = self.SOURCE_ROOT.resolve()
            working = self.WORKING_ROOT.resolve()
            try:
                overlap = source == working or working.is_relative_to(source) or source.is_relative_to(working)
            except AttributeError:
                overlap = source == working or str(working).startswith(str(source) + os.sep) or str(source).startswith(str(working) + os.sep)
            if overlap:
                raise ValueError(f"Unsafe workspace configuration: SOURCE_ROOT ({source}) and WORKING_ROOT ({working}) overlap.")
            if self.ALLOW_SOURCE_WRITE:
                raise ValueError("Unsafe workspace configuration: ALLOW_SOURCE_WRITE must remain false in personal local mode.")
        working = self.WORKING_ROOT.resolve()
        backup = self.BACKUP_ROOT.resolve()
        if backup == working or backup.is_relative_to(working):
            raise ValueError(f"Unsafe workspace configuration: BACKUP_ROOT ({backup}) must not be inside WORKING_ROOT ({working}).")
        if self.SOURCE_ROOT:
            source = self.SOURCE_ROOT.resolve()
            if backup == source or backup.is_relative_to(source):
                raise ValueError(f"Unsafe workspace configuration: BACKUP_ROOT ({backup}) must not be inside SOURCE_ROOT ({source}).")
        for writable_root in (self.FINAL_ROOT, self.QUARANTINE_ROOT):
            try:
                inside = writable_root.resolve().is_relative_to(working)
            except AttributeError:
                inside = str(writable_root.resolve()).startswith(str(working) + os.sep)
            if not inside:
                raise ValueError(f"Unsafe workspace configuration: {writable_root} must be inside WORKING_ROOT ({working}).")

        # Ensure directories exist
        for path_attr in ["WATCH_FOLDER", "PROCESSING_WORKSPACE", "ORGANIZED_ROOT",
                         "DUPLICATE_FOLDER", "SUSPICIOUS_FOLDER", "LOG_DIR"]:
            path = getattr(self, path_attr)
            path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Configuration loaded: environment={self.ENVIRONMENT}, db={self.DATABASE_URL.split('@')[-1] if '@' in self.DATABASE_URL else 'sqlite'}, storage={self.STORAGE_TYPE}")

    def get_supplier_by_alias(self, text: str) -> Optional[SupplierConfig]:
        """Find supplier by matching aliases in text."""
        text_lower = text.lower()
        for supplier in self.suppliers:
            for alias in supplier.aliases:
                if alias.lower() in text_lower:
                    return supplier
        return None

    def get_category_keywords(self) -> Dict[str, List[str]]:
        """Get mapping of category -> keywords."""
        result: Dict[str, List[str]] = {}
        for key, config in self.keyword_mapping.items():
            cat = config.category
            if cat not in result:
                result[cat] = []
            result[cat].extend(config.keywords)
        return result

    def is_sensitive_category(self, category: str) -> bool:
        """Check if a document category requires encryption."""
        for key, config in self.keyword_mapping.items():
            if config.category == category and config.sensitive:
                return True
        return category in ["NRC", "Invoices", "Government"]

    def to_dict(self) -> Dict[str, Any]:
        """Export settings as dictionary (for health checks, debugging)."""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "database_type": "postgresql" if "postgresql" in self.DATABASE_URL else "sqlite",
            "minio_endpoint": self.MINIO_ENDPOINT,
            "minio_bucket": self.MINIO_BUCKET_NAME,
            "suppliers_count": len(self.suppliers),
            "keyword_mappings": list(self.keyword_mapping.keys()),
            "thresholds": {
                "unknown": self.thresholds.unknown,
                "review": self.thresholds.review,
                "approved": self.thresholds.approved,
            },
            "sop_templates": list(self.sop_defaults.keys()),
        }


# Singleton instance
settings = Settings()
