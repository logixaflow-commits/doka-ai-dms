import React, { useState, useRef, useMemo } from 'react';
import {
  Play,
  Square,
  Plus,
  Save,
  Trash2,
  Settings2,
  FileText,
  ScanText,
  ShieldCheck,
  Send,
  Cloud,
  CheckCircle2,
  Clock,
  Sparkles,
  Layers,
  X,
  Activity,
  Sliders,
  Lock,
  Eye,
  FileCheck
} from 'lucide-react';

export interface WorkflowNode {
  id: string;
  title: string;
  category: 'trigger' | 'ocr' | 'ai' | 'approval' | 'storage';
  type: string;
  x: number;
  y: number;
  status: 'idle' | 'running' | 'success' | 'error';
  config: Record<string, any>;
  icon: string;
}

export interface WorkflowConnection {
  id: string;
  from: string;
  to: string;
}

const INITIAL_NODES: WorkflowNode[] = [
  {
    id: 'doka-trigger',
    title: 'Inbound Document Watcher',
    category: 'trigger',
    type: 'Dropzone & S3 Webhook',
    x: 60,
    y: 140,
    status: 'idle',
    config: {
      acceptedFormats: ['PDF', 'TIFF', 'PNG', 'JPEG'],
      maxFileSize: '50MB',
      pollInterval: 'Realtime WebSocket',
    },
    icon: 'FileText',
  },
  {
    id: 'doka-ocr',
    title: 'Tesseract Neural OCR',
    category: 'ocr',
    type: 'Bilingual OCR Engine',
    x: 420,
    y: 140,
    status: 'idle',
    config: {
      languages: ['my_MM (Burmese)', 'eng (English)'],
      dpiUpscaling: true,
      tableDetection: 'Enabled',
    },
    icon: 'ScanText',
  },
  {
    id: 'doka-ai-extract',
    title: 'Gemini 2.5 Entity Parser',
    category: 'ai',
    type: 'Structured Data Extractor',
    x: 780,
    y: 70,
    status: 'idle',
    config: {
      model: 'gemini-2.5-pro',
      fields: ['Vendor', 'TaxID', 'InvoiceDate', 'LineItems', 'TotalAmount'],
      confidenceThreshold: 0.92,
    },
    icon: 'Sparkles',
  },
  {
    id: 'doka-pii-mask',
    title: 'PII & Security Masker',
    category: 'approval',
    type: 'GDPR / Compliance Filter',
    x: 780,
    y: 290,
    status: 'idle',
    config: {
      redactNRC: true,
      redactCreditCards: true,
      encryption: 'AES-GCM 256-bit',
    },
    icon: 'ShieldCheck',
  },
  {
    id: 'doka-telegram-gate',
    title: 'Telegram Approval Gate',
    category: 'approval',
    type: 'Human-in-the-Loop Bot',
    x: 1140,
    y: 140,
    status: 'idle',
    config: {
      targetTopic: '#Doka-Approval-Channel',
      autoApproveAboveConfidence: 0.95,
      notificationType: 'Interactive Inline Keyboard',
    },
    icon: 'Send',
  },
  {
    id: 'doka-cloud-vault',
    title: 'Encrypted Cloud Archive',
    category: 'storage',
    type: 'Cloud Vault & Audit Log',
    x: 1480,
    y: 140,
    status: 'idle',
    config: {
      destination: 'Supabase Encrypted Storage',
      immutabilityLock: 'WORM (Write Once, Read Many)',
      retentionPolicy: '7 Years Compliance',
    },
    icon: 'Cloud',
  },
];

const INITIAL_CONNECTIONS: WorkflowConnection[] = [
  { id: 'c1', from: 'doka-trigger', to: 'doka-ocr' },
  { id: 'c2', from: 'doka-ocr', to: 'doka-ai-extract' },
  { id: 'c3', from: 'doka-ocr', to: 'doka-pii-mask' },
  { id: 'c4', from: 'doka-ai-extract', to: 'doka-telegram-gate' },
  { id: 'c5', from: 'doka-pii-mask', to: 'doka-telegram-gate' },
  { id: 'c6', from: 'doka-telegram-gate', to: 'doka-cloud-vault' },
];

