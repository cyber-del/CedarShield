import React, { useState, useMemo } from "react";
import { 
  Server, 
  Zap, 
  Workflow, 
  Code2, 
  BrainCircuit, 
  Database, 
  Users, 
  ArrowRight, 
  CheckCircle2, 
  ShieldCheck, 
  Shield, 
  ExternalLink,
  Lock,
  Layers,
  Radio,
  Share2,
  Activity
} from "lucide-react";

const NODES = [
  {
    id: "gateway",
    title: "AgentCore Gateway",
    subtitle: "MCP Enforcement Layer",
    icon: ShieldCheck,
    service: "Amazon Bedrock AgentCore",
    arn: "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv",
    status: "READY (Mode: ENFORCE)",
    connectedTo: ["eventbridge", "bedrock", "cognito"],
    flowDescription: "Evaluates Cedar policies synchronously; emits policy denial payloads to EventBridge when -32002 threshold breaches occur.",
    details: "Intercepts MCP tools/call requests via AWS SigV4 signed sessions. Enforces active Cedar policies and synchronously returns -32002 JSON-RPC denials for unauthorized transactions."
  },
  {
    id: "eventbridge",
    title: "EventBridge Bus",
    subtitle: "Asynchronous Dispatch",
    icon: Zap,
    service: "Amazon EventBridge",
    arn: "arn:aws:events:ap-southeast-2:097935663941:event-bus/default",
    status: "ACTIVE (Rule: CedarShield.PolicyDenied)",
    connectedTo: ["gateway", "stepfunctions"],
    flowDescription: "Receives raw denial payloads from Gateway and triggers the Step Functions CedarShieldRemediationPipeline state machine asynchronously.",
    details: "Captures policy denial payloads (principal ARN, action, requested amount, context) from AgentCore Gateway and fans out to the remediation orchestrator."
  },
  {
    id: "stepfunctions",
    title: "Step Functions",
    subtitle: "State Machine",
    icon: Workflow,
    service: "AWS Step Functions",
    arn: "arn:aws:states:ap-southeast-2:097935663941:stateMachine:CedarShieldRemediationPipeline",
    status: "ACTIVE ($2,500 Hard Ceiling Guard)",
    connectedTo: ["eventbridge", "lambda", "bedrock"],
    flowDescription: "Controls remediation lifecycle: invokes Lambda workers for AST analysis and Bedrock for Cedar synthesis, routing >$2,500 breaches to manual review.",
    details: "Orchestrates Diagnose -> CheckCeiling -> Patch -> AdversarialVerify -> AwaitApproval flow. Enforces hard $2,500 autonomous boundary, routing high-risk breaches to manual review."
  },
  {
    id: "lambda",
    title: "Lambda Workers",
    subtitle: "AST & Test Verifiers",
    icon: Code2,
    service: "AWS Lambda",
    arn: "arn:aws:lambda:ap-southeast-2:097935663941:function:CedarShield-*",
    status: "ACTIVE (Python 3.11 Runtime)",
    connectedTo: ["stepfunctions", "bedrock", "dynamodb"],
    flowDescription: "Executes 5-vector adversarial edge-case testing, unified git-diff synthesis, and computes SHA-256 block hashes into DynamoDB.",
    details: "Executes diagnosis, Cedar patch unification, 5-vector adversarial test suites, and cryptographic SHA-256 block hashing."
  },
  {
    id: "bedrock",
    title: "Bedrock & Engine",
    subtitle: "AI Reasoning & Cedar AST",
    icon: BrainCircuit,
    service: "Amazon Bedrock & Policy Engine",
    arn: "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:policy-engine/CedarShieldPolicyEngine-2ivsrp1osh",
    status: "ACTIVE (Anthropic Claude + Cedar AST)",
    connectedTo: ["stepfunctions", "lambda", "gateway", "dynamodb"],
    flowDescription: "Synthesizes minimal least-privilege Cedar condition patches and evaluates Cedar AST statements in <5ms.",
    details: "Claude models analyze denial root causes and formulate minimal-privilege Cedar diffs. The Policy Engine compiles and evaluates Cedar statements in <5ms."
  },
  {
    id: "dynamodb",
    title: "DynamoDB Ledger",
    subtitle: "Tamper-Evident Chain",
    icon: Database,
    service: "Amazon DynamoDB",
    arn: "arn:aws:dynamodb:ap-southeast-2:097935663941:table/cedarshield-audit-log",
    status: "ACTIVE (SHA-256 Block Chained)",
    connectedTo: ["lambda", "bedrock", "cognito"],
    flowDescription: "Maintains immutable audit sequence. Validates cryptographic prev_hash pointers across all remediation and approval blocks.",
    details: "Immutable audit store. Every decision (denial, patch, approval, rejection) is cryptographically linked to the previous block via prev_hash and record_hash."
  },
  {
    id: "cognito",
    title: "Cognito Governance",
    subtitle: "Human Signoff",
    icon: Users,
    service: "Amazon Cognito",
    arn: "arn:aws:cognito-idp:ap-southeast-2:097935663941:userpool/ap-southeast-2_QGbPPwecZ",
    status: "ACTIVE (App Client: 5v5di986mlbftuo81vvspu1qcd)",
    connectedTo: ["dynamodb", "gateway"],
    flowDescription: "Validates security admin JWT token signatures before authorized Cedar policy mutations are committed to the live Gateway.",
    details: "Enforces cryptographic JWT signature verification before any Cedar patch is applied to the live policy engine. Logs admin identity directly into the tamper-evident chain."
  }
];

