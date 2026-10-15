"""
Rule Engine Service - IF-THEN rule evaluation and execution
Evaluates conditions and executes actions for workflow automation.
"""
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from datetime import datetime, timedelta
import re
import time
import os


class RuleCondition:
    """Represents a rule condition (IF part)."""

    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator  # eq, ne, gt, gte, lt, lte, contains, in, regex
        self.value = value

    def evaluate(self, data: Dict) -> bool:
        """
        Evaluate condition against data.
        
        Args:
            data: Document or event data
            
        Returns:
            True if condition is met
        """
        try:
            # Get field value from data (support nested fields with dot notation)
            field_value = self._get_field_value(data, self.field)
            
            if field_value is None:
                return False

            # Evaluate based on operator
            if self.operator == 'eq':
                return field_value == self.value
            elif self.operator == 'ne':
                return field_value != self.value
            elif self.operator == 'gt':
                return float(field_value) > float(self.value)
            elif self.operator == 'gte':
                return float(field_value) >= float(self.value)
            elif self.operator == 'lt':
                return float(field_value) < float(self.value)
            elif self.operator == 'lte':
                return float(field_value) <= float(self.value)
            elif self.operator == 'contains':
                return str(self.value).lower() in str(field_value).lower()
            elif self.operator == 'in':
                return field_value in self.value if isinstance(self.value, (list, tuple)) else False
            elif self.operator == 'regex':
                return bool(re.search(self.value, str(field_value), re.IGNORECASE))
            else:
                logger.warning(f"Unknown operator: {self.operator}")
                return False

        except Exception as e:
            logger.error(f"Failed to evaluate condition {self.field} {self.operator} {self.value}: {e}")
            return False

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get field value from data (supports nested fields)."""
        if '.' not in field:
            return data.get(field)
        
        keys = field.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class RuleAction:
    """Represents a rule action (THEN part)."""

    def __init__(self, action_type: str, parameters: Dict):
        self.action_type = action_type  # assign_user, set_folder, send_email, set_tag, create_reminder
        self.parameters = parameters

    def execute(self, document: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Execute the action on a document.
        
        Args:
            document: Document data
            context: Additional context (user_id, etc.)
            
        Returns:
            Execution result
        """
        context = context or {}
        result = {'action_type': self.action_type, 'success': False, 'message': ''}

        try:
            if self.action_type == 'set_tag':
                result = self._execute_set_tag(document, context)
            elif self.action_type == 'set_folder':
                result = self._execute_set_folder(document, context)
            elif self.action_type == 'send_email':
                result = self._execute_send_email(document, context)
            elif self.action_type == 'create_reminder':
                result = self._execute_create_reminder(document, context)
            elif self.action_type == 'assign_user':
                result = self._execute_assign_user(document, context)
            elif self.action_type == 'set_urgency':
                result = self._execute_set_urgency(document, context)
            elif self.action_type == 'set_status':
                result = self._execute_set_status(document, context)
            else:
                result['message'] = f"Unknown action type: {self.action_type}"

        except Exception as e:
            result['message'] = f"Execution failed: {str(e)}"
            logger.error(f"Failed to execute action {self.action_type}: {e}")

        return result

    def _execute_set_tag(self, document: Dict, context: Dict) -> Dict:
        """Execute set_tag action."""
        tag = self.parameters.get('tag')
        if not tag:
            return {'success': False, 'message': 'Tag parameter required', 'action_type': 'set_tag'}
        
        # In production, this would update the database
        return {'success': True, 'message': f'Tag "{tag}" would be set', 'action_type': 'set_tag', 'tag': tag}

    def _execute_set_folder(self, document: Dict, context: Dict) -> Dict:
        """Execute set_folder action."""
        folder = self.parameters.get('target_folder')
        if not folder:
            return {'success': False, 'message': 'target_folder parameter required', 'action_type': 'set_folder'}
        
        return {'success': True, 'message': f'Folder would be set to "{folder}"', 'action_type': 'set_folder', 'folder': folder}

    def _execute_send_email(self, document: Dict, context: Dict) -> Dict:
        """Execute send_email action."""
        template = self.parameters.get('template')
        recipient = self.parameters.get('recipient')
        
        return {'success': True, 'message': f'Email would be sent using template "{template}"', 'action_type': 'send_email', 'template': template}

    def _execute_create_reminder(self, document: Dict, context: Dict) -> Dict:
        """Execute create_reminder action."""
        days = self.parameters.get('days', 7)
        message = self.parameters.get('message', 'Follow up required')
        
        due_date = datetime.utcnow() + timedelta(days=days)
        
        return {
            'success': True, 
            'message': f'Reminder created due {due_date}', 
            'action_type': 'create_reminder',
            'days': days,
            'due_date': due_date.isoformat()
        }

    def _execute_assign_user(self, document: Dict, context: Dict) -> Dict:
        """Execute assign_user action."""
        target_user = self.parameters.get('target_user')
        if not target_user:
            return {'success': False, 'message': 'target_user parameter required', 'action_type': 'assign_user'}
        
        return {'success': True, 'message': f'Document would be assigned to "{target_user}"', 'action_type': 'assign_user', 'target_user': target_user}

    def _execute_set_urgency(self, document: Dict, context: Dict) -> Dict:
        """Execute set_urgency action."""
        urgency = self.parameters.get('urgency', 'normal')
        
        return {'success': True, 'message': f'Urgency would be set to "{urgency}"', 'action_type': 'set_urgency', 'urgency': urgency}

    def _execute_set_status(self, document: Dict, context: Dict) -> Dict:
        """Execute set_status action."""
        status = self.parameters.get('status')
        if not status:
            return {'success': False, 'message': 'status parameter required', 'action_type': 'set_status'}
        
        return {'success': True, 'message': f'Status would be set to "{status}"', 'action_type': 'set_status', 'status': status}