const AVAILABLE_MODULES = [
  { title: 'Barcode & QR Code Decoder', category: 'ocr', type: 'ZBar Scanner', icon: 'ScanText', desc: 'Auto-extracts tracking barcodes and digital signatures' },
  { title: 'Document Deduplicator', category: 'ai', type: 'SHA-256 & Perceptual Hash', icon: 'FileCheck', desc: 'Detects duplicates before saving to storage' },
  { title: 'PDF Splitter & Merger', category: 'trigger', type: 'Batch Processor', icon: 'Layers', desc: 'Splits multi-page bulk scans into individual vouchers' },
  { title: 'ERP/Accounting Webhook', category: 'storage', type: 'REST API Dispatcher', icon: 'Send', desc: 'Posts structured invoice JSON to SAP/QuickBooks' },
];

export default function WorkflowsPage() {
  const [nodes, setNodes] = useState<WorkflowNode[]>(INITIAL_NODES);
  const [connections, setConnections] = useState<WorkflowConnection[]>(INITIAL_CONNECTIONS);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<Array<{ timestamp: string; nodeTitle: string; message: string; type: 'info' | 'success' | 'warn' }>>([
    { timestamp: '09:00:00', nodeTitle: 'DOKA-CORE', message: 'Document automation pipeline ready. Awaiting trigger.', type: 'info' }
  ]);
  const [showAddDrawer, setShowAddDrawer] = useState(false);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const canvasRef = useRef<HTMLDivElement>(null);
  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);

  // Dragging logic
  const handleMouseDown = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedNodeId(id);
    const node = nodes.find(n => n.id === id);
    if (!node) return;
    setDraggingNodeId(id);
    setDragOffset({
      x: e.clientX - node.x,
      y: e.clientY - node.y,
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNodeId) return;
    const newX = Math.max(20, Math.min(1900, e.clientX - dragOffset.x));
    const newY = Math.max(20, Math.min(900, e.clientY - dragOffset.y));
    setNodes(prev => prev.map(n => n.id === draggingNodeId ? { ...n, x: newX, y: newY } : n));
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
  };

  const handleAddModule = (module: typeof AVAILABLE_MODULES[0]) => {
    const newId = `node-${Date.now()}`;
    const newNode: WorkflowNode = {
      id: newId,
      title: module.title,
      category: module.category as any,
      type: module.type,
      x: 350 + Math.random() * 200,
      y: 200 + Math.random() * 150,
      status: 'idle',
      config: { note: 'Added via Doka Visual Canvas' },
      icon: module.icon,
    };
    setNodes(prev => [...prev, newNode]);
    setShowAddDrawer(false);
    setSelectedNodeId(newId);
    setLogs(prev => [
      { timestamp: new Date().toLocaleTimeString(), nodeTitle: module.title, message: 'Node added to pipeline.', type: 'info' },
      ...prev,
    ]);
  };

  const handleDeleteNode = (id: string) => {
    setNodes(prev => prev.filter(n => n.id !== id));
    setConnections(prev => prev.filter(c => c.from !== id && c.to !== id));
    if (selectedNodeId === id) setSelectedNodeId(null);
  };

  // Run Workflow Simulation
  const handleRunWorkflow = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setLogs(prev => [
      { timestamp: new Date().toLocaleTimeString(), nodeTitle: 'ENGINE', message: 'Simulating document intake: "Invoice_2026_0412.pdf"...', type: 'info' },
      ...prev,
    ]);

    setNodes(prev => prev.map(n => ({ ...n, status: 'idle' })));
    const sequence = ['doka-trigger', 'doka-ocr', 'doka-ai-extract', 'doka-pii-mask', 'doka-telegram-gate', 'doka-cloud-vault'];

    for (let i = 0; i < sequence.length; i++) {
      const currentId = sequence[i];
      setNodes(prev => prev.map(n => n.id === currentId ? { ...n, status: 'running' } : n));
      const targetNode = nodes.find(n => n.id === currentId);

      setLogs(prev => [
        { timestamp: new Date().toLocaleTimeString(), nodeTitle: targetNode?.title || currentId, message: `Processing stage [${i + 1}/${sequence.length}]...`, type: 'info' },
        ...prev,
      ]);

      await new Promise(r => setTimeout(r, 850));

      setNodes(prev => prev.map(n => n.id === currentId ? { ...n, status: 'success' } : n));
      setLogs(prev => [
        { timestamp: new Date().toLocaleTimeString(), nodeTitle: targetNode?.title || currentId, message: `Stage completed with 0 errors. Forwarding data.`, type: 'success' },
        ...prev,
      ]);
    }

    setLogs(prev => [
      { timestamp: new Date().toLocaleTimeString(), nodeTitle: 'DOKA-CORE', message: 'Document indexed into Cloud Vault & Telegram notification dispatched!', type: 'success' },
      ...prev,
    ]);
    setIsRunning(false);
  };

  // Render SVG connecting Bezier cables
  const renderCables = () => {
    return connections.map(conn => {
      const fromNode = nodes.find(n => n.id === conn.from);
      const toNode = nodes.find(n => n.id === conn.to);
      if (!fromNode || !toNode) return null;

      const startX = fromNode.x + 240;
      const startY = fromNode.y + 55;
      const endX = toNode.x;
      const endY = toNode.y + 55;

      const deltaX = Math.abs(endX - startX) * 0.5;
      const path = `M ${startX} ${startY} C ${startX + deltaX} ${startY}, ${endX - deltaX} ${endY}, ${endX} ${endY}`;

      const isPulse = fromNode.status === 'running' || toNode.status === 'running';
      const isSuccess = fromNode.status === 'success' && toNode.status === 'success';

      return (
        <g key={conn.id}>
          <path
            d={path}
            fill="none"
            stroke={isPulse ? '#38bdf8' : isSuccess ? '#10b981' : '#334155'}
            strokeWidth={isPulse ? '3' : '2'}
            strokeDasharray={isPulse ? '6,6' : 'none'}
            className={isPulse ? 'animate-pulse' : ''}
          />
          <circle cx={startX} cy={startY} r="4" fill="#38bdf8" />
          <circle cx={endX} cy={endY} r="4" fill="#a855f7" />
        </g>
      );
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-70px)] bg-[#070b14] text-slate-100 overflow-hidden select-none -m-4 sm:-m-7">
      {/* Top Header */}
      <header className="h-14 border-b border-white/[0.08] bg-[#0c1322]/80 backdrop-blur px-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <span className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Sliders className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
              Doka Document Processing Workflow
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Visual n8n Canvas
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">OCR · Entity Extraction · Telegram Gate · Encrypted Vault</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddDrawer(!showAddDrawer)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-slate-200 border border-white/[0.1] transition-all"
          >
            <Plus className="h-3.5 w-3.5 text-cyan-400" />
            Add Node
          </button>

          <button
            onClick={handleRunWorkflow}
            disabled={isRunning}
            className={`flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded-lg shadow-lg transition-all ${
              isRunning
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse'
                : 'bg-gradient-to-r from-blue-500 to-cyan-400 hover:from-blue-400 hover:to-cyan-300 text-slate-950 font-bold shadow-cyan-500/20'
            }`}
          >
            {isRunning ? (
              <>
                <Square className="h-3.5 w-3.5 animate-spin" /> Processing Inbound File...
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" /> Run Pipeline
              </>
            )}
          </button>

          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08]">
            <Save className="h-3.5 w-3.5" /> Save
          </button>
        </div>
      </header>

      {/* Canvas Area */}
      <div className="flex-1 relative overflow-hidden flex" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}>
        <div
          ref={canvasRef}
          onClick={() => setSelectedNodeId(null)}
          className="flex-1 h-full relative cursor-grab active:cursor-grabbing overflow-auto"
          style={{
            backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            backgroundColor: '#070b14',
          }}
        >
          <svg className="absolute inset-0 w-[2400px] h-[1200px] pointer-events-none z-0">
            {renderCables()}
          </svg>

          {nodes.map(node => {
            const isSelected = selectedNodeId === node.id;
            const isRunningNode = node.status === 'running';
            const isSuccessNode = node.status === 'success';

            const categoryColors: Record<string, string> = {
              trigger: 'from-amber-500/20 to-orange-500/10 border-amber-500/40 text-amber-400',
              ocr: 'from-cyan-500/20 to-blue-500/10 border-cyan-500/40 text-cyan-400',
              ai: 'from-purple-500/20 to-pink-500/10 border-purple-500/40 text-purple-400',
              approval: 'from-rose-500/20 to-orange-500/10 border-rose-500/40 text-rose-400',
              storage: 'from-emerald-500/20 to-teal-500/10 border-emerald-500/40 text-emerald-400',
            };

            return (
              <div
                key={node.id}
                onMouseDown={e => handleMouseDown(e, node.id)}
                style={{
                  transform: `translate3d(${node.x}px, ${node.y}px, 0)`,
                  width: '240px',
                }}
                className={`absolute z-10 rounded-xl border p-3.5 backdrop-blur-md bg-slate-900/90 shadow-xl transition-shadow select-none ${
                  isSelected ? 'ring-2 ring-cyan-400 border-cyan-400 shadow-cyan-500/20' : 'border-white/10 hover:border-white/20'
                } ${isRunningNode ? 'ring-2 ring-amber-400 animate-pulse' : ''} ${
                  isSuccessNode ? 'border-emerald-500/60 shadow-emerald-500/10' : ''
                }`}
              >
                <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-cyan-400 hover:scale-125 transition-transform" />
                <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-purple-400 hover:scale-125 transition-transform" />

                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg bg-gradient-to-br border ${categoryColors[node.category] || 'border-white/10'}`}>
                      {node.category === 'trigger' && <FileText className="h-4 w-4" />}
                      {node.category === 'ocr' && <ScanText className="h-4 w-4" />}
                      {node.category === 'ai' && <Sparkles className="h-4 w-4" />}
                      {node.category === 'approval' && <ShieldCheck className="h-4 w-4" />}
                      {node.category === 'storage' && <Cloud className="h-4 w-4" />}
                    </div>
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                        {node.category}
                      </span>
                      <h3 className="text-xs font-semibold text-white leading-tight">{node.title}</h3>
                    </div>
                  </div>

                  <span
                    className={`h-2 w-2 rounded-full ${
                      node.status === 'running'
                        ? 'bg-amber-400 animate-ping'
                        : node.status === 'success'
                        ? 'bg-emerald-400'
                        : 'bg-slate-600'
                    }`}
                  />
                </div>

                <p className="text-[11px] text-slate-400 line-clamp-1 mb-2.5 font-mono">{node.type}</p>

                <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-slate-400">
                  <span className="truncate max-w-[150px]">
                    {node.config.pollInterval || node.config.model || node.config.targetTopic || node.config.destination || 'Active'}
                  </span>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      handleDeleteNode(node.id);
                    }}
                    className="text-slate-500 hover:text-rose-400 p-0.5 rounded transition-colors"
                    title="Delete Node"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Node Inspector Drawer */}
        {selectedNode && (
          <div className="w-80 border-l border-white/[0.08] bg-[#0c1322]/95 backdrop-blur-xl p-5 flex flex-col z-20 shadow-2xl overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-4">
              <div className="flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-cyan-400" />
                <h2 className="text-sm font-semibold text-white">Doka Node Inspector</h2>
              </div>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="text-slate-400 hover:text-white p-1 rounded-md"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Title</label>
                <input
                  type="text"
                  value={selectedNode.title}
                  onChange={e => {
                    const val = e.target.value;
                    setNodes(prev => prev.map(n => n.id === selectedNode.id ? { ...n, title: val } : n));
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.1] text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Type & Category</label>
                <div className="px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 font-mono text-[11px]">
                  {selectedNode.type} ({selectedNode.category})
                </div>
              </div>

              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Configuration Parameters</label>
                <pre className="p-3 rounded-lg bg-black/40 border border-white/[0.08] text-[11px] text-cyan-300 font-mono overflow-x-auto">
                  {JSON.stringify(selectedNode.config, null, 2)}
                </pre>
              </div>

              <div className="pt-4 border-t border-white/[0.08]">
                <button
                  onClick={() => handleDeleteNode(selectedNode.id)}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 transition-all font-medium text-xs"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Remove from Pipeline
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Add Node Modal */}
        {showAddDrawer && (
          <div className="absolute top-4 left-6 w-80 bg-[#0d1627] border border-white/10 rounded-xl shadow-2xl p-4 z-30 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] mb-3">
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Plus className="h-3.5 w-3.5 text-cyan-400" /> Doka Processing Modules
              </span>
              <button onClick={() => setShowAddDrawer(false)} className="text-slate-400 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2">
              {AVAILABLE_MODULES.map((mod, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAddModule(mod)}
                  className="w-full text-left p-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] hover:border-cyan-500/30 transition-all flex flex-col gap-1 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-200 group-hover:text-cyan-300">{mod.title}</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 uppercase">
                      {mod.category}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 leading-normal">{mod.desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Telemetry & Audit Logs */}
      <div className="h-32 border-t border-white/[0.08] bg-[#070d18] px-6 py-2.5 flex flex-col z-20">
        <div className="flex items-center justify-between pb-1.5 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-blue-400" />
            <span className="text-xs font-mono font-medium text-slate-300">DOKA PIPELINE AUDIT LOGS</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            {isRunning ? 'PROCESSING ACTIVE' : 'SYSTEM STANDBY'}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto font-mono text-[11px] space-y-1 pt-1.5">
          {logs.map((log, index) => (
            <div key={index} className="flex items-center gap-3">
              <span className="text-slate-500">{log.timestamp}</span>
              <span className="text-blue-400 font-semibold">[{log.nodeTitle}]</span>
              <span className={log.type === 'success' ? 'text-emerald-400' : log.type === 'warn' ? 'text-amber-400' : 'text-slate-300'}>
                {log.message}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
