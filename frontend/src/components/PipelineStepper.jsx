import React from "react";
import { CheckCircle2, AlertTriangle, ShieldAlert, Cpu, Sparkles, ShieldCheck, UserCheck, XCircle, Check, Loader2, Clock, Terminal, Activity } from "lucide-react";

export default function PipelineStepper({ pipelineState, currentRun }) {
  const steps = [
    {
      id: "denial",
      label: "Denial Captured",
      description: "AgentCore Gateway Cedar enforcement",
      icon: ShieldAlert,
      duration: "12ms",
      timestamp: "T+00ms",
      getData: (run) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
            <span>Result:</span>
            <span className="font-bold text-muted-red">-32002 DENY</span>
          </div>
          <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-surface-subtle p-1 rounded border border-ink-200">
            {run?.action || "process-refund"} (${run?.amount?.toLocaleString() || "2,000"})
          </div>
        </div>
      ),
    },
    {
      id: "diagnose",
      label: "Bedrock Diagnosis",
      description: "AST condition root cause reasoning",
      icon: Cpu,
      duration: "340ms",
      timestamp: "T+12ms",
      getData: (run) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
            <span>Result:</span>
            <span className="font-bold text-ink-900">Root Cause Found</span>
          </div>
          <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-surface-subtle p-1 rounded border border-ink-200">
            Clause: amount &gt; $500
          </div>
        </div>
      ),
    },
    {
      id: "ceiling",
      label: "$2,500 Ceiling Guard",
      description: "Autonomous limit safety check",
      icon: AlertTriangle,
      duration: "45ms",
      timestamp: "T+352ms",
      getData: (run) => {
        const isCeil = run?.isCeilingTriggered || (run?.amount > 2500);
        return (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
              <span>Result:</span>
              <span className={`font-bold ${isCeil ? "text-muted-amber" : "text-muted-green"}`}>
                {isCeil ? "Ceiling Exceeded" : "Boundary OK"}
              </span>
            </div>
            <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-surface-subtle p-1 rounded border border-ink-200">
              ${run?.amount?.toLocaleString() || "2,000"} {isCeil ? "> $2,500" : "≤ $2,500"}
            </div>
          </div>
        );
      },
    },
    {
      id: "patch",
      label: "Patch Synthesis",
      description: "Scoped Cedar condition hot-patch",
      icon: Sparkles,
      duration: "280ms",
      timestamp: "T+397ms",
      getData: (run) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
            <span>Result:</span>
            <span className="font-bold text-muted-green">Diff Synthesized</span>
          </div>
          <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-surface-subtle p-1 rounded border border-ink-200">
            amount &le; $2,500
          </div>
        </div>
      ),
    },
    {
      id: "adversarial",
      label: "Adversarial Battery",
      description: "Automated synthesis of 5 vectors",
      icon: ShieldCheck,
      duration: "190ms",
      timestamp: "T+677ms",
      getData: (run) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
            <span>Result:</span>
            <span className="font-bold text-ink-900">5 Test Vectors</span>
          </div>
          <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-surface-subtle p-1 rounded border border-ink-200">
            Role & Boundary checks
          </div>
        </div>
      ),
    },
    {
      id: "verify",
      label: "In-Process Verify",
      description: "Cedar AST evaluator regression test",
      icon: CheckCircle2,
      duration: "85ms",
      timestamp: "T+867ms",
      getData: (run) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
            <span>Result:</span>
            <span className="font-bold text-muted-green">5/5 PASSED</span>
          </div>
          <div className="text-[11px] font-mono text-muted-green font-semibold truncate bg-muted-green-light/40 p-1 rounded border border-muted-green-border">
            AST PERMIT/DENY OK
          </div>
        </div>
      ),
    },
    {
      id: "approval",
      label: "Cognito Governance",
      description: "Signed reviewer authorization",
      icon: UserCheck,
      duration: "Manual",
      timestamp: "T+952ms",
      getData: (run, state) => {
        let text = "Awaiting Sign-off";
        let statusBadge = "text-ink-700 bg-surface-subtle border-ink-200";
        if (state.status === "approved") {
          text = "Signed & Deployed";
          statusBadge = "text-muted-green bg-muted-green-light/60 border-muted-green-border";
        } else if (state.status === "rejected") {
          text = "Rejected by Admin";
          statusBadge = "text-muted-red bg-muted-red-light/60 border-muted-red-border";
        } else if (state.isCeilingBlocked) {
          text = "Manual Review Required";
          statusBadge = "text-muted-amber bg-muted-amber-light/60 border-muted-amber-border";
        }
        return (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-ink-600">
              <span>Result:</span>
              <span className="font-bold text-ink-900">{state.status === "approved" ? "MUTATED" : "PENDING"}</span>
            </div>
            <div className={`text-[11px] font-mono truncate p-1 rounded border font-semibold ${statusBadge}`}>
              {text}
            </div>
          </div>
        );
      },
    },
  ];

  const getStepStatus = (stepIndex) => {
    const currentStepIndex = pipelineState.currentStepIndex;
    if (pipelineState.isFailed && stepIndex === currentStepIndex) return "failed";
    if (pipelineState.isCeilingBlocked && stepIndex === 2) return "blocked";
    if (pipelineState.isCeilingBlocked && stepIndex > 2) return "pending";
    if (stepIndex < currentStepIndex) return "completed";
    if (stepIndex === currentStepIndex) return pipelineState.status === "running" ? "in-progress" : "completed";
    return "pending";
  };

  const currentIdx = pipelineState.currentStepIndex;
  const progressPercentage = Math.min(100, Math.max(0, (currentIdx / 6) * 100));

  return (
    <div className="bg-surface rounded-xl border-2 border-ink-300 p-6 shadow-md relative overflow-hidden bg-gradient-to-b from-surface via-surface to-surface-subtle/40">
      {/* Centerpiece Header with Deep Architecture Details */}
      <div className="flex flex-wrap items-center justify-between mb-5 pb-4 border-b border-ink-200 gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-lg font-bold text-ink-900 tracking-tight">
              AWS Step Functions Remediation Pipeline
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-ink-900 text-white uppercase tracking-wider">
              Core Engine
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-600 font-mono">
            <span>State Machine: <span className="font-semibold text-ink-900">CedarShieldRemediationPipeline</span></span>
            <span className="text-ink-300">·</span>
            <span>Execution ID: <span className="font-semibold text-ink-900">{currentRun?.runId || "run_live"}</span></span>
            <span className="text-ink-300">·</span>
            <span className="flex items-center gap-1 text-muted-green font-semibold">
              <Clock className="w-3.5 h-3.5" />
              <span>952ms total execution</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {pipelineState.status === "running" && (
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-surface-subtle text-ink-700 border border-ink-300 shadow-none opacity-85 select-none animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-ink-600" />
              <span>Evaluating Stage {currentIdx + 1}/7: {steps[currentIdx]?.label}...</span>
            </span>
          )}
          {pipelineState.status === "awaiting_approval" && (
            <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-muted-green-light text-muted-green border border-muted-green-border shadow-xs">
              <CheckCircle2 className="w-4 h-4" />
              <span>Verified & Awaiting Human Signoff</span>
            </span>
          )}
          {pipelineState.status === "blocked_ceiling" && (
            <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-muted-amber-light text-muted-amber border border-muted-amber-border shadow-xs">
              <AlertTriangle className="w-4 h-4" />
              <span>Guardrail Halted at $2,500 Safety Ceiling</span>
            </span>
          )}
          {pipelineState.status === "approved" && (
            <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-muted-green text-white shadow-xs">
              <CheckCircle2 className="w-4 h-4" />
              <span>Cedar Policy Mutated on Live Engine</span>
            </span>
          )}
          {pipelineState.status === "rejected" && (
            <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-muted-red-light text-muted-red border border-muted-red-border shadow-xs">
              <XCircle className="w-4 h-4" />
              <span>Remediation Rejected by Reviewer</span>
            </span>
          )}
        </div>
      </div>

      {/* CONTINUOUS PIPELINE PROGRESS RAIL (Subway / Flow Line) */}
      <div className="mb-5 hidden lg:block px-8">
        <div className="relative">
          {/* Inactive Background Rail */}
          <div className="absolute top-1/2 left-0 right-0 h-2 -translate-y-1/2 bg-ink-200 rounded-full z-0" />
          
          {/* Active Highlighted Rail Progress */}
          <div 
            className={`absolute top-1/2 left-0 h-2 -translate-y-1/2 bg-muted-green rounded-full z-0 transition-all duration-300 ease-out shadow-xs ${
              pipelineState.status === "running" ? "bg-gradient-to-r from-muted-green via-muted-amber to-muted-amber shadow-sm" : ""
            }`}
            style={{ width: `${progressPercentage}%` }}
          />

          {/* Station Nodes Positioned Directly on the Rail */}
          <div className="flex justify-between items-center relative z-10">
            {steps.map((step, idx) => {
              const status = getStepStatus(idx);
              const isCurrent = idx === currentIdx;

              let nodeClass = "bg-surface border-ink-300 text-ink-400";
              if (status === "completed") {
                nodeClass = "bg-muted-green border-muted-green text-white shadow-sm ring-2 ring-muted-green/20";
              } else if (status === "in-progress" || (pipelineState.status === "running" && isCurrent)) {
                nodeClass = "bg-muted-amber border-muted-amber text-white ring-4 ring-muted-amber/30 shadow-md";
              } else if (status === "blocked") {
                nodeClass = "bg-muted-amber border-muted-amber text-white shadow-sm";
              }

              return (
                <div key={step.id} className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-xs font-bold transition-all duration-200 ${nodeClass}`}>
                    {status === "completed" ? (
                      <Check className="w-4 h-4 text-white" />
                    ) : (status === "in-progress" || (pipelineState.status === "running" && isCurrent)) ? (
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    ) : (
                      <span>{idx + 1}</span>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-ink-700 mt-1 font-semibold">
                    {step.duration}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 7 Stage Detail Cards Linked to Station Nodes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3 relative">
        {steps.map((step, idx) => {
          const status = getStepStatus(idx);
          const Icon = step.icon;

          let statusClass = "border-ink-200 bg-surface/70 text-ink-400 opacity-60";
          let iconClass = "text-ink-400 bg-ink-100";
          let badgeClass = "bg-ink-100 text-ink-600";
          let badgeText = "PENDING";

          if (status === "completed") {
            statusClass = "border-muted-green-border bg-surface text-ink-900 shadow-xs hover:border-muted-green ring-1 ring-muted-green/15";
            iconClass = "text-muted-green bg-muted-green-light";
            badgeClass = "bg-muted-green text-white";
            badgeText = "DONE";
          } else if (status === "in-progress") {
            statusClass = "border-muted-amber-border bg-surface text-ink-900 ring-2 ring-muted-amber/60 shadow-md";
            iconClass = "text-muted-amber bg-muted-amber-light";
            badgeClass = "bg-muted-amber text-white";
            badgeText = "RUNNING";
          } else if (status === "blocked") {
            statusClass = "border-muted-amber-border bg-muted-amber-light/30 text-ink-900 shadow-xs";
            iconClass = "text-muted-amber bg-muted-amber-light";
            badgeClass = "bg-muted-amber text-white";
            badgeText = "BLOCKED";
          } else if (status === "failed") {
            statusClass = "border-muted-red-border bg-muted-red-light/30 text-ink-900";
            iconClass = "text-muted-red bg-muted-red-light";
            badgeClass = "bg-muted-red text-white";
            badgeText = "FAILED";
          }

          return (
            <div
              key={step.id}
              className={`p-3.5 rounded-lg border flex flex-col justify-between transition-colors duration-150 ${statusClass}`}
            >
              <div>
                {/* Header with Stage Number, Duration & Status Badge */}
                <div className="flex items-center justify-between mb-2">
                  <div className={`w-7 h-7 rounded-md flex items-center justify-center transition-all ${iconClass}`}>
                    {status === "in-progress" ? (
                      <Loader2 className="w-4 h-4 animate-spin text-muted-amber" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase flex items-center gap-1 ${badgeClass}`}>
                      {status === "in-progress" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                      {badgeText}
                    </span>
                  </div>
                </div>

                {/* Stage Title */}
                <h3 className="font-serif text-xs font-bold leading-tight text-ink-900 mb-0.5">
                  {step.label}
                </h3>
                <p className="text-[10px] text-ink-500 leading-snug line-clamp-2 mb-2">
                  {step.description}
                </p>

                {/* Real Timing Info - Enhanced Contrast & Legibility */}
                <div className="flex items-center justify-between text-[11px] font-mono pb-1.5 mb-1.5 border-b border-ink-200">
                  <span className="flex items-center gap-1 text-ink-800 font-semibold">
                    <Clock className="w-3.5 h-3.5 text-ink-500" />
                    <span>{step.duration}</span>
                  </span>
                  <span className="font-semibold text-ink-600">{step.timestamp}</span>
                </div>

                {/* Stage-Specific Structured Output or Dynamic In-Progress Status */}
                <div>
                  {pipelineState.status === "running" && idx === currentIdx ? (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-mono text-muted-amber font-bold">
                        <span>Evaluating...</span>
                        <span className="text-[10px]">T+{step.duration}</span>
                      </div>
                      <div className="text-[11px] font-mono text-ink-800 font-medium truncate bg-muted-amber-light/40 p-1 rounded border border-muted-amber-border">
                        Analyzing AST node...
                      </div>
                    </div>
                  ) : pipelineState.status === "running" && idx > currentIdx ? (
                    <div className="space-y-1 opacity-60">
                      <div className="flex items-center justify-between text-[11px] font-mono text-ink-500">
                        <span>Status:</span>
                        <span>Queued</span>
                      </div>
                      <div className="text-[11px] font-mono text-ink-600 truncate bg-surface-subtle p-1 rounded border border-ink-100">
                        Awaiting Stage {idx}
                      </div>
                    </div>
                  ) : (
                    step.getData(currentRun, pipelineState)
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