class Rule:
    """Complete rule with conditions and actions."""

    def __init__(
        self,
        rule_id: int,
        name: str,
        conditions: List[Dict],
        actions: List[Dict],
        enabled: bool = True,
        priority: int = 0,
        logic: str = 'AND'
    ):
        self.rule_id = rule_id
        self.name = name
        self.conditions = [RuleCondition(**c) for c in conditions]
        self.actions = [RuleAction(**a) for a in actions]
        self.enabled = enabled
        self.priority = priority
        self.logic = logic  # AND or OR - how to combine conditions

    def evaluate(self, data: Dict) -> bool:
        """
        Evaluate rule conditions.
        
        Args:
            data: Document or event data
            
        Returns:
            True if all conditions are met (according to logic)
        """
        if not self.enabled or not self.conditions:
            return False

        results = [condition.evaluate(data) for condition in self.conditions]

        if self.logic == 'AND':
            return all(results)
        elif self.logic == 'OR':
            return any(results)
        else:
            return all(results)

    def execute(self, document: Dict, context: Optional[Dict] = None) -> List[Dict]:
        """
        Execute rule actions.
        
        Args:
            document: Document data
            context: Additional context
            
        Returns:
            List of action execution results
        """
        results = []
        for action in self.actions:
            result = action.execute(document, context)
            results.append(result)
        return results


