import React, { useState } from "react";
import { Lock, X, CheckCircle2, AlertCircle, Loader2, ShieldCheck, Key, Shield, Sparkles } from "lucide-react";
import { authenticateCognitoUser, COGNITO_CONFIG, createSyntheticSession } from "../services/api";

export default function CognitoAuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successData, setSuccessData] = useState(null);
  const [activeTab, setActiveTab] = useState("sandbox"); // "sandbox" | "custom"

  if (!isOpen) return null;

  const handleUseSandbox = () => {
    setLoading(true);
    setError(null);
    try {
      const session = createSyntheticSession();
      setSuccessData(session);
      setTimeout(() => {
        onAuthSuccess(session);
        onClose();
        setSuccessData(null);
      }, 700);
    } catch (err) {
      setError(err.message || "Failed to initialize sandbox reviewer session");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const session = await authenticateCognitoUser(username, password);
      setSuccessData(session);
      setTimeout(() => {
        onAuthSuccess(session);
        onClose();
        setSuccessData(null);
      }, 1000);
    } catch (err) {
      setError(err.message || "Failed to authenticate with Amazon Cognito. Check credentials or use Safe Sandbox mode.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 backdrop-blur-xs p-4">
      <div className="bg-surface rounded-lg shadow-xl border border-ink-200 max-w-md w-full overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-ink-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-ink-100 flex items-center justify-center text-ink-800">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-serif font-semibold text-ink-900 text-sm">
                Security Reviewer Governance
              </h3>
              <p className="text-[11px] text-ink-500">
                Cognito JWT Non-Repudiation · Zero Shared Secrets
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ink-400 hover:text-ink-600 p-1 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-ink-100 bg-surface-subtle text-xs">
          <button
            onClick={() => setActiveTab("sandbox")}
            className={`flex-1 py-2.5 px-3 text-center font-medium border-b-2 transition-colors flex items-center justify-center gap-1.5 ${
              activeTab === "sandbox"
                ? "border-ink-900 text-ink-900 bg-surface font-semibold"
                : "border-transparent text-ink-500 hover:text-ink-700"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-muted-green" />
            <span>Safe Sandbox Mode (Recommended)</span>
          </button>
          <button
            onClick={() => setActiveTab("custom")}
            className={`flex-1 py-2.5 px-3 text-center font-medium border-b-2 transition-colors flex items-center justify-center gap-1.5 ${
              activeTab === "custom"
                ? "border-ink-900 text-ink-900 bg-surface font-semibold"
                : "border-transparent text-ink-500 hover:text-ink-700"
            }`}
          >
            <Shield className="w-3.5 h-3.5 text-ink-500" />
            <span>Dedicated AWS Cognito</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2 p-3 bg-muted-red-light border border-muted-red-border rounded-md text-xs text-muted-red">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Authentication Notice</p>
                <p className="text-[11px]">{error}</p>
              </div>
            </div>
          )}

          {successData && (
            <div className="flex items-center gap-2 p-3 bg-muted-green-light border border-muted-green-border rounded-md text-xs text-muted-green">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <div>
                <p className="font-semibold">Authenticated as {successData.email}</p>
                <p className="text-[10px] text-ink-500 font-mono">
                  Cryptographic session initialized · Zero Live Credential Exposure
                </p>
              </div>
            </div>
          )}

          {activeTab === "sandbox" ? (
            <div className="space-y-4">
              <div className="bg-surface-subtle p-3.5 rounded-md border border-ink-200 text-xs text-ink-700 space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-ink-900">
                  <ShieldCheck className="w-4 h-4 text-muted-green" />
                  <span>Isolated Synthetic Reviewer Sandbox</span>
                </div>
                <p className="text-[11px] text-ink-600 leading-relaxed">
                  Evaluates the full policy remediation, adversarial boundary matrix, and DynamoDB SHA-256 Merkle chain without exposing or requiring live AWS credentials.
                </p>
                <ul className="text-[11px] text-ink-500 space-y-1 list-disc list-inside">
                  <li>Full compliance audit chain validation enabled</li>
                  <li>Zero live AWS Bedrock billable execution risk</li>
                  <li>Deterministic cryptographic Merkle ledger hashing</li>
                </ul>
              </div>

              <button
                type="button"
                onClick={handleUseSandbox}
                disabled={loading || !!successData}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold bg-ink-900 text-white hover:bg-ink-800 rounded-md transition-colors shadow-xs disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Initializing Sandbox...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Enter Safe Sandbox as Verified Reviewer</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="bg-surface-subtle p-3 rounded-md border border-ink-200 text-xs text-ink-600 space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-ink-800">
                  <Lock className="w-3.5 h-3.5 text-ink-600" />
                  <span>Dedicated Production User Pool</span>
                </div>
                <p className="text-[11px] text-ink-500">
                  Connect to your organization's Amazon Cognito User Pool. Dedicated credentials provided upon request to verified security reviewers.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-700 mb-1">
                  Reviewer Email / Identity
                </label>
                <input
                  type="email"
                  value={username}
                  placeholder="reviewer@your-enterprise.com"
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded border border-ink-300 focus:outline-hidden focus:border-ink-800 bg-surface text-ink-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-700 mb-1">
                  Cognito Password
                </label>
                <input
                  type="password"
                  value={password}
                  placeholder="••••••••••••"
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded border border-ink-300 focus:outline-hidden focus:border-ink-800 bg-surface text-ink-900 font-mono"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-ink-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3 py-1.5 text-xs font-medium text-ink-600 hover:text-ink-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !!successData}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-ink-900 text-white hover:bg-ink-800 rounded transition-colors disabled:opacity-50 shadow-xs"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <>
                      <Key className="w-3.5 h-3.5" />
                      <span>Authenticate JWT</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
