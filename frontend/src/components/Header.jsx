import React, { useState, useEffect } from "react";
import { Shield, UserCheck, LogOut, Key, Layers, Workflow, CheckCircle2 } from "lucide-react";
import { fetchAuditLog } from "../services/api";

export default function Header({ activeTab, setActiveTab, session, onOpenAuthModal, onLogout }) {
  const [isLive, setIsLive] = useState(true);

  // Lightweight live connectivity check on demand when history tab is active
  useEffect(() => {
    if (activeTab !== "history") return;
    const checkConnectivity = async () => {
      try {
        await fetchAuditLog();
        setIsLive(true);
      } catch {
        setIsLive(false);
      }
    };
    checkConnectivity();
    const interval = setInterval(checkConnectivity, 30000);
    return () => clearInterval(interval);
  }, [activeTab]);

  return (
    <header className="border-b border-ink-200 bg-surface/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Project Identity */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-ink-900 text-white flex items-center justify-center shadow-sm">
              <Shield className="w-5 h-5 text-surface" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-lg font-semibold tracking-tight text-ink-900">
                  CedarShield
                </span>
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-ink-200 bg-surface-subtle text-ink-600 font-mono text-xs">
                  <span className={`w-2 h-2 rounded-full ${isLive ? "bg-muted-green animate-pulse" : "bg-muted-amber"}`} />
                  <span className="text-[10px] font-semibold text-muted-green tracking-wider">LIVE</span>
                  <span className="text-ink-300">·</span>
                  <span>ap-southeast-2</span>
                </div>
              </div>
              <p className="text-xs text-ink-500 hidden sm:block">
                Autonomous policy remediation & tamper-evident audit
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-surface-subtle p-1 rounded-lg border border-ink-200 text-xs font-medium">
            <button
              onClick={() => setActiveTab("simulate")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === "simulate"
                  ? "bg-surface text-ink-900 shadow-xs font-semibold"
                  : "text-ink-600 hover:text-ink-900"
              }`}
            >
              Simulate & Remediate
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === "history"
                  ? "bg-surface text-ink-900 shadow-xs font-semibold"
                  : "text-ink-600 hover:text-ink-900"
              }`}
            >
              Audit Case History
            </button>
            <button
              onClick={() => setActiveTab("architecture")}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === "architecture"
                  ? "bg-surface text-ink-900 shadow-xs font-semibold"
                  : "text-ink-600 hover:text-ink-900"
              }`}
            >
              Architecture
            </button>
          </nav>

          {/* Cognito Authentication Bar */}
          <div className="flex items-center gap-2">
            {session ? (
              <div className="flex items-center gap-2 bg-muted-green-light border border-muted-green-border px-3 py-1.5 rounded-md text-xs">
                <UserCheck className="w-3.5 h-3.5 text-muted-green" />
                <div className="flex flex-col text-left">
                  <span className="font-medium text-muted-green max-w-[150px] truncate">
                    {session.email}
                  </span>
                  <span className="text-[10px] text-ink-500 font-mono">
                    sub: {session.sub?.slice(0, 8)}...
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  title="Sign out from Cognito session"
                  className="ml-1 p-1 text-ink-400 hover:text-muted-red transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuthModal}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-ink-900 text-white hover:bg-ink-800 transition-colors shadow-xs"
              >
                <Key className="w-3.5 h-3.5" />
                <span>Sign in (Cognito)</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
