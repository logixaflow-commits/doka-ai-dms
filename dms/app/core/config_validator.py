"""
Configuration Validator for Enterprise AI DMS
Validates config.yaml structure using Pydantic models.
Provides graceful error handling and default config generation.
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from loguru import logger


class SupplierConfigModel(BaseModel):
    """Supplier configuration model."""
    name: str = Field(..., min_length=1, description="Supplier name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    folder: str = Field(default="Other", description="Target folder")
    contact_email: Optional[str] = Field(None, description="Contact email")


class KeywordConfigModel(BaseModel):
    """Keyword mapping configuration model."""
    keywords: List[str] = Field(..., min_items=1, description="Keywords for this category")
    category: str = Field(..., min_length=1, description="Document category")
    confidence_boost: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence boost")
    sensitive: bool = Field(default=False, description="Mark as sensitive")


class ThresholdConfigModel(BaseModel):
    """Classification threshold configuration model."""
    unknown: float = Field(default=0.4, ge=0.0, le=1.0, description="Unknown threshold")
    review: float = Field(default=0.7, ge=0.0, le=1.0, description="Review threshold")
    approved: float = Field(default=0.85, ge=0.0, le=1.0, description="Approved threshold")

    @validator('review')
    def review_must_be_greater_than_unknown(cls, v, values):
        if 'unknown' in values and v <= values['unknown']:
            raise ValueError('review threshold must be greater than unknown threshold')
        return v

    @validator('approved')
    def approved_must_be_greater_than_review(cls, v, values):
        if 'review' in values and v <= values['review']:
            raise ValueError('approved threshold must be greater than review threshold')
        return v


class OCRConfigModel(BaseModel):
    """OCR configuration model."""
    tesseract_cmd: str = Field(default="tesseract", description="Tesseract command")
    myanmar_lang: str = Field(default="mya", description="Myanmar language code")
    eng_lang: str = Field(default="eng", description="English language code")
    preprocessing: bool = Field(default=True, description="Enable preprocessing")
    dpi: int = Field(default=300, ge=100, le=600, description="DPI for OCR")
    oem: int = Field(default=3, ge=0, le=3, description="OCR Engine Mode")
    psm: int = Field(default=6, ge=0, le=13, description="Page Segmentation Mode")
    fallback_enabled: bool = Field(default=True, description="Enable OCR fallback")
    timeout: int = Field(default=30, ge=5, le=120, description="OCR timeout in seconds")


class DuplicateConfigModel(BaseModel):
    """Duplicate detection configuration model."""
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Similarity threshold")
    near_duplicate_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Near duplicate threshold")
    recent_docs_limit: int = Field(default=500, ge=10, le=10000, description="Recent documents limit")
    hash_algorithm: str = Field(default="sha256", description="Hash algorithm")
    min_text_length: int = Field(default=50, ge=10, le=1000, description="Minimum text length")


class SOPStepConfigModel(BaseModel):
    """SOP step configuration model."""
    name: str = Field(..., min_length=1, description="Step name")
    description: Optional[str] = Field(None, description="Step description")
    required_doc_types: List[str] = Field(default_factory=list, description="Required document types")
    duration_days: int = Field(default=1, ge=1, le=365, description="Duration in days")
    order: int = Field(default=1, ge=1, description="Step order")


class SOPTemplateConfigModel(BaseModel):
    """SOP template configuration model."""
    name: str = Field(..., min_length=1, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    document_types: List[str] = Field(default_factory=list, description="Applicable document types")
    steps: List[SOPStepConfigModel] = Field(default_factory=list, description="Workflow steps")


class NotificationConfigModel(BaseModel):
    """Notification configuration model."""
    eta_warning_days: int = Field(default=3, ge=1, le=30, description="ETA warning days")
    overdue_alert_days: int = Field(default=1, ge=1, le=30, description="Overdue alert days")
    reminder_check_interval_hours: int = Field(default=6, ge=1, le=24, description="Reminder check interval")


class CleanupConfigModel(BaseModel):
    """Cleanup configuration model."""
    processing_workspace_max_age_hours: int = Field(default=24, ge=1, le=168, description="Processing workspace max age")
    log_retention_days: int = Field(default=90, ge=7, le=365, description="Log retention days")
    audit_log_retention_days: int = Field(default=2555, ge=30, le=3650, description="Audit log retention")
    backup_retention_days: int = Field(default=30, ge=7, le=365, description="Backup retention")


class SocialMediaConfigModel(BaseModel):
    """Social media configuration model."""
    base_folder: str = Field(default="Organized/Social_Media", description="Base folder")
    date_format: str = Field(default="%Y-%m-%d", description="Date format")
    naming_template: str = Field(default="{date}_{source}_{category}_{original_name}", description="Naming template")
    create_daily_folders: bool = Field(default=True, description="Create daily folders")


class Phase2ConfigModel(BaseModel):
    """Phase 2 configuration model."""
    folder_permissions_enabled: bool = Field(default=True, description="Enable folder permissions")
    admin_all_folders_access: bool = Field(default=True, description="Admin has all folder access")
    report_retention_days: int = Field(default=30, ge=7, le=365, description="Report retention days")
    report_sync_max_records: int = Field(default=10000, ge=1000, le=100000, description="Max sync report records")
    scheduled_reports_enabled: bool = Field(default=True, description="Enable scheduled reports")
    daily_report_time: str = Field(default="09:00", description="Daily report time")
    weekly_report_day: str = Field(default="Monday", description="Weekly report day")
    weekly_report_time: str = Field(default="08:00", description="Weekly report time")


class Phase3ConfigModel(BaseModel):
    """Phase 3 configuration model."""
    ai_tagging_enabled: bool = Field(default=False, description="Enable AI tagging")
    vector_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Vector embedding model")
    vector_cache_enabled: bool = Field(default=True, description="Enable vector search caching")
    vector_cache_ttl: int = Field(default=3600, ge=60, le=86400, description="Vector cache TTL in seconds")
    rule_engine_batch_size: int = Field(default=100, ge=10, le=1000, description="Rule engine batch size")
    rule_engine_timeout: int = Field(default=30, ge=5, le=300, description="Rule engine timeout in seconds")


class Phase4ConfigModel(BaseModel):
    """Phase 4 configuration model."""
    document_versioning_enabled: bool = Field(default=True, description="Enable document versioning")
    max_document_versions: int = Field(default=10, ge=1, le=100, description="Max versions per document")
    pwa_enabled: bool = Field(default=True, description="Enable PWA features")
    pwa_app_name: str = Field(default="Enterprise DMS", description="PWA app name")
    pwa_short_name: str = Field(default="DMS", description="PWA short name")
    pwa_theme_color: str = Field(default="#1a73e8", description="PWA theme color")
    customs_api_url: Optional[str] = Field(None, description="Customs API URL")
    customs_api_key: Optional[str] = Field(None, description="Customs API key")
    shipping_api_url: Optional[str] = Field(None, description="Shipping API URL")
    shipping_api_key: Optional[str] = Field(None, description="Shipping API key")


class ConfigYamlModel(BaseModel):
    """Main config.yaml model."""
    watch_sources: List[str] = Field(default_factory=list, description="Watch source paths")
    social_media: SocialMediaConfigModel = Field(default_factory=SocialMediaConfigModel, description="Social media config")
    suppliers: List[SupplierConfigModel] = Field(default_factory=list, description="Supplier configurations")
    keyword_mapping: Dict[str, KeywordConfigModel] = Field(default_factory=dict, description="Keyword mappings")
    folder_mapping: Dict[str, str] = Field(default_factory=dict, description="Folder mappings")
    patterns: Dict[str, str] = Field(default_factory=dict, description="Regex patterns")
    thresholds: ThresholdConfigModel = Field(default_factory=ThresholdConfigModel, description="Classification thresholds")
    ocr: OCRConfigModel = Field(default_factory=OCRConfigModel, description="OCR configuration")
    duplicate: DuplicateConfigModel = Field(default_factory=DuplicateConfigModel, description="Duplicate detection")
    sop_defaults: Dict[str, SOPTemplateConfigModel] = Field(default_factory=dict, description="SOP templates")
    notifications: NotificationConfigModel = Field(default_factory=NotificationConfigModel, description="Notifications")
    cleanup: CleanupConfigModel = Field(default_factory=CleanupConfigModel, description="Cleanup settings")
    phase2: Phase2ConfigModel = Field(default_factory=Phase2ConfigModel, description="Phase 2 configuration")
    phase3: Phase3ConfigModel = Field(default_factory=Phase3ConfigModel, description="Phase 3 configuration")
    phase4: Phase4ConfigModel = Field(default_factory=Phase4ConfigModel, description="Phase 4 configuration")


class ConfigValidator:
    """Configuration validator with error handling and default generation."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> bool:
        """Validate config.yaml and return True if valid."""
        try:
            if not self.config_path.exists():
                self.warnings.append(f"Config file not found: {self.config_path}")
                return self._generate_default_config()
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            
            if config_data is None:
                self.warnings.append("Config file is empty")
                return self._generate_default_config()
            
            # Validate using Pydantic
            validated_config = ConfigYamlModel(**config_data)
            
            logger.info("✓ Configuration validation passed")
            return True
            
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            logger.error(f"Config YAML error: {e}")
            return False
        except ValueError as e:
            self.errors.append(f"Validation error: {e}")
            logger.error(f"Config validation error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error: {e}")
            logger.error(f"Unexpected config error: {e}")
            return False
    
    def _generate_default_config(self) -> bool:
        """Generate default config.yaml file."""
        try:
            default_config = ConfigYamlModel().dict()
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"✓ Generated default config at: {self.config_path}")
            return True
        except Exception as e:
            self.errors.append(f"Failed to generate default config: {e}")
            logger.error(f"Failed to generate default config: {e}")
            return False
    
    def get_error_report(self) -> str:
        """Get detailed error report."""
        report = []
        if self.warnings:
            report.append("Warnings:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        if self.errors:
            report.append("Errors:")
            for error in self.errors:
                report.append(f"  - {error}")
        return "\n".join(report)
    
    def exit_on_error(self):
        """Exit with error message if validation failed."""
        if not self.validate():
            error_report = self.get_error_report()
            logger.error("=" * 60)
            logger.error("CONFIGURATION VALIDATION FAILED")
            logger.error("=" * 60)
            logger.error(error_report)
            logger.error("=" * 60)
            logger.error("Please fix the configuration errors and restart the application.")
            logger.error("For help, see: .env.example and default config.yaml structure")
            logger.error("=" * 60)
            raise SystemExit(1)


def validate_config(config_path: Optional[Path] = None, skip_validation: bool = False) -> ConfigYamlModel:
    """
    Validate config.yaml and return validated model.
    Exits with error if validation fails.
    
    Args:
        config_path: Path to config.yaml file
        skip_validation: If True, skip validation (for testing)
    """
    import os
    
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    
    # Skip validation if environment variable is set (for testing)
    if os.getenv('SKIP_CONFIG_VALIDATION') == 'true' or skip_validation:
        # Load and return config without validation
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return ConfigYamlModel(**config_data)
    
    validator = ConfigValidator(config_path)
    validator.exit_on_error()
    
    # Load and return validated config
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    return ConfigYamlModel(**config_data)
