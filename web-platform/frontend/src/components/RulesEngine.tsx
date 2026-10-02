import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { 
  Plus, 
  Trash2, 
  Play, 
  Pause, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  Settings,
  Zap,
  ArrowRight,
  FileText,
  Tag,
  Folder,
  Mail,
  Clock,
  User,
  Flag
} from 'lucide-react';

const API_BASE = '/api';

interface RuleCondition {
  field: string;
  operator: string;
  value: string;
}

interface RuleAction {
  type: string;
  params: Record<string, any>;
}

interface Rule {
  id: number;
  name: string;
  description: string;
  enabled: boolean;
  priority: number;
  conditions: RuleCondition[];
  actions: RuleAction[];
  created_at: string;
  execution_count: number;
  last_executed: string | null;
}

const FIELD_OPTIONS = [
  { value: 'category', label: 'Category' },
  { value: 'status', label: 'Status' },
  { value: 'file_size', label: 'File Size' },
  { value: 'confidence', label: 'Confidence Score' },
  { value: 'urgency', label: 'Urgency' },
  { value: 'supplier', label: 'Supplier' },
  { value: 'amount', label: 'Amount' },
  { value: 'bl_number', label: 'Bill of Lading Number' },
];

const OPERATOR_OPTIONS = [
  { value: 'eq', label: 'Equals' },
  { value: 'ne', label: 'Not Equals' },
  { value: 'gt', label: 'Greater Than' },
  { value: 'lt', label: 'Less Than' },
  { value: 'contains', label: 'Contains' },
  { value: 'regex', label: 'Matches Regex' },
];

const ACTION_TYPES = [
  { value: 'set_tag', label: 'Set Tag', icon: Tag },
  { value: 'set_folder', label: 'Set Folder', icon: Folder },
  { value: 'send_email', label: 'Send Email', icon: Mail },
  { value: 'create_reminder', label: 'Create Reminder', icon: Clock },
  { value: 'assign_user', label: 'Assign User', icon: User },
  { value: 'set_urgency', label: 'Set Urgency', icon: Flag },
  { value: 'set_status', label: 'Set Status', icon: FileText },
];

function getToken() {
  return localStorage.getItem('access_token');
}

async function apiFetch(url: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
}

