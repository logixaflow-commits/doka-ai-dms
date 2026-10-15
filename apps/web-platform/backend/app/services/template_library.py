"""
Template Library Service - Pre-built SOP template management
"""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
import yaml

from sqlalchemy.orm import Session
from app.core.config import settings


class TemplateLibraryService:
    """Service for managing pre-built SOP templates."""

    def __init__(self):
        self.templates: Dict[str, Dict] = {}
        self._load_templates_from_config()

    def _load_templates_from_config(self):
        """Load templates from config.yaml."""
        try:
            # Try to load from config.yaml
            config_path = settings.CONFIG_FILE if hasattr(settings, 'CONFIG_FILE') else None
            
            if config_path:
                import os
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    if config_data and 'template_library' in config_data:
                        self.templates = config_data['template_library']
                        logger.info(f"Loaded {len(self.templates)} template categories from config")
                        return

            # Use default templates if config not available
            self._load_default_templates()
            
        except Exception as e:
            logger.warning(f"Failed to load templates from config: {e}")
            self._load_default_templates()

    def _load_default_templates(self):
        """Load default templates."""
        self.templates = {
            'import': [
                {
                    'id': 'import_process_standard',
                    'name': 'Import Process - Standard',
                    'description': 'Standard operating procedure for import shipments',
                    'icon': '📦',
                    'steps': self._get_standard_import_steps()
                },
                {
                    'id': 'import_process_express',
                    'name': 'Import Process - Express',
                    'description': 'Express import for urgent shipments',
                    'icon': '🚀',
                    'steps': self._get_express_import_steps()
                }
            ],
            'export': [
                {
                    'id': 'export_process_standard',
                    'name': 'Export Process - Standard',
                    'description': 'Standard operating procedure for export shipments',
                    'icon': '✈️',
                    'steps': self._get_standard_export_steps()
                }
            ],
            'customs': [
                {
                    'id': 'customs_clearance_standard',
                    'name': 'Customs Clearance - Standard',
                    'description': 'Standard customs clearance procedure',
                    'icon': '🛃',
                    'steps': self._get_customs_steps()
                }
            ],
            'compliance': [
                {
                    'id': 'fda_approval_process',
                    'name': 'FDA Approval Process',
                    'description': 'Food and Drug Administration approval workflow',
                    'icon': '💊',
                    'steps': self._get_fda_steps()
                },
                {
                    'id': 'nrc_verification_process',
                    'name': 'NRC Verification Process',
                    'description': 'National Registration Card verification workflow',
                    'icon': '🪪',
                    'steps': self._get_nrc_steps()
                }
            ]
        }
        logger.info(f"Loaded {sum(len(v) for v in self.templates.values())} default templates")

    def _get_standard_import_steps(self):
        """Standard import process steps."""
        return [
            {'name': 'Import License', 'required_doc_types': ['Licenses', 'Permits'], 'duration_days': 7, 'order': 1, 'assignee_role': 'customs_agent'},
            {'name': 'FDA Approval', 'required_doc_types': ['FDA'], 'duration_days': 10, 'order': 2, 'assignee_role': 'compliance_team'},
            {'name': 'Shipping Documentation', 'required_doc_types': ['BL', 'Invoices'], 'duration_days': 14, 'order': 3, 'assignee_role': 'shipping_agent'},
            {'name': 'Customs Clearance', 'required_doc_types': ['Invoices', 'BL', 'Customs_Declaration'], 'duration_days': 5, 'order': 4, 'assignee_role': 'customs_agent'},
            {'name': 'Delivery Confirmation', 'required_doc_types': ['Delivery_Note'], 'duration_days': 3, 'order': 5, 'assignee_role': 'warehouse_team'}
        ]

    def _get_express_import_steps(self):
        """Express import process steps."""
        return [
            {'name': 'Expedited License Processing', 'required_doc_types': ['Licenses'], 'duration_days': 2, 'order': 1, 'assignee_role': 'customs_agent'},
            {'name': 'Priority FDA Review', 'required_doc_types': ['FDA'], 'duration_days': 3, 'order': 2, 'assignee_role': 'compliance_team'},
            {'name': 'Express Shipping', 'required_doc_types': ['BL', 'Invoices'], 'duration_days': 5, 'order': 3, 'assignee_role': 'shipping_agent'},
            {'name': 'Fast-Track Customs', 'required_doc_types': ['Invoices', 'BL'], 'duration_days': 2, 'order': 4, 'assignee_role': 'customs_agent'},
            {'name': 'Priority Delivery', 'required_doc_types': ['Delivery_Note'], 'duration_days': 1, 'order': 5, 'assignee_role': 'warehouse_team'}
        ]

    def _get_standard_export_steps(self):
        """Standard export process steps."""
        return [
            {'name': 'Export License Application', 'required_doc_types': ['Licenses'], 'duration_days': 5, 'order': 1, 'assignee_role': 'customs_agent'},
            {'name': 'Consular Documentation', 'required_doc_types': ['Certificates'], 'duration_days': 7, 'order': 2, 'assignee_role': 'export_agent'},
            {'name': 'Export Declaration', 'required_doc_types': ['Invoices', 'BL'], 'duration_days': 3, 'order': 3, 'assignee_role': 'customs_agent'},
            {'name': 'Port Clearance', 'required_doc_types': ['Customs_Declaration'], 'duration_days': 2, 'order': 4, 'assignee_role': 'customs_agent'},
            {'name': 'Shipping Confirmation', 'required_doc_types': ['Bill of Lading'], 'duration_days': 1, 'order': 5, 'assignee_role': 'shipping_agent'}
        ]

    def _get_customs_steps(self):
        """Customs clearance process steps."""
        return [
            {'name': 'Document Verification', 'required_doc_types': ['Invoices', 'BL'], 'duration_days': 2, 'order': 1, 'assignee_role': 'customs_agent'},
            {'name': 'Classification', 'required_doc_types': [], 'duration_days': 1, 'order': 2, 'assignee_role': 'customs_agent'},
            {'name': 'Duty Assessment', 'required_doc_types': ['Invoices'], 'duration_days': 2, 'order': 3, 'assignee_role': 'customs_agent'},
            {'name': 'Inspection', 'required_doc_types': [], 'duration_days': 3, 'order': 4, 'assignee_role': 'customs_inspector'},
            {'name': 'Release', 'required_doc_types': [], 'duration_days': 1, 'order': 5, 'assignee_role': 'customs_agent'}
        ]

    def _get_fda_steps(self):
        """FDA approval process steps."""
        return [
            {'name': 'Application Submission', 'required_doc_types': ['FDA_Application'], 'duration_days': 3, 'order': 1, 'assignee_role': 'compliance_team'},
            {'name': 'Document Review', 'required_doc_types': ['Invoices', 'Product_Info'], 'duration_days': 7, 'order': 2, 'assignee_role': 'fda_officer'},
            {'name': 'Inspection', 'required_doc_types': [], 'duration_days': 5, 'order': 3, 'assignee_role': 'fda_inspector'},
            {'name': 'Approval Decision', 'required_doc_types': [], 'duration_days': 3, 'order': 4, 'assignee_role': 'fda_supervisor'},
            {'name': 'Certificate Issuance', 'required_doc_types': [], 'duration_days': 2, 'order': 5, 'assignee_role': 'compliance_team'}
        ]

    def _get_nrc_steps(self):
        """NRC verification process steps."""
        return [
            {'name': 'NRC Submission', 'required_doc_types': ['NRC'], 'duration_days': 1, 'order': 1, 'assignee_role': 'clerk'},
            {'name': 'Identity Verification', 'required_doc_types': ['NRC', 'Photo_ID'], 'duration_days': 3, 'order': 2, 'assignee_role': 'verification_officer'},
            {'name': 'Database Check', 'required_doc_types': [], 'duration_days': 2, 'order': 3, 'assignee_role': 'system_admin'},
            {'name': 'Approval', 'required_doc_types': [], 'duration_days': 2, 'order': 4, 'assignee_role': 'supervisor'},
            {'name': 'Certificate Generation', 'required_doc_types': [], 'duration_days': 1, 'order': 5, 'assignee_role': 'clerk'}
        ]

    def get_categories(self) -> List[str]:
        """Get all template categories."""
        return list(self.templates.keys())

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """Get all templates in a category."""
        return self.templates.get(category, [])

    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get a specific template by ID."""
        for category, templates in self.templates.items():
            for template in templates:
                if template.get('id') == template_id:
                    return template
        return None

    def export_template(self, template_id: str) -> Optional[str]:
        """Export template as YAML string."""
        template = self.get_template(template_id)
        if not template:
            return None
        return yaml.dump(template, default_flow_style=False)

    def import_template(self, yaml_data: str, category: str) -> Optional[Dict]:
        """Import template from YAML."""
        try:
            template = yaml.safe_load(yaml_data)
            if not template or not isinstance(template, dict):
                return None

            if category not in self.templates:
                self.templates[category] = []

            # Generate ID if not present
            if 'id' not in template:
                template['id'] = f"custom_{len(self.templates[category]) + 1}"

            self.templates[category].append(template)
            logger.info(f"Imported template: {template.get('name', 'Unknown')}")
            return template

        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return None

    def instantiate_template(self, template_id: str, document_id: int, db: Session) -> Optional[int]:
        """Create SOP instance from template."""
        template = self.get_template(template_id)
        if not template:
            return None

        # In production, this would create an SOP record in the database
        # For now, return the template ID
        return template.get('id')


# Global template library service instance
template_library_service = TemplateLibraryService()