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
  Download, 
  Upload, 
  Trash2, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  FileText,
  Zap,
  Clock,
  Shield,
  Ship,
  Package,
  Users
} from 'lucide-react';

const API_BASE = '/api';

interface Template {
  id: number;
  name: string;
  description: string;
  category: string;
  steps: TemplateStep[];
  created_at: string;
  is_default: boolean;
}

interface TemplateStep {
  id: number;
  title: string;
  description: string;
  required_fields: string[];
  assignee_role: string;
  estimated_duration: number;
}

const TEMPLATE_CATEGORIES = [
  { value: 'import', label: 'Import Process', icon: Ship },
  { value: 'export', label: 'Export Process', icon: Package },
  { value: 'compliance', label: 'Compliance', icon: Shield },
  { value: 'verification', label: 'Verification', icon: Users },
  { value: 'custom', label: 'Custom', icon: FileText },
];

const DEFAULT_TEMPLATES = [
  {
    name: 'Standard Import Workflow',
    description: 'Complete import document processing from submission to approval',
    category: 'import',
    steps: [
      { title: 'Document Upload', description: 'Upload import documents', required_fields: ['invoice', 'bl', 'packing_list'], assignee_role: 'staff', estimated_duration: 30 },
      { title: 'Initial Review', description: 'Review uploaded documents', required_fields: [], assignee_role: 'staff', estimated_duration: 60 },
      { title: 'Customs Check', description: 'Verify customs compliance', required_fields: ['customs_declaration'], assignee_role: 'admin', estimated_duration: 120 },
      { title: 'Final Approval', description: 'Approve or reject import', required_fields: [], assignee_role: 'admin', estimated_duration: 30 },
    ],
  },
  {
    name: 'Express Import',
    description: 'Fast-track import for urgent shipments',
    category: 'import',
    steps: [
      { title: 'Priority Upload', description: 'Upload urgent documents', required_fields: ['invoice', 'bl'], assignee_role: 'staff', estimated_duration: 15 },
      { title: 'Expedited Review', description: 'Quick review process', required_fields: [], assignee_role: 'admin', estimated_duration: 30 },
      { title: 'Fast Approval', description: 'Expedited approval', required_fields: [], assignee_role: 'admin', estimated_duration: 15 },
    ],
  },
  {
    name: 'Standard Export SOP',
    description: 'Standard export processing workflow',
    category: 'export',
    steps: [
      { title: 'Export Declaration', description: 'Submit export documents', required_fields: ['invoice', 'packing_list'], assignee_role: 'staff', estimated_duration: 30 },
      { title: 'Quality Check', description: 'Verify export quality', required_fields: [], assignee_role: 'staff', estimated_duration: 45 },
      { title: 'Customs Clearance', description: 'Clear customs for export', required_fields: ['export_permit'], assignee_role: 'admin', estimated_duration: 90 },
    ],
  },
  {
    name: 'Customs Clearance',
    description: 'Myanmar customs declaration process',
    category: 'compliance',
    steps: [
      { title: 'Document Submission', description: 'Submit customs documents', required_fields: ['customs_form', 'invoice'], assignee_role: 'staff', estimated_duration: 45 },
      { title: 'Authority Review', description: 'Customs authority review', required_fields: [], assignee_role: 'admin', estimated_duration: 180 },
      { title: 'Clearance Decision', description: 'Grant or deny clearance', required_fields: [], assignee_role: 'admin', estimated_duration: 60 },
    ],
  },
  {
    name: 'FDA Approval',
    description: 'Food & Drug approval workflow',
    category: 'compliance',
    steps: [
      { title: 'Application Submission', description: 'Submit FDA application', required_fields: ['application_form', 'lab_report'], assignee_role: 'staff', estimated_duration: 60 },
      { title: 'Lab Verification', description: 'Verify lab results', required_fields: [], assignee_role: 'staff', estimated_duration: 120 },
      { title: 'FDA Review', description: 'FDA authority review', required_fields: [], assignee_role: 'admin', estimated_duration: 240 },
      { title: 'Approval Decision', description: 'Grant or deny approval', required_fields: [], assignee_role: 'admin', estimated_duration: 60 },
    ],
  },
  {
    name: 'NRC Verification',
    description: 'National Registration Card verification',
    category: 'verification',
    steps: [
      { title: 'NRC Submission', description: 'Submit NRC document', required_fields: ['nrc_document'], assignee_role: 'staff', estimated_duration: 30 },
      { title: 'Identity Check', description: 'Verify identity information', required_fields: [], assignee_role: 'staff', estimated_duration: 45 },
      { title: 'Database Verification', description: 'Check against database', required_fields: [], assignee_role: 'admin', estimated_duration: 60 },
    ],
  },
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

export default function TemplateLibrary() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // New template form state
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateCategory, setTemplateCategory] = useState('custom');
  const [templateSteps, setTemplateSteps] = useState<TemplateStep[]>([
    { title: '', description: '', required_fields: [], assignee_role: 'staff', estimated_duration: 30 }
  ]);

  useEffect(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    try {
      setLoading(true);
      const response = await apiFetch(`${API_BASE}/templates`);
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      } else {
        // Load default templates if API fails
        const defaultTemplates = DEFAULT_TEMPLATES.map((t, index) => ({
          id: index + 1,
          ...t,
          created_at: new Date().toISOString(),
          is_default: true,
        }));
        setTemplates(defaultTemplates);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
      // Load default templates on error
      const defaultTemplates = DEFAULT_TEMPLATES.map((t, index) => ({
        id: index + 1,
        ...t,
        created_at: new Date().toISOString(),
        is_default: true,
      }));
      setTemplates(defaultTemplates);
    } finally {
      setLoading(false);
    }
  }

  async function createTemplate() {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/templates`, {
        method: 'POST',
        body: JSON.stringify({
          name: templateName,
          description: templateDescription,
          category: templateCategory,
          steps: templateSteps,
        }),
      });

      if (response.ok) {
        setSuccess('Template created successfully');
        setShowCreateDialog(false);
        resetForm();
        loadTemplates();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create template');
      }
    } catch (err) {
      setError('Error creating template');
      console.error('Failed to create template:', err);
    }
  }

  async function deleteTemplate(templateId: number) {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/templates/${templateId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadTemplates();
      }
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  }

  async function instantiateTemplate(templateId: number) {
    try {
      const response = await apiFetch(`${API_BASE}/templates/${templateId}/instantiate`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('Template instantiated successfully');
        setTimeout(() => setSuccess(null), 3000);
      }
    } catch (err) {
      setError('Failed to instantiate template');
      console.error('Failed to instantiate template:', err);
    }
  }

  async function exportTemplate(templateId: number) {
    try {
      const response = await apiFetch(`${API_BASE}/templates/${templateId}/export`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `template-${templateId}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      setError('Failed to export template');
      console.error('Failed to export template:', err);
    }
  }

  function addStep() {
    setTemplateSteps([...templateSteps, { title: '', description: '', required_fields: [], assignee_role: 'staff', estimated_duration: 30 }]);
  }

  function removeStep(index: number) {
    setTemplateSteps(templateSteps.filter((_, i) => i !== index));
  }

  function updateStep(index: number, field: keyof TemplateStep, value: any) {
    const newSteps = [...templateSteps];
    newSteps[index][field] = value;
    setTemplateSteps(newSteps);
  }

  function resetForm() {
    setTemplateName('');
    setTemplateDescription('');
    setTemplateCategory('custom');
    setTemplateSteps([{ title: '', description: '', required_fields: [], assignee_role: 'staff', estimated_duration: 30 }]);
  }

  const filteredTemplates = selectedCategory === 'all' 
    ? templates 
    : templates.filter(t => t.category === selectedCategory);

  const totalEstimatedTime = (steps: TemplateStep[]) => 
    steps.reduce((sum, step) => sum + step.estimated_duration, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading templates...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Template Library</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Pre-built workflow templates for common processes
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadTemplates} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Create Template
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

      {/* Category Filter */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Button
              variant={selectedCategory === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('all')}
            >
              All Templates
            </Button>
            {TEMPLATE_CATEGORIES.map(category => (
              <Button
                key={category.value}
                variant={selectedCategory === category.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category.value)}
              >
                <category.icon className="w-4 h-4 mr-2" />
                {category.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create Template Dialog */}
      {showCreateDialog && (
        <Card className="border-blue-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Create New Template
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Template Name</Label>
                  <Input
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    placeholder="e.g., Express Import Process"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={templateDescription}
                    onChange={(e) => setTemplateDescription(e.target.value)}
                    placeholder="Describe the workflow"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={templateCategory} onValueChange={setTemplateCategory}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATE_CATEGORIES.map(category => (
                        <SelectItem key={category.value} value={category.value}>
                          {category.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Steps */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-lg font-medium">Workflow Steps</Label>
                  <Button onClick={addStep} size="sm" variant="outline">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Step
                  </Button>
                </div>
                {templateSteps.map((step, index) => (
                  <div key={index} className="p-4 bg-slate-50 dark:bg-slate-900 rounded-lg space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">Step {index + 1}</Badge>
                      <Button
                        onClick={() => removeStep(index)}
                        variant="ghost"
                        size="icon"
                        className="text-red-600 ml-auto"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Step Title</Label>
                        <Input
                          value={step.title}
                          onChange={(e) => updateStep(index, 'title', e.target.value)}
                          placeholder="e.g., Document Review"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Assignee Role</Label>
                        <Select
                          value={step.assignee_role}
                          onValueChange={(value) => updateStep(index, 'assignee_role', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="staff">Staff</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Description</Label>
                      <Input
                        value={step.description}
                        onChange={(e) => updateStep(index, 'description', e.target.value)}
                        placeholder="Describe this step"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Estimated Duration (minutes)</Label>
                      <Input
                        type="number"
                        value={step.estimated_duration}
                        onChange={(e) => updateStep(index, 'estimated_duration', parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button onClick={createTemplate}>
                  Create Template
                </Button>
                <Button onClick={() => { setShowCreateDialog(false); resetForm(); }} variant="outline">
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map(template => {
          const categoryInfo = TEMPLATE_CATEGORIES.find(c => c.value === template.category);
          return (
            <Card key={template.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <categoryInfo.icon className="w-5 h-5 text-slate-400" />
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                  </div>
                  {template.is_default && (
                    <Badge variant="secondary">Default</Badge>
                  )}
                </div>
                <CardDescription>{template.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500">Steps</span>
                    <span className="font-medium">{template.steps.length}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-500">Total Time</span>
                    <span className="font-medium flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {totalEstimatedTime(template.steps)} min
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => instantiateTemplate(template.id)}
                      size="sm"
                      className="flex-1"
                    >
                      <Zap className="w-4 h-4 mr-2" />
                      Use Template
                    </Button>
                    <Button
                      onClick={() => exportTemplate(template.id)}
                      size="sm"
                      variant="outline"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                    {!template.is_default && (
                      <Button
                        onClick={() => deleteTemplate(template.id)}
                        size="sm"
                        variant="ghost"
                        className="text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
              No Templates Found
            </h3>
            <p className="text-slate-500 dark:text-slate-400">
              Create your first workflow template or select a different category
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