export default function RulesEngine() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // New rule form state
  const [ruleName, setRuleName] = useState('');
  const [ruleDescription, setRuleDescription] = useState('');
  const [rulePriority, setRulePriority] = useState(1);
  const [ruleConditions, setRuleConditions] = useState<RuleCondition[]>([{ field: 'category', operator: 'eq', value: '' }]);
  const [ruleActions, setRuleActions] = useState<RuleAction[]>([{ type: 'set_tag', params: { tag: '' } }]);

  useEffect(() => {
    loadRules();
  }, []);

  async function loadRules() {
    try {
      setLoading(true);
      const response = await apiFetch(`${API_BASE}/rules`);
      if (response.ok) {
        const data = await response.json();
        setRules(data.rules || []);
      }
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  }

  async function createRule() {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/rules`, {
        method: 'POST',
        body: JSON.stringify({
          name: ruleName,
          description: ruleDescription,
          priority: rulePriority,
          conditions: ruleConditions,
          actions: ruleActions,
        }),
      });

      if (response.ok) {
        setSuccess('Rule created successfully');
        setShowCreateDialog(false);
        resetForm();
        loadRules();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create rule');
      }
    } catch (err) {
      setError('Error creating rule');
      console.error('Failed to create rule:', err);
    }
  }

  async function updateRule(ruleId: number) {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: ruleName,
          description: ruleDescription,
          priority: rulePriority,
          conditions: ruleConditions,
          actions: ruleActions,
        }),
      });

      if (response.ok) {
        setSuccess('Rule updated successfully');
        setEditingRule(null);
        resetForm();
        loadRules();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update rule');
      }
    } catch (err) {
      setError('Error updating rule');
      console.error('Failed to update rule:', err);
    }
  }

  async function toggleRule(ruleId: number, enabled: boolean) {
    try {
      const response = await apiFetch(`${API_BASE}/rules/${ruleId}/toggle`, {
        method: 'POST',
        body: JSON.stringify({ enabled }),
      });

      if (response.ok) {
        loadRules();
      }
    } catch (err) {
      console.error('Failed to toggle rule:', err);
    }
  }

  async function deleteRule(ruleId: number) {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/rules/${ruleId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadRules();
      }
    } catch (err) {
      console.error('Failed to delete rule:', err);
    }
  }

  async function testRule(ruleId: number) {
    try {
      const response = await apiFetch(`${API_BASE}/rules/${ruleId}/test`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(`Rule test completed: ${data.matched_count} documents matched`);
        setTimeout(() => setSuccess(null), 3000);
      }
    } catch (err) {
      setError('Failed to test rule');
      console.error('Failed to test rule:', err);
    }
  }

  function addCondition() {
    setRuleConditions([...ruleConditions, { field: 'category', operator: 'eq', value: '' }]);
  }

  function removeCondition(index: number) {
    setRuleConditions(ruleConditions.filter((_, i) => i !== index));
  }

  function updateCondition(index: number, field: keyof RuleCondition, value: string) {
    const newConditions = [...ruleConditions];
    newConditions[index][field] = value;
    setRuleConditions(newConditions);
  }

  function addAction() {
    setRuleActions([...ruleActions, { type: 'set_tag', params: { tag: '' } }]);
  }

  function removeAction(index: number) {
    setRuleActions(ruleActions.filter((_, i) => i !== index));
  }

  function updateAction(index: number, field: keyof RuleAction, value: any) {
    const newActions = [...ruleActions];
    if (field === 'type') {
      newActions[index] = { type: value, params: {} };
    } else {
      newActions[index].params = value;
    }
    setRuleActions(newActions);
  }

  function resetForm() {
    setRuleName('');
    setRuleDescription('');
    setRulePriority(1);
    setRuleConditions([{ field: 'category', operator: 'eq', value: '' }]);
    setRuleActions([{ type: 'set_tag', params: { tag: '' } }]);
  }

  function startEditing(rule: Rule) {
    setEditingRule(rule);
    setRuleName(rule.name);
    setRuleDescription(rule.description);
    setRulePriority(rule.priority);
    setRuleConditions(rule.conditions);
    setRuleActions(rule.actions);
    setShowCreateDialog(true);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading rules...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Workflow Automation</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Create IF-THEN rules to automate document processing
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadRules} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Create Rule
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Create/Edit Rule Dialog */}
      {showCreateDialog && (
        <Card className="border-blue-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              {editingRule ? 'Edit Rule' : 'Create New Rule'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Rule Name</Label>
                  <Input
                    value={ruleName}
                    onChange={(e) => setRuleName(e.target.value)}
                    placeholder="e.g., Auto-tag FDA documents"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={ruleDescription}
                    onChange={(e) => setRuleDescription(e.target.value)}
                    placeholder="Describe what this rule does"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Priority (1-10, higher executes first)</Label>
                  <Input
                    type="number"
                    min="1"
                    max="10"
                    value={rulePriority}
                    onChange={(e) => setRulePriority(parseInt(e.target.value))}
                  />
                </div>
              </div>

              {/* Conditions */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-lg font-medium">IF Conditions</Label>
                  <Button onClick={addCondition} size="sm" variant="outline">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Condition
                  </Button>
                </div>
                {ruleConditions.map((condition, index) => (
                  <div key={index} className="flex gap-2 items-center p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
                    <Select
                      value={condition.field}
                      onValueChange={(value) => updateCondition(index, 'field', value)}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {FIELD_OPTIONS.map(field => (
                          <SelectItem key={field.value} value={field.value}>
                            {field.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select
                      value={condition.operator}
                      onValueChange={(value) => updateCondition(index, 'operator', value)}
                    >
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {OPERATOR_OPTIONS.map(op => (
                          <SelectItem key={op.value} value={op.value}>
                            {op.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      value={condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                      placeholder="Value"
                      className="flex-1"
                    />
                    <Button
                      onClick={() => removeCondition(index)}
                      variant="ghost"
                      size="icon"
                      className="text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-lg font-medium">THEN Actions</Label>
                  <Button onClick={addAction} size="sm" variant="outline">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Action
                  </Button>
                </div>
                {ruleActions.map((action, index) => (
                  <div key={index} className="flex gap-2 items-center p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
                    <Select
                      value={action.type}
                      onValueChange={(value) => updateAction(index, 'type', value)}
                    >
                      <SelectTrigger className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ACTION_TYPES.map(at => (
                          <SelectItem key={at.value} value={at.value}>
                            <div className="flex items-center gap-2">
                              <at.icon className="w-4 h-4" />
                              {at.label}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      value={action.params.tag || action.params.folder || action.params.status || action.params.urgency || ''}
                      onChange={(e) => updateAction(index, 'params', { 
                        tag: action.type === 'set_tag' ? e.target.value : action.params.tag,
                        folder: action.type === 'set_folder' ? e.target.value : action.params.folder,
                        status: action.type === 'set_status' ? e.target.value : action.params.status,
                        urgency: action.type === 'set_urgency' ? e.target.value : action.params.urgency,
                      })}
                      placeholder="Parameter value"
                      className="flex-1"
                    />
                    <Button
                      onClick={() => removeAction(index)}
                      variant="ghost"
                      size="icon"
                      className="text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button onClick={editingRule ? () => updateRule(editingRule.id) : createRule}>
                  {editingRule ? 'Update Rule' : 'Create Rule'}
                </Button>
                <Button onClick={() => { setShowCreateDialog(false); setEditingRule(null); resetForm(); }} variant="outline">
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rules List */}
      <div className="space-y-4">
        {rules.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Zap className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
                No Rules Created
              </h3>
              <p className="text-slate-500 dark:text-slate-400">
                Create your first automation rule to streamline document processing
              </p>
            </CardContent>
          </Card>
        ) : (
          rules.map(rule => (
            <Card key={rule.id} className={!rule.enabled ? 'opacity-60' : ''}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <CardTitle className="text-lg">{rule.name}</CardTitle>
                      <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                        {rule.enabled ? 'Active' : 'Inactive'}
                      </Badge>
                      <Badge variant="outline">Priority: {rule.priority}</Badge>
                    </div>
                    <CardDescription>{rule.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => toggleRule(rule.id, !rule.enabled)}
                      variant="ghost"
                      size="icon"
                    >
                      {rule.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button onClick={() => testRule(rule.id)} variant="ghost" size="icon">
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button onClick={() => startEditing(rule)} variant="ghost" size="icon">
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button onClick={() => deleteRule(rule.id)} variant="ghost" size="icon" className="text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="conditions" className="w-full">
                  <TabsList>
                    <TabsTrigger value="conditions">Conditions</TabsTrigger>
                    <TabsTrigger value="actions">Actions</TabsTrigger>
                    <TabsTrigger value="stats">Statistics</TabsTrigger>
                  </TabsList>

                  <TabsContent value="conditions" className="mt-4">
                    <div className="space-y-2">
                      {rule.conditions.map((condition, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          <span className="font-medium">{index + 1}.</span>
                          <span>{FIELD_OPTIONS.find(f => f.value === condition.field)?.label}</span>
                          <span className="text-slate-500">{OPERATOR_OPTIONS.find(o => o.value === condition.operator)?.label}</span>
                          <span className="font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                            {condition.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="actions" className="mt-4">
                    <div className="space-y-2">
                      {rule.actions.map((action, index) => {
                        const actionType = ACTION_TYPES.find(a => a.value === action.type);
                        return (
                          <div key={index} className="flex items-center gap-2 text-sm">
                            <actionType.icon className="w-4 h-4" />
                            <span>{actionType.label}</span>
                            <ArrowRight className="w-4 h-4 text-slate-400" />
                            <span className="font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                              {JSON.stringify(action.params)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </TabsContent>

                  <TabsContent value="stats" className="mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-slate-500">Execution Count</div>
                        <div className="text-2xl font-bold">{rule.execution_count}</div>
                      </div>
                      <div>
                        <div className="text-sm text-slate-500">Last Executed</div>
                        <div className="text-sm">
                          {rule.last_executed 
                            ? new Date(rule.last_executed).toLocaleString()
                            : 'Never'}
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
