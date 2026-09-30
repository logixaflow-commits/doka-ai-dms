import React, { useState, useEffect } from 'react';
import { FileText, AlertTriangle, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';

interface FunctionDetectionResult {
  primary_function: string;
  confidence: number;
  alternative_functions: Array<{ function: string; confidence: number }>;
  detected_keywords: string[];
  detected_patterns: string[];
}

interface FractureDetectionResult {
  quality_level: string;
  damage_detected: boolean;
  damage_type: string | null;
  damage_severity: string;
  affected_areas: string[];
  confidence: number;
  recommended_actions: string[];
}

interface DocumentAnalysisProps {
  documentId?: number;
  onAnalysisComplete?: (results: any) => void;
}

const DocumentAnalysis: React.FC<DocumentAnalysisProps> = ({ documentId, onAnalysisComplete }) => {
  const [loading, setLoading] = useState(false);
  const [functionResult, setFunctionResult] = useState<FunctionDetectionResult | null>(null);
  const [fractureResult, setFractureResult] = useState<FractureDetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeDocument = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      let endpoint = '/api/analysis/analyze-document';
      
      if (documentId) {
        endpoint = `/api/analysis/analyze-document/${documentId}`;
      }

      const formData = new FormData();
      if (documentId) {
        formData.append('perform_ocr', 'true');
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();
      
      if (data.success) {
        setFunctionResult(data.data.function_detection);
        setFractureResult(data.data.fracture_detection);
        
        if (onAnalysisComplete) {
          onAnalysisComplete(data.data);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50';
      case 'high': return 'text-orange-600 bg-orange-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'text-green-600 bg-green-50';
      case 'good': return 'text-blue-600 bg-blue-50';
      case 'acceptable': return 'text-yellow-600 bg-yellow-50';
      case 'poor': return 'text-orange-600 bg-orange-50';
      case 'fractured': return 'text-red-600 bg-red-50';
      case 'damaged': return 'text-red-600 bg-red-50';
      case 'incomplete': return 'text-orange-600 bg-orange-50';
      case 'unreadable': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Document Analysis
        </h3>
        <button
          onClick={analyzeDocument}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4" />
              Analyze Document
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <XCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {functionResult && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-md font-semibold mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            Function Detection
          </h4>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Primary Function:</span>
              <span className="font-semibold capitalize">
                {functionResult.primary_function.replace(/_/g, ' ')}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Confidence:</span>
              <div className="flex items-center gap-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${functionResult.confidence * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">
                  {(functionResult.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {functionResult.alternative_functions.length > 0 && (
              <div>
                <span className="text-gray-600 block mb-2">Alternative Functions:</span>
                <div className="space-y-2">
                  {functionResult.alternative_functions.map((alt, idx) => (
                    <div key={idx} className="flex items-center justify-between text-sm">
                      <span className="capitalize">{alt.function.replace(/_/g, ' ')}</span>
                      <span className="text-gray-500">{(alt.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {functionResult.detected_keywords.length > 0 && (
              <div>
                <span className="text-gray-600 block mb-2">Detected Keywords:</span>
                <div className="flex flex-wrap gap-2">
                  {functionResult.detected_keywords.map((keyword, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {fractureResult && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-md font-semibold mb-4 flex items-center gap-2">
            {fractureResult.damage_detected ? (
              <AlertTriangle className="w-5 h-5 text-red-600" />
            ) : (
              <CheckCircle className="w-5 h-5 text-green-600" />
            )}
            Quality & Fracture Detection
          </h4>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Quality Level:</span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getQualityColor(fractureResult.quality_level)}`}>
                {fractureResult.quality_level.replace(/_/g, ' ')}
              </span>
            </div>

            {fractureResult.damage_detected && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Damage Type:</span>
                  <span className="font-semibold capitalize">{fractureResult.damage_type?.replace(/_/g, ' ')}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Severity:</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getSeverityColor(fractureResult.damage_severity)}`}>
                    {fractureResult.damage_severity}
                  </span>
                </div>

                {fractureResult.affected_areas.length > 0 && (
                  <div>
                    <span className="text-gray-600 block mb-2">Affected Areas:</span>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {fractureResult.affected_areas.map((area, idx) => (
                        <li key={idx} className="text-gray-700">{area}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}

            {fractureResult.recommended_actions.length > 0 && (
              <div>
                <span className="text-gray-600 block mb-2">Recommended Actions:</span>
                <ul className="space-y-2">
                  {fractureResult.recommended_actions.map((action, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <span className="text-blue-600 mt-1">•</span>
                      <span className="text-gray-700">{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-gray-600">Analysis Confidence:</span>
              <div className="flex items-center gap-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full"
                    style={{ width: `${fractureResult.confidence * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">
                  {(fractureResult.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {!functionResult && !fractureResult && !loading && (
        <div className="text-center py-12 text-gray-500">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p>Click "Analyze Document" to start analysis</p>
        </div>
      )}
    </div>
  );
};

export default DocumentAnalysis;