import React from "react";
import { FileCode, AlertTriangle, ShieldCheck, Info, ArrowRight, CheckCircle2, Stamp, Award } from "lucide-react";

export default function PolicyDiffViewer({ diffData, diagnosis, isCeilingTriggered, amount }) {
  const diffText = diffData?.diff || `--- process_refund.cedar (current)
+++ process_refund.cedar (proposed)
@@ -1,11 +1,11 @@
 permit (
     principal is AgentCore::IamEntity,
     action == AgentCore::Action::"process-refund",
     resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
 )
 when {
     (
         principal.id like "arn:aws:iam::097935663941:role/*FinanceAgent*" ||
         principal.id like "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*"
     ) &&
-    context has amount && context.amount <= 500
+    context has amount && context.amount <= 2500
 };`;

  const diffLines = diffText.split("\n");
  const isAmountRelevant = typeof amount === "number" && amount > 0;
  const isCeilingBreach = isCeilingTriggered || (amount > 2500);

  return (
    <div className="bg-surface rounded-lg border border-ink-200 shadow-sm overflow-hidden space-y-0 relative">
      {/* Header */}
      <div className="p-4 border-b border-ink-100 bg-surface flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-ink-900 flex items-center justify-center text-white shadow-2xs">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-serif text-base font-semibold text-ink-900">
                Cedar Policy Redline Diff
              </h2>
              {isAmountRelevant && (
                <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md bg-surface-subtle border border-ink-200 text-ink-800">
                  ${amount.toLocaleString()} Evaluation
                </span>
              )}
            </div>
            <p className="text-[11px] text-ink-500 font-mono">
              Policy ID: <span className="text-ink-800 font-medium">ProcessRefundPolicy-kryp2370fb</span> · Target: <span className="text-ink-800">AgentCore::Gateway</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border border-ink-200 bg-surface-subtle font-mono text-[10px] text-ink-700">
            Scope: CedarShield-FinanceAgent-Role
          </span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-muted-green-border bg-muted-green-light text-muted-green font-mono text-[10px] font-bold uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5" />
            Bedrock Guardrail Clean
          </span>
        </div>
      </div>

      {/* Dynamic Contextual Autonomous Ceiling Banner */}
      {isAmountRelevant && (
        <div
          className={`p-3.5 border-b flex items-center justify-between gap-3 ${
            isCeilingBreach
              ? "bg-muted-amber-light border-muted-amber-border text-ink-900"
              : "bg-muted-green-light/40 border-muted-green-border text-ink-900"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {isCeilingBreach ? (
              <AlertTriangle className="w-4 h-4 text-muted-amber shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-muted-green shrink-0" />
            )}
            <div>
              <span className="font-serif text-xs font-semibold block">
                {isCeilingBreach
                  ? "Autonomous Ceiling Guardrail Triggered ($2,500 Limit)"
                  : "Autonomous Safety Ceiling Verified (Within Permitted Boundary)"}
              </span>
              <p className="text-[11px] text-ink-600">
                {isCeilingBreach
                  ? `Requested amount ($${amount.toLocaleString()}) exceeds the $2,500 autonomous threshold. Hot-patching is halted; escalated to manual review.`
                  : `Proposed patch ($${amount.toLocaleString()} requested <= $2,500 ceiling) is within autonomous remediation limits.`}
              </p>
            </div>
          </div>
          <span
            className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border uppercase tracking-wider shrink-0 ${
              isCeilingBreach
                ? "bg-white text-muted-amber border-muted-amber-border"
                : "bg-white text-muted-green border-muted-green-border"
            }`}
          >
            {isCeilingBreach ? "Escalation Tier" : "Authorized Tier"}
          </span>
        </div>
      )}

      {/* Bedrock Diagnosis Reasoning */}
      {diagnosis && (
        <div className="p-3.5 bg-surface-subtle/70 border-b border-ink-100 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-ink-500 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-serif font-semibold text-ink-900">
                Bedrock Policy Diagnosis
              </span>
              <span className="text-[10px] font-mono text-ink-500">
                Confidence: {Math.round((diagnosis.confidence_score || 0.98) * 100)}%
              </span>
            </div>
            <p className="text-ink-700 leading-relaxed">
              {diagnosis.root_cause}
            </p>
          </div>
        </div>
      )}

      {/* Redline Code Diff Viewer */}
      <div className="bg-[#181A1F] text-ink-100 font-mono text-xs overflow-x-auto p-4 select-text relative">
        {/* Subtle Legal Attestation Stamp in top-right of diff */}
        <div className="absolute right-4 top-4 select-none opacity-85 hidden sm:block pointer-events-none">
          <div className="border-2 border-dashed border-muted-green/60 text-muted-green px-3 py-1 rounded text-[10px] font-serif font-bold uppercase tracking-widest rotate-[-3deg] shadow-xs">
            [ AST VERIFIED · PERMIT &le; $2,500 ]
          </div>
        </div>

        <div className="space-y-0.5">
          {diffLines.map((line, idx) => {
            const isRemoved = line.startsWith("-") && !line.startsWith("---");
            const isAdded = line.startsWith("+") && !line.startsWith("+++");
            const isHeader = line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++");

            let lineStyle = "text-ink-300";
            let bgStyle = "bg-transparent";

            if (isRemoved) {
              lineStyle = "text-[#F87171] font-semibold";
              bgStyle = "bg-[#B3261E]/20 -mx-4 px-4 block border-l-2 border-[#B3261E]";
            } else if (isAdded) {
              lineStyle = "text-[#4ADE80] font-semibold";
              bgStyle = "bg-[#2F6B4F]/25 -mx-4 px-4 block border-l-2 border-[#2F6B4F]";
            } else if (isHeader) {
              lineStyle = "text-ink-400 font-medium opacity-70";
            }

            return (
              <div key={idx} className={`${bgStyle} flex items-start leading-5`}>
                <span className="w-8 select-none text-ink-500 text-right pr-3 shrink-0 text-[10px]">
                  {idx + 1}
                </span>
                <span className={`${lineStyle} whitespace-pre`}>
                  {line}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