class RuleEngine:
    """Engine for evaluating and executing rules with performance optimizations."""

    def __init__(self):
        self.rules: List[Rule] = []
        self.action_handlers: Dict[str, Callable] = {}
        self.batch_size = int(os.getenv('RULE_ENGINE_BATCH_SIZE', '100'))
        self.timeout = int(os.getenv('RULE_ENGINE_TIMEOUT', '30'))
        self.performance_log = []
        self.indexed_fields = ['category', 'status', 'confidence', 'urgency']  # Fields with database indexes

    def _pre_filter_documents(self, documents: List[Dict], rule: Rule) -> List[Dict]:
        """
        Pre-filter documents using indexed fields before rule evaluation.
        This reduces the number of documents that need full evaluation.
        
        Args:
            documents: List of documents to filter
            rule: Rule to pre-filter for
            
        Returns:
            Filtered list of documents
        """
        if not rule.conditions:
            return documents
            
        filtered = documents
        
        # Check each condition for pre-filtering opportunities
        for condition in rule.conditions:
            if condition.field in self.indexed_fields:
                # Apply simple filtering for indexed fields
                if condition.operator == 'eq':
                    filtered = [d for d in filtered if self._get_field_value(d, condition.field) == condition.value]
                elif condition.operator == 'in':
                    filtered = [d for d in filtered if self._get_field_value(d, condition.field) in condition.value]
                elif condition.operator == 'contains':
                    filtered = [d for d in filtered if condition.value in str(self._get_field_value(d, condition.field))]
                
                # Early exit if no documents match
                if not filtered:
                    break
        
        return filtered

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get field value from data (supports nested fields)."""
        if '.' not in field:
            return data.get(field)
        
        keys = field.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def add_rule(self, rule: Rule):
        """Add a rule to the engine."""
        self.rules.append(rule)
        # Sort by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: int):
        """Remove a rule from the engine."""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

    def evaluate_rule(self, rule_id: int, data: Dict) -> bool:
        """
        Evaluate a specific rule.
        
        Args:
            rule_id: Rule ID
            data: Document or event data
            
        Returns:
            True if rule conditions are met
        """
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.evaluate(data)
        return False

    def evaluate_all(self, data: Dict) -> List[int]:
        """
        Evaluate all enabled rules against data.
        
        Args:
            data: Document or event data
            
        Returns:
            List of rule IDs that matched
        """
        matching_rules = []
        for rule in self.rules:
            if rule.evaluate(data):
                matching_rules.append(rule.rule_id)
        return matching_rules

    def execute_rule(self, rule_id: int, document: Dict, context: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a specific rule.
        
        Args:
            rule_id: Rule ID
            document: Document data
            context: Additional context
            
        Returns:
            List of action execution results
        """
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.execute(document, context)
        return []

    def process_document(self, document: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Process document against all rules with performance logging.
        
        Args:
            document: Document data
            context: Additional context
            
        Returns:
            Dictionary with matched rules and execution results
        """
        start_time = time.time()
        context = context or {}
        matched_rules = self.evaluate_all(document)
        
        results = {
            'document_id': document.get('id'),
            'matched_rules': [],
            'execution_results': []
        }

        for rule_id in matched_rules:
            rule_name = next((r.name for r in self.rules if r.rule_id == rule_id), f"Rule {rule_id}")
            action_results = self.execute_rule(rule_id, document, context)
            
            results['matched_rules'].append({
                'rule_id': rule_id,
                'rule_name': rule_name
            })
            results['execution_results'].extend(action_results)

        duration = time.time() - start_time
        self.performance_log.append({
            'operation': 'process_document',
            'document_id': document.get('id'),
            'matched_count': len(matched_rules),
            'duration': duration
        })
        
        # Log slow rule evaluations
        if duration > 1.0:
            logger.warning(f"Slow rule evaluation for document {document.get('id')}: {duration:.2f}s")

        return results

    def process_documents_batch(self, documents: List[Dict], context: Optional[Dict] = None) -> Dict:
        """
        Process multiple documents in batches for improved performance.
        
        Args:
            documents: List of documents to process
            context: Additional context
            
        Returns:
            Dictionary with batch processing results
        """
        start_time = time.time()
        context = context or {}
        results = {
            'total_documents': len(documents),
            'processed_count': 0,
            'total_matches': 0,
            'document_results': [],
            'batch_stats': {}
        }
        
        # Process in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_start = time.time()
            
            for document in batch:
                try:
                    doc_result = self.process_document(document, context)
                    results['document_results'].append(doc_result)
                    results['processed_count'] += 1
                    results['total_matches'] += len(doc_result['matched_rules'])
                except Exception as e:
                    logger.error(f"Failed to process document {document.get('id')}: {e}")
                    results['document_results'].append({
                        'document_id': document.get('id'),
                        'error': str(e)
                    })
            
            batch_duration = time.time() - batch_start
            logger.debug(f"Batch {i//self.batch_size + 1} processed {len(batch)} documents in {batch_duration:.2f}s")

        total_duration = time.time() - start_time
        results['batch_stats'] = {
            'total_duration': total_duration,
            'avg_duration_per_doc': total_duration / len(documents) if documents else 0,
            'docs_per_second': len(documents) / total_duration if total_duration > 0 else 0
        }
        
        logger.info(f"Processed {results['processed_count']} documents in {total_duration:.2f}s ({results['batch_stats']['docs_per_second']:.2f} docs/s)")
        
        return results

    def register_action_handler(self, action_type: str, handler: Callable):
        """Register a custom action handler."""
        self.action_handlers[action_type] = handler

    def clear_rules(self):
        """Clear all rules."""
        self.rules = []

    def get_performance_stats(self) -> Dict:
        """Get performance statistics for rule evaluation."""
        if not self.performance_log:
            return {'message': 'No performance data available'}
        
        total_operations = len(self.performance_log)
        avg_duration = sum(log['duration'] for log in self.performance_log) / total_operations
        slow_operations = [log for log in self.performance_log if log['duration'] > 1.0]
        
        return {
            'total_operations': total_operations,
            'avg_duration': avg_duration,
            'slow_operations_count': len(slow_operations),
            'slow_operations': slow_operations[-10:],  # Last 10 slow operations
            'rule_count': len(self.rules)
        }

    def identify_slow_rules(self) -> List[Dict]:
        """
        Identify rules that are causing performance issues.
        
        Returns:
            List of slow rules with their average evaluation time
        """
        rule_performance = {}
        
        for log in self.performance_log:
            if log['operation'] == 'process_document' and log['matched_count'] > 0:
                doc_id = log['document_id']
                # In a real implementation, we would track which specific rules were slow
                # For now, return documents with slow processing
                if log['duration'] > 1.0:
                    rule_performance[doc_id] = log['duration']
        
        return [{'document_id': doc_id, 'duration': duration} 
                for doc_id, duration in sorted(rule_performance.items(), key=lambda x: x[1], reverse=True)]


# Global rule engine instance
rule_engine = RuleEngine()