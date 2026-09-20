import React, { useState, useEffect } from "react";
import { Users, ShieldAlert, Sparkles, Clock, Database, RefreshCw } from "lucide-react";
import { fetchKpis } from "../services/api";

export default function KpiStrip() {
  const [kpis, setKpis] = useState({
    active_agents: 2,
    policy_violations: 3,
    auto_remediable: 2,
    pending_approval: 1,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [lastSync, setLastSync] = useState(new Date().toLocaleTimeString());

  const loadKpis = async () => {
    setIsLoading(true);
    try {
      const data = await fetchKpis();
      if (data) {
        setKpis(data);
        setLastSync(new Date().toLocaleTimeString());
      }
    } catch (e) {
      console.warn("KPI load notice:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadKpis();
  }, []);

  const items = [
    {
      id: "agents",
      label: "Active Agents",
      value: kpis.active_agents,
      sub: "FinanceAgent, SupportAgent",
      icon: Users,
      color: "text-ink-900",
      accent: "border-ink-200",
    },
    {
      id: "violations",
      label: "Policy Violations",
      value: kpis.policy_violations,
      sub: "Live -32002 gateway captures",
      icon: ShieldAlert,
      color: "text-muted-red",
      accent: "border-muted-red-border/60",
    },
    {
      id: "remediable",
      label: "Auto-Remediable",
      value: kpis.auto_remediable,
      sub: "Under $2,500 safety ceiling",
      icon: Sparkles,
      color: "text-muted-green",
      accent: "border-muted-green-border/60",
    },
    {
      id: "pending",
      label: "Pending Approval",
      value: kpis.pending_approval,
      sub: "Cognito reviewer sign-off",
      icon: Clock,
      color: "text-muted-amber",
      accent: "border-muted-amber-border/60",
    },
  ];

  return (
    <div className="bg-surface rounded-lg border border-ink-200 p-3 shadow-xs">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-ink-100 text-[10px] font-mono text-ink-500">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-muted-green" />
          <span>DynamoDB Live Telemetry (<span className="text-ink-800 font-semibold">cedarshield-audit-log</span>)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-muted-green animate-pulse" />
          <span>Synced: {lastSync}</span>
          <button
            onClick={loadKpis}
            title="Refresh Live DynamoDB Metrics"
            className="p-0.5 rounded hover:bg-ink-100 text-ink-400 hover:text-ink-800 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              className={`p-2.5 rounded-md bg-surface-subtle border ${item.accent} flex items-center justify-between`}
            >
              <div>
                <span className="text-[10px] font-mono uppercase text-ink-500 font-medium block">
                  {item.label}
                </span>
                <span className={`font-serif text-2xl font-bold tracking-tight ${item.color}`}>
                  {item.value}
                </span>
                <span className="text-[9px] font-mono text-ink-400 block truncate">
                  {item.sub}
                </span>
              </div>
              <div className="w-7 h-7 rounded bg-surface border border-ink-100 flex items-center justify-center text-ink-500 shadow-2xs">
                <Icon className="w-4 h-4" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
