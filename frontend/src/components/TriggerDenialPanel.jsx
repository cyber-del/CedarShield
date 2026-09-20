import React, { useState } from "react";
import { Play, ShieldAlert, AlertOctagon, UserX, Loader2, Sparkles, ShieldX, Check, Sliders } from "lucide-react";

const PRESETS = [
  {
    id: "vip_refund",
    title: "VIP Priority Refund",
    role: "CedarShield-FinanceAgent-Role",
    action: "process-refund",
    reason: "VIP customer priority refund request",
    forceFail: false,
    description: "Exceeds $500 baseline policy, but safely within the $2,500 autonomous ceiling.",
    icon: Sparkles,
  },
  {
    id: "enterprise_ceiling",
    title: "Enterprise Dispute",
    role: "CedarShield-FinanceAgent-Role",
    action: "process-refund",
    reason: "High-value enterprise billing dispute adjustment",
    forceFail: true,
    description: "Exceeds the $2,500 autonomous ceiling. Guardrail halts auto-patch and escalates to reviewer.",
    icon: AlertOctagon,
  },
  {
    id: "role_mismatch",
    title: "Privilege Escalation",
    role: "CedarShield-SupportAgent-Role",
    action: "delete-resource",
    reason: "Support agent attempting administrative resource deletion",
    forceFail: true,
    description: "Role mismatch boundary. System detects non-remediable action escalation and denies unconditionally.",
    icon: UserX,
  },
];

