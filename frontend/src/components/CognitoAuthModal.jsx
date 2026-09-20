import React, { useState } from "react";
import { Lock, X, CheckCircle2, AlertCircle, Loader2, ShieldCheck, Key } from "lucide-react";
import { authenticateCognitoUser, COGNITO_CONFIG } from "../services/api";

export default function CognitoAuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [username, setUsername] = useState("security-reviewer@example.com");
  const [password, setPassword] = useState("ReviewerPass#2026!Sec");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successData, setSuccessData] = useState(null);

  if (!isOpen) return null;

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
      setError(err.message || "Failed to authenticate with Amazon Cognito");
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
                Security Reviewer Authentication
              </h3>
              <p className="text-[11px] text-ink-500">
                Amazon Cognito User Pool ({COGNITO_CONFIG.region})
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

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-surface-subtle p-3 rounded-md border border-ink-200 text-xs text-ink-600 space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-ink-800">
              <ShieldCheck className="w-3.5 h-3.5 text-muted-green" />
              <span>Cognito JWT Protected Governance</span>
            </div>
            <p className="text-[11px] text-ink-500">
              Policy approval and rejection routes require a verified Cognito identity token to guarantee non-repudiation in the audit log.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-muted-red-light border border-muted-red-border rounded-md text-xs text-muted-red">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Authentication failed</p>
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
                  Token generated · Session valid for 1 hour
                </p>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-ink-700 mb-1">
              Email Address / Username
            </label>
            <input
              type="email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 text-xs rounded border border-ink-300 focus:outline-hidden focus:border-ink-800 bg-surface text-ink-900 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
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
              ) : successData ? (
                <span>Success</span>
              ) : (
                <>
                  <Key className="w-3.5 h-3.5" />
                  <span>Authenticate Session</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
