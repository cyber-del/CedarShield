import React, { useState } from "react";
import { Check, X, Lock, ShieldCheck, Loader2, AlertCircle, AlertTriangle, FileSignature, CheckCircle2, ArrowRight, XCircle } from "lucide-react";

export default function ReviewActionPanel({
  runId,
  session,
  isProcessing,
  pipelineStatus,
  onApprove,
  onReject,
  onOpenAuthModal,
  onViewAuditHistory,
  isCeilingBlocked,
}) {
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);

  const isApproved = pipelineStatus === "approved";
  const isRejected = pipelineStatus === "rejected";

  const handleApprove = () => {
    if (!session) {
      onOpenAuthModal();
      return;
    }
    onApprove(runId);
  };

  const handleReject = () => {
    if (!session) {
      onOpenAuthModal();
      return;
    }
    if (!showRejectInput) {
      setShowRejectInput(true);
      return;
    }
    onReject(runId, rejectReason || "Human reviewer rejected policy adjustment.");
  };

  return (
    <div className={`rounded-lg border p-5 shadow-xs relative overflow-hidden transition-all ${
      isApproved
        ? "bg-muted-green-light/40 border-muted-green-border"
        : isRejected
        ? "bg-muted-red-light/40 border-muted-red-border"
        : "bg-surface border-ink-200"
    }`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-serif text-base font-semibold text-ink-900">
              Security Governance Authorization
            </h3>
            {isApproved ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-muted-green-light text-muted-green border border-muted-green-border font-mono font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                POLICY PATCH APPLIED & ENFORCED
              </span>
            ) : isRejected ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-muted-red-light text-muted-red border border-muted-red-border font-mono font-semibold">
                <XCircle className="w-3.5 h-3.5" />
                POLICY REJECTED & ARCHIVED
              </span>
            ) : session ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-muted-green-light text-muted-green border border-muted-green-border">
                <ShieldCheck className="w-3.5 h-3.5" />
                Cognito Authenticated Signer
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-muted-amber-light text-muted-amber border border-muted-amber-border">
                <Lock className="w-3.5 h-3.5" />
                Cognito Authentication Required
              </span>
            )}
          </div>
          <p className="text-xs text-ink-500">
            {isApproved
              ? `Decision cryptographically signed by ${session?.email || "security-reviewer@example.com"} and anchored in DynamoDB SHA-256 Merkle chain.`
              : isRejected
              ? `Rejection recorded in audit history. No policy changes applied to AgentCore engine.`
              : session
              ? `Decision will be cryptographically bound to ${session.email} in the DynamoDB tamper-evident audit ledger.`
              : "Approve and Reject actions are protected. Sign in with your verified Cognito security reviewer credentials."}
          </p>
        </div>

        {/* Action Controls & Sign-off Stamp */}
        <div className="flex items-center gap-3 shrink-0">
          {isApproved ? (
            <div className="flex items-center gap-2">
              <div className="px-3.5 py-2 rounded-md bg-muted-green text-white text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs">
                <Check className="w-4 h-4" />
                <span>Patch Live on Gateway</span>
              </div>
              <button
                onClick={onViewAuditHistory}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink-900 hover:bg-ink-800 text-white rounded-md text-xs font-semibold transition-all shadow-xs hover:shadow-md"
              >
                <span>View Audit Log & Rollback</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : isRejected ? (
            <div className="flex items-center gap-2">
              <div className="px-3.5 py-2 rounded-md bg-muted-red text-white text-xs font-semibold inline-flex items-center gap-1.5 shadow-xs">
                <X className="w-4 h-4" />
                <span>Rejected</span>
              </div>
              <button
                onClick={onViewAuditHistory}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink-900 hover:bg-ink-800 text-white rounded-md text-xs font-semibold transition-all shadow-xs hover:shadow-md"
              >
                <span>View in Audit History</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : !session ? (
            <button
              onClick={onOpenAuthModal}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-ink-900 hover:bg-ink-800 text-white rounded-md text-xs font-semibold transition-all shadow-xs hover:shadow-md"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Sign in to Unlock Governance</span>
            </button>
          ) : (
            <>
              {showRejectInput ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Reason for rejection..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="px-3 py-1.5 text-xs rounded border border-ink-300 focus:outline-hidden focus:border-ink-800 font-sans w-56 text-ink-900"
                  />
                  <button
                    onClick={handleReject}
                    disabled={isProcessing}
                    className="px-3.5 py-1.5 bg-muted-red hover:bg-red-800 text-white rounded text-xs font-semibold transition-colors shadow-xs disabled:opacity-50"
                  >
                    Confirm Rejection
                  </button>
                  <button
                    onClick={() => setShowRejectInput(false)}
                    className="px-2 py-1.5 text-xs text-ink-500 hover:text-ink-700"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleReject}
                  disabled={isProcessing}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-muted-red-border text-muted-red hover:bg-muted-red-light rounded-md text-xs font-medium transition-colors shadow-2xs disabled:opacity-50"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject Patch</span>
                </button>
              )}

              <button
                onClick={handleApprove}
                disabled={isProcessing || isCeilingBlocked}
                className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-md text-xs font-semibold text-white transition-all shadow-xs hover:shadow-md ${
                  isCeilingBlocked
                    ? "bg-ink-400 cursor-not-allowed opacity-60"
                    : "bg-muted-green hover:bg-[#255740] active:scale-[0.99]"
                }`}
                title={isCeilingBlocked ? "Cannot auto-approve: Autonomous ceiling exceeded" : "Approve & Commit Patch to AgentCore"}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Signing & Applying...</span>
                  </>
                ) : (
                  <>
                    <FileSignature className="w-4 h-4" />
                    <span>Approve & Apply Scoped Patch</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