export default function TriggerDenialPanel({ onTrigger, isExecuting }) {
  const [selectedPreset, setSelectedPreset] = useState("vip_refund");
  const [amounts, setAmounts] = useState({
    vip_refund: 2000,
    enterprise_ceiling: 5000,
    role_mismatch: 0,
  });
  const [customReason, setCustomReason] = useState("VIP customer priority refund request");

  const handleSelectPreset = (id) => {
    setSelectedPreset(id);
    const p = PRESETS.find((item) => item.id === id);
    if (p) setCustomReason(p.reason);
  };

  const handleSliderChange = (id, newAmount) => {
    setSelectedPreset(id);
    setAmounts((prev) => ({ ...prev, [id]: newAmount }));
  };

  const handleExecute = () => {
    const active = PRESETS.find((p) => p.id === selectedPreset);
    if (!active) return;

    const amount = amounts[active.id];
    const isCeilingBreached = amount > 2500 || active.id === "role_mismatch";

    onTrigger({
      principal: `arn:aws:iam::097935663941:role/${active.role}`,
      action: active.action,
      amount: amount,
      reason: customReason,
      force_fail: isCeilingBreached,
      presetId: active.id,
    });
  };

  return (
    <div className="bg-surface rounded-lg border border-ink-200 shadow-xs overflow-hidden">
      {/* Header with Production AWS Telemetry & Serious Live Action Trigger */}
      <div className="p-5 border-b border-ink-100 flex flex-wrap items-center justify-between gap-4 bg-surface">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-base font-bold text-ink-900">
              Agent Operation Simulation & Policy Dispatch
            </h2>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-muted-red-light text-muted-red border border-muted-red-border">
              <span className="w-1.5 h-1.5 rounded-full bg-muted-red animate-pulse" />
              LIVE AWS INFRASTRUCTURE
            </span>
          </div>
          <p className="text-xs text-ink-500 font-mono">
            Directly invokes Amazon Bedrock AgentCore Gateway <span className="text-ink-800 font-semibold">(Mode: ENFORCE)</span> in <span className="text-ink-800 font-semibold">ap-southeast-2</span>
          </p>
        </div>

        {/* High-Gravity Live Execution Trigger */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col text-right font-mono text-[10px] text-ink-500">
            <span className="text-ink-700 font-semibold">Target: MCP /tools/call</span>
            <span>SigV4 Assumed Role Auth</span>
          </div>

          <button
            onClick={handleExecute}
            disabled={isExecuting}
            className={`inline-flex items-center gap-2.5 px-6 py-3 rounded-lg text-xs font-mono font-bold transition-all ${
              isExecuting
                ? "bg-surface-subtle text-ink-600 border border-ink-300 opacity-75 cursor-not-allowed pointer-events-none shadow-none ring-0 select-none animate-pulse"
                : "bg-ink-900 hover:bg-black text-white shadow-md hover:ring-2 hover:ring-muted-red/50 hover:shadow-lg active:scale-[0.98] cursor-pointer"
            }`}
          >
            {isExecuting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-ink-500" />
                <span className="text-ink-700">Invoking Live Gateway...</span>
              </>
            ) : (
              <>
                <ShieldAlert className="w-4 h-4 text-muted-red" />
                <span>Execute Live Denial</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-white/20 text-white uppercase tracking-wider font-semibold">
                  LIVE
                </span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3 Interactive Scenario Cards */}
      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        {PRESETS.map((p) => {
          const isSelected = selectedPreset === p.id;
          const Icon = p.icon;
          const currentAmount = amounts[p.id];
          const isRefund = p.id !== "role_mismatch";
          const isBreached = currentAmount > 2500;

          // Decision Status Dominance
          let outcomeText = "AUTO-REMEDIABLE";
          let outcomeBadge = "bg-muted-green text-white";
          let outcomeBorder = isSelected ? "border-muted-green" : "border-muted-green/40";
          let outcomeSub = "Under $2,500 safety ceiling";
          let riskLevelColor = "text-muted-green";

          if (p.id === "role_mismatch") {
            outcomeText = "BLOCKED";
            outcomeBadge = "bg-muted-red text-white";
            outcomeBorder = isSelected ? "border-muted-red" : "border-muted-red/40";
            outcomeSub = "Role isolation boundary failure";
            riskLevelColor = "text-muted-red";
          } else if (isBreached) {
            outcomeText = "MANUAL REVIEW";
            outcomeBadge = "bg-muted-amber text-white";
            outcomeBorder = isSelected ? "border-muted-amber" : "border-muted-amber/40";
            outcomeSub = `Ceiling exceeded (+$${(currentAmount - 2500).toLocaleString()})`;
            riskLevelColor = "text-muted-amber";
          }

          return (
            <div
              key={p.id}
              onClick={() => handleSelectPreset(p.id)}
              className={`cursor-pointer rounded-lg p-4 border transition-colors duration-150 flex flex-col justify-between ${
                isSelected
                  ? "border-ink-900 bg-surface shadow-md ring-2 ring-ink-900/25"
                  : "border-ink-200 bg-surface hover:border-ink-400"
              }`}
            >
              <div>
                {/* Hero Decision / Outcome Header (Visually Dominant) */}
                <div className="flex items-start justify-between gap-2 pb-3 mb-2.5 border-b border-ink-100">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[11px] font-mono font-bold tracking-wider px-2 py-0.5 rounded shadow-2xs ${outcomeBadge}`}>
                        {outcomeText}
                      </span>
                      <span className="text-[10px] font-mono text-ink-500">
                        {outcomeSub}
                      </span>
                    </div>
                    {/* Scenario Title & Target Action */}
                    <h3 className="font-serif text-sm font-semibold text-ink-900 mt-1.5 flex items-center gap-1.5">
                      <span>{p.title}</span>
                    </h3>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {isSelected && (
                      <span className="w-2 h-2 rounded-full bg-ink-900" title="Selected scenario" />
                    )}
                    <div className={`p-1 rounded ${isSelected ? "text-ink-900 bg-ink-100" : "text-ink-400"}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>
                </div>

                {/* Requested Amount Display */}
                <div className="my-1">
                  <div className="flex items-baseline gap-2">
                    <span className={`font-serif text-2xl font-bold tracking-tight transition-colors duration-150 ${
                      p.id === "role_mismatch" ? "text-muted-red" : isBreached ? "text-muted-amber" : "text-ink-900"
                    }`}>
                      {isRefund ? `$${currentAmount.toLocaleString()}` : "ADMIN OP"}
                    </span>
                    {isRefund && (
                      <span className="text-[11px] font-mono text-ink-400">
                        USD Live Requested
                      </span>
                    )}
                  </div>
                </div>

                {/* Live Draggable Slider & Risk Meter for Refunds */}
                {isRefund ? (
                  <div className="my-2.5 p-2.5 rounded-md bg-surface-subtle border border-ink-100 space-y-2">
                    {/* Header Labels */}
                    <div className="flex justify-between items-center text-[10px] font-mono">
                      <span className="text-ink-500">$500 Base</span>
                      <span className="font-bold text-ink-800 bg-surface px-1.5 py-0.2 rounded border border-ink-200 shadow-2xs">
                        Ceiling: $2,500
                      </span>
                      <span className="text-muted-amber font-semibold">Breach Zone</span>
                    </div>

                    {/* Visual Progress Track (Scale: $0 to $6,000, $2,500 Ceiling at 42%) */}
                    <div className="w-full bg-ink-200 h-3 rounded-md relative overflow-hidden flex">
                      {/* Left Permitted Zone (0 to 42% -> $2,500) */}
                      <div className="w-[42%] h-full relative bg-ink-200 border-r-2 border-dashed border-ink-600">
                        <div className="absolute left-[20%] top-0 bottom-0 w-0.5 bg-ink-300" title="Base: $500" />
                        
                        {/* Safe Fill Bar - instant width without transition queue delay */}
                        <div 
                          className="h-full bg-muted-green rounded-l-md"
                          style={{ width: `${Math.min(100, (currentAmount / 2500) * 100)}%` }}
                        />
                      </div>

                      {/* Right Overflow / Breach Zone (42% to 100%) */}
                      <div className="w-[58%] h-full relative bg-muted-amber-light/30">
                        {isBreached && (
                          <div 
                            className="h-full bg-muted-amber rounded-r-md relative overflow-hidden"
                            style={{ width: `${Math.min(100, ((currentAmount - 2500) / 3500) * 100)}%` }}
                          >
                            <div className="absolute inset-0 bg-repeating-linear-stripes opacity-40 animate-pulse" />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Live Draggable Range Slider */}
                    <div className="pt-1" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-between text-[10px] font-mono text-ink-400 mb-1">
                        <span>$100</span>
                        <span className="flex items-center gap-1 text-ink-700 font-semibold">
                          <Sliders className="w-3 h-3 text-ink-500" />
                          <span>Drag to test ceiling</span>
                        </span>
                        <span>$6,000</span>
                      </div>
                      <input
                        type="range"
                        min="100"
                        max="6000"
                        step="50"
                        value={currentAmount}
                        onChange={(e) => handleSliderChange(p.id, parseInt(e.target.value))}
                        className="w-full h-1.5 bg-ink-200 rounded-lg appearance-none cursor-pointer accent-ink-900 focus:outline-hidden"
                      />
                    </div>

                    {/* Bottom Status Indicator */}
                    <div className="flex justify-between items-center text-[10px] pt-0.5">
                      <span className={`font-mono font-semibold transition-colors ${
                        isBreached ? "text-muted-amber" : "text-muted-green"
                      }`}>
                        {isBreached 
                          ? `▲ OVERFLOW: +$${(currentAmount - 2500).toLocaleString()} Past Ceiling` 
                          : `● Within Auto Limit ($${currentAmount.toLocaleString()} <= $2,500)`}
                      </span>
                      <span className="text-[10px] text-ink-500 font-mono">
                        {isBreached ? "Manual Review" : "Auto-Remediable"}
                      </span>
                    </div>
                  </div>
                ) : (
                  /* Visual Role-Boundary Barrier for Privilege Escalation */
                  <div className="my-3 p-2.5 rounded-md bg-muted-red-light/30 border border-muted-red-border/60 flex items-center justify-between text-[11px] font-mono">
                    <div className="flex items-center gap-1.5 text-muted-red">
                      <ShieldX className="w-4 h-4 shrink-0" />
                      <span className="font-medium">SupportAgent ⊘ delete_resource</span>
                    </div>
                    <span className="text-[10px] font-semibold text-muted-red bg-white px-1.5 py-0.5 rounded border border-muted-red-border">
                      FORBIDDEN
                    </span>
                  </div>
                )}

                <p className="text-xs text-ink-500 leading-snug">
                  {p.description}
                </p>
              </div>

              {/* Card Footer Details */}
              <div className="pt-2.5 mt-3 border-t border-ink-100 flex items-center justify-between text-[11px] font-mono text-ink-600">
                <span className="text-ink-400 font-sans">Role: <span className="text-ink-700 font-mono">{p.role.split("-")[1]}</span></span>
                <span className="text-ink-400 font-sans">Action: <span className="text-ink-700 font-mono">{p.action}</span></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