export default function ArchitectureView() {
  const [selectedNode, setSelectedNode] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("node") || "stepfunctions";
  });

  const activeNode = useMemo(() => {
    return NODES.find(n => n.id === selectedNode) || NODES[0];
  }, [selectedNode]);

  const connectedNodeIds = useMemo(() => {
    return new Set(activeNode.connectedTo || []);
  }, [activeNode]);

  return (
    <div className="space-y-6">
      {/* Top Header Panel */}
      <div className="bg-surface rounded-lg border border-ink-200 p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-serif text-lg font-semibold text-ink-900">
              AWS Production Architecture & Service Pipeline
            </h2>
            <p className="text-xs text-ink-500">
              End-to-end event-driven policy remediation and governance pipeline deployed in <span className="font-mono text-[11px] text-ink-700">ap-southeast-2</span> (Sydney)
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-ink-600 bg-surface-subtle px-3 py-1.5 rounded-md border border-ink-200">
            <span className="w-2 h-2 rounded-full bg-muted-green animate-pulse" />
            <span>Interactive Topology: Click nodes to trace real-time communication paths</span>
          </div>
        </div>
      </div>

      {/* Interactive Horizontal Pipeline Visualizer with Smooth Transitions */}
      <div className="bg-surface rounded-lg border border-ink-200 p-4 shadow-xs relative">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-7 gap-2 relative z-10">
          {NODES.map((node, index) => {
            const Icon = node.icon;
            const isSelected = selectedNode === node.id;
            const isConnected = connectedNodeIds.has(node.id);

            let cardStyle = "bg-surface-subtle/70 hover:bg-surface text-ink-800 border-ink-200 hover:border-ink-400";
            if (isSelected) {
              cardStyle = "bg-ink-900 text-white border-ink-900 shadow-md ring-2 ring-ink-900/30 scale-[1.02] animate-link-pulse";
            } else if (isConnected) {
              cardStyle = "bg-muted-green-light/40 border-muted-green text-ink-900 shadow-xs ring-2 ring-muted-green/40";
            }

            return (
              <button
                key={node.id}
                onClick={() => setSelectedNode(node.id)}
                className={`p-2.5 rounded-lg border text-left transition-colors duration-150 flex flex-col justify-between hover:-translate-y-0.5 relative ${cardStyle}`}
              >
                <div className="flex items-center justify-between mb-1.5 w-full">
                  <span className={`w-6 h-6 rounded-md flex items-center justify-center transition-colors duration-150 ${
                    isSelected 
                      ? "bg-white/10 text-white" 
                      : isConnected
                      ? "bg-muted-green text-white shadow-xs"
                      : "bg-ink-900 text-white shadow-xs"
                  }`}>
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                  
                  <div className="flex items-center gap-1.5">
                    {isConnected && (
                      <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-md bg-muted-green text-white uppercase tracking-wider">
                        LINKED
                      </span>
                    )}
                    <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md transition-colors duration-150 ${
                      isSelected ? "bg-white/20 text-white" : "bg-ink-200 text-ink-700"
                    }`}>
                      0{index + 1}
                    </span>
                  </div>
                </div>

                <div>
                  <h3 className={`font-serif text-[11px] font-semibold leading-tight transition-colors duration-150 ${
                    isSelected ? "text-white" : "text-ink-900"
                  }`}>
                    {node.title}
                  </h3>
                  <p className={`text-[9px] truncate mt-0.5 transition-colors duration-150 ${
                    isSelected ? "text-white/80" : isConnected ? "text-muted-green font-medium" : "text-ink-500"
                  }`}>
                    {isConnected ? "Active Connection" : node.subtitle}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Inter-Service Signal Connection Track */}
        <div className="mt-3 pt-2.5 border-t border-ink-100 flex items-center justify-between text-[11px] font-mono text-ink-500 px-1">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-muted-green animate-pulse" />
            <span>Active Router: <span className="font-semibold text-ink-900 font-sans">{activeNode.title}</span></span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-green animate-ping" />
            <span className="text-muted-green font-semibold font-mono">{activeNode.connectedTo.length} Active Data Channels</span>
          </div>
        </div>
      </div>

      {/* GPU-Composited Detail Panel Container (Never Unmounted) */}
      <div className="bg-surface rounded-lg border border-ink-200 p-5 shadow-xs gpu-layer">
        <div 
          key={selectedNode} 
          className="animate-panel-swap space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-ink-100">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-lg bg-ink-900 text-white flex items-center justify-center shadow-xs">
                <activeNode.icon className="w-5 h-5" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                <h3 className="font-serif text-base font-semibold text-ink-900">
                  {activeNode.title}
                </h3>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md bg-muted-green-light text-muted-green border border-muted-green-border">
                  {activeNode.status}
                </span>
              </div>
              <span className="text-xs text-ink-500 font-medium">
                {activeNode.service}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-ink-500">
              Active Links: <span className="font-semibold text-muted-green">{activeNode.connectedTo.length} Services</span>
            </span>
          </div>
        </div>

        {/* Data Flow & ARN Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="md:col-span-2 space-y-3">
            <div>
              <span className="text-[10px] text-ink-400 font-sans uppercase tracking-wider block mb-1">
                Data Flow & Interactive Link Routing
              </span>
              <div className="bg-surface-subtle p-3.5 rounded-md border border-ink-100 space-y-2">
                <p className="text-xs text-ink-800 leading-relaxed">
                  {activeNode.flowDescription}
                </p>
                <div className="pt-2 border-t border-ink-200/60 flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className="text-ink-500 font-sans">Direct Inter-Service Communications:</span>
                  {activeNode.connectedTo.map((targetId) => {
                    const targetNode = NODES.find(n => n.id === targetId);
                    return (
                      <button
                        key={targetId}
                        onClick={() => setSelectedNode(targetId)}
                        className="cursor-pointer font-mono text-[10px] px-2.5 py-1 rounded bg-white border border-muted-green text-muted-green font-semibold hover:bg-muted-green hover:text-white transition-colors shadow-2xs hover:shadow-xs active:scale-[0.98]"
                        title={`Click to inspect ${targetNode?.title}`}
                      >
                        → {targetNode?.title || targetId}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <span className="text-[10px] text-ink-400 font-sans uppercase tracking-wider block mb-1">
                Live AWS Resource ARN
              </span>
              <div className="bg-surface-subtle p-3 rounded-md border border-ink-100 font-mono text-[11px] text-ink-800 break-all leading-tight select-all">
                {activeNode.arn}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
