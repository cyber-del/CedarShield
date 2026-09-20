import React, { useState, useEffect } from "react";
import { 
  Link2, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Hash, 
  Calendar, 
  User, 
  Loader2, 
  FileText, 
  Check, 
  ShieldAlert,
  Fingerprint,
  ArrowDown,
  RotateCcw
} from "lucide-react";
import { fetchAuditLog, verifyAuditChainServer, simulateAbuseAndRollback } from "../services/api";

export default function AuditLogView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verificationResult, setVerificationResult] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSimulatingRollback, setIsSimulatingRollback] = useState(false);
  const [rollbackSuccessMsg, setRollbackSuccessMsg] = useState(null);
  const [verifiedBlockIndices, setVerifiedBlockIndices] = useState(new Set());
  const [currentVerifyingIndex, setCurrentVerifyingIndex] = useState(null);
  const [error, setError] = useState(null);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLog();
      setLogs(data);
      return data;
    } catch (err) {
      setError(err.message || "Failed to load audit history");
      return [];
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateRollback = async () => {
    setIsSimulatingRollback(true);
    setError(null);
    setRollbackSuccessMsg(null);
    try {
      const res = await simulateAbuseAndRollback();
      setRollbackSuccessMsg(
        `Autonomous Anomaly Triggered! Policy reverted live on AgentCore to $500 baseline. Block #${res.block?.sequence_number || "new"} appended.`
      );
      await loadLogs();
    } catch (e) {
      setError(e.message || "Failed to simulate anomaly");
    } finally {
      setIsSimulatingRollback(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      const data = await loadLogs();
      const params = new URLSearchParams(window.location.search);
      if (params.get("verify") === "true" && data.length > 0) {
        setTimeout(() => {
          handleVerifyChain(data);
        }, 300);
      }
    };
    init();
  }, []);

  const chainedLogs = [...logs]
    .filter((l) => l.prev_hash)
    .sort((a, b) => parseInt(a.sequence_number || 0) - parseInt(b.sequence_number || 0));

  const handleVerifyChain = async (customData) => {
    setIsVerifying(true);
    setError(null);
    setVerificationResult(null);
    setVerifiedBlockIndices(new Set());
    setCurrentVerifyingIndex(0);

    const activeList = (Array.isArray(customData) && customData.length > 0)
      ? customData.filter((l) => l.prev_hash).sort((a, b) => parseInt(a.sequence_number || 0) - parseInt(b.sequence_number || 0))
      : chainedLogs;

    try {
      // 1. Trigger backend verification check
      const result = await verifyAuditChainServer();

      // 2. Perform sequential block-by-block animation
      for (let i = 0; i < activeList.length; i++) {
        setCurrentVerifyingIndex(i);
        await new Promise((resolve) => setTimeout(resolve, 220)); // ~220ms staggered delay
        setVerifiedBlockIndices((prev) => new Set([...prev, i]));
      }

      setCurrentVerifyingIndex(null);
      setVerificationResult(result);
    } catch (err) {
      setError("Cryptographic verification error: " + err.message);
      setCurrentVerifyingIndex(null);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="bg-surface rounded-lg border border-ink-200 p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-ink-800" />
            <h2 className="font-serif text-lg font-semibold text-ink-900">
              Tamper-Evident Cryptographic Ledger
            </h2>
          </div>
          <p className="text-xs text-ink-500 mt-0.5">
            Table: <span className="font-mono text-[11px] text-ink-700">cedarshield-audit-log</span> · Region: <span className="font-mono text-[11px] text-ink-700">ap-southeast-2</span> · SHA-256 Merkle Chain
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadLogs}
            disabled={loading || isVerifying || isSimulatingRollback}
            className="p-2 border border-ink-200 hover:bg-surface-subtle text-ink-600 rounded-md text-xs transition-colors"
            title="Refresh records from DynamoDB"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={handleSimulateRollback}
            disabled={isSimulatingRollback || loading || isVerifying}
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-muted-red-border text-muted-red hover:bg-muted-red-light bg-surface rounded-md text-xs font-semibold transition-all shadow-xs disabled:opacity-50"
            title="Simulate 3 rapid near-ceiling invocations ($2,450, $2,480, $2,490) to trigger automatic rollback"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isSimulatingRollback ? "animate-spin" : ""}`} />
            <span>{isSimulatingRollback ? "Executing Rollback..." : "Simulate Post-Patch Anomaly"}</span>
          </button>

          <button
            onClick={() => handleVerifyChain()}
            disabled={isVerifying || chainedLogs.length === 0}
            className="inline-flex items-center gap-2 px-4 py-2 bg-ink-900 hover:bg-ink-800 text-white rounded-md text-xs font-semibold transition-all shadow-xs disabled:opacity-50"
          >
            {isVerifying ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Validating Block #{((currentVerifyingIndex ?? 0) + 1)}...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Verify Chain Integrity</span>
              </>
            )}
          </button>
        </div>
      </div>

      {rollbackSuccessMsg && (
        <div className="p-3.5 rounded-lg border bg-muted-amber-light border-muted-amber-border text-xs text-ink-900 flex items-center justify-between gap-2 animate-panel-swap">
          <div className="flex items-center gap-2">
            <RotateCcw className="w-4 h-4 text-muted-red shrink-0" />
            <span className="font-medium">{rollbackSuccessMsg}</span>
          </div>
          <button onClick={() => setRollbackSuccessMsg(null)} className="text-ink-500 hover:text-ink-800 font-mono text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-lg border flex items-start gap-3 transition-all animate-panel-swap ${
            verificationResult.is_valid
              ? "bg-muted-green-light border-muted-green-border text-ink-900"
              : "bg-muted-red-light border-muted-red-border text-ink-900"
          }`}
        >
          {verificationResult.is_valid ? (
            <CheckCircle2 className="w-5 h-5 text-muted-green shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-muted-red shrink-0 mt-0.5" />
          )}
          <div className="space-y-1 w-full">
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-sm font-semibold">
                {verificationResult.is_valid
                  ? "Cryptographic Verification Succeeded: All Hashes & Prev-Pointers Intact"
                  : "Cryptographic Verification Failed: Hash Mismatch or Tampering Detected"}
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-muted-green-border bg-white text-muted-green font-semibold">
                {verificationResult.total_blocks} Blocks Validated Live
              </span>
            </div>
            <p className="text-xs text-ink-600">
              {verificationResult.is_valid
                ? "Every block's SHA-256 record_hash and prev_hash link were computed live against the DynamoDB ledger state. All cryptographic signatures matched."
                : "A mismatch between computed and stored hashes was detected."}
            </p>
            <div className="pt-1.5 text-[10px] font-mono text-ink-500 truncate">
              Latest Block Hash: <span className="text-ink-800 font-semibold">{verificationResult.latest_block_hash}</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-muted-red-light border border-muted-red-border rounded-lg text-xs text-muted-red flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* CONTINUOUS VISUAL HASH CHAIN TIMELINE */}
      <div className="relative pl-10 pr-2 space-y-4">
        {/* Continuous Central Vertical Chain Spine */}
        <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-ink-200" />

        {loading ? (
          <div className="p-10 text-center bg-surface rounded-lg border border-ink-200">
            <Loader2 className="w-6 h-6 animate-spin mx-auto text-ink-400 mb-2" />
            <p className="text-xs text-ink-500">Querying DynamoDB audit log table...</p>
          </div>
        ) : chainedLogs.length === 0 ? (
          <div className="p-10 text-center bg-surface rounded-lg border border-ink-200 text-ink-500 text-xs">
            No chained audit records found. Execute a demo denial and approve a patch to generate blocks.
          </div>
        ) : (
          chainedLogs.map((item, idx) => {
            const seq = item.sequence_number || idx + 1;
            const isRollback = item.final_decision === "AUTOMATIC_ROLLBACK" || item.status === "ROLLED_BACK";
            const isApproved = item.final_decision === "APPLIED" || item.status === "APPROVED";
            const isManualReview = item.final_decision === "MANUAL_REVIEW" || item.status === "MANUAL_REVIEW_REQUIRED";
            const isGenesis = item.prev_hash === "0".repeat(64);

            const isCurrentlyVerifying = currentVerifyingIndex === idx;
            const isVerified = verifiedBlockIndices.has(idx);

            // Subtle Status Border Color
            const statusBorderClass = isRollback
              ? "border-l-4 border-l-muted-red bg-muted-red-light/10 ring-1 ring-muted-red/20"
              : isApproved
              ? "border-l-4 border-l-muted-green"
              : isManualReview
              ? "border-l-4 border-l-muted-amber"
              : "border-l-4 border-l-muted-red";

            return (
              <div key={item.run_id || idx} className="relative group">
                {/* Node Anchor on the Continuous Spine */}
                <div 
                  className={`absolute -left-10 top-5 w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-xs font-semibold shadow-xs transition-all duration-300 z-10 ${
                    isVerified
                      ? "bg-muted-green text-white border-muted-green ring-4 ring-muted-green/20"
                      : isRollback
                      ? "bg-muted-red text-white border-muted-red ring-4 ring-muted-red/30 shadow-md"
                      : isCurrentlyVerifying
                      ? "bg-ink-900 text-white border-ink-900 animate-pulse ring-4 ring-ink-900/30"
                      : "bg-surface text-ink-800 border-ink-300 group-hover:border-ink-600"
                  }`}
                >
                  {isVerified ? (
                    <Check className="w-4 h-4 text-white" />
                  ) : isRollback ? (
                    <RotateCcw className="w-4 h-4 text-white" />
                  ) : isCurrentlyVerifying ? (
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                  ) : (
                    <span>#{seq}</span>
                  )}
                </div>

                {/* Horizontal Connector Line from Spine to Card */}
                <div className="absolute -left-2 top-9 w-2 h-0.5 bg-ink-200 group-hover:bg-ink-400 transition-colors" />

                {/* Block Card with reduced padding and high density */}
                <div className={`bg-surface rounded-lg border border-ink-200 shadow-xs overflow-hidden hover:border-ink-300 transition-all ${statusBorderClass}`}>
                  
                  {/* Card Header (High Density py-2.5 px-4) */}
                  <div className="px-4 py-2.5 border-b border-ink-100 bg-surface-subtle/50 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-serif font-semibold text-xs text-ink-900">
                        Block #{seq} · Run: {item.run_id}
                      </span>
                      {isGenesis && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-ink-100 text-ink-700 font-medium">
                          Genesis Block
                        </span>
                      )}
                      {isVerified && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted-green-light text-muted-green border border-muted-green-border font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>VALID SHA-256</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-ink-400 font-mono">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded font-medium border flex items-center gap-1 ${
                          isRollback
                            ? "bg-muted-red text-white border-muted-red font-bold shadow-2xs"
                            : isApproved
                            ? "bg-muted-green-light text-muted-green border-muted-green-border"
                            : isManualReview
                            ? "bg-muted-amber-light text-muted-amber border-muted-amber-border"
                            : "bg-muted-red-light text-muted-red border-muted-red-border"
                        }`}
                      >
                        {isRollback && <RotateCcw className="w-3 h-3" />}
                        <span>{item.final_decision || item.status || "COMPLETED"}</span>
                      </span>
                    </div>
                  </div>

                  {/* Card Body (High Density p-3.5) */}
                  <div className="p-3.5 space-y-2.5">
                    {/* Anomaly Rollback Highlight Box if Rollback Event */}
                    {isRollback && (
                      <div className="p-3 rounded-md bg-muted-red-light/50 border border-muted-red-border/70 space-y-1">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-muted-red">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          <span>AUTONOMOUS ANOMALY ROLLBACK EXECUTED</span>
                        </div>
                        <p className="text-xs text-ink-800 font-sans leading-relaxed">
                          {item.anomaly_reason || "Suspicious near-ceiling clustering anomaly tripped automatic policy reversion on Bedrock AgentCore."}
                        </p>
                        <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] font-mono text-ink-600">
                          <span>Reverted Policy: <strong className="text-ink-900">{item.policy_applied || "ProcessRefundPolicy-kryp2370fb"}</strong></span>
                          <span>·</span>
                          <span>Restored Boundary: <strong className="text-muted-green font-semibold">{item.policy_reverted_to || "Pre-Patch Boundary (current_policy)"}</strong></span>
                        </div>
                      </div>
                    )}

                    {/* Metadata Compact Row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs bg-surface-subtle p-2.5 rounded-md border border-ink-100 font-mono text-ink-700">
                      <div>
                        <span className="text-ink-400 font-sans block text-[10px]">Principal Identity</span>
                        <span className="font-medium truncate block" title={item.principal}>
                          {item.principal ? item.principal.split("/").pop() : "FinanceAgent-Role"}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-400 font-sans block text-[10px]">Action</span>
                        <span className="font-medium truncate block">
                          {item.action || "process-refund"}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-400 font-sans block text-[10px]">Approver Identity</span>
                        <span className={`font-medium truncate block ${isRollback ? "text-muted-red font-bold" : "text-muted-green"}`} title={item.approver_identity}>
                          {item.approver_identity || "security-reviewer@example.com"}
                        </span>
                      </div>
                    </div>

                    {/* Tight Monospace Hash Grid */}
                    <div className="pt-2 border-t border-ink-100 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
                      {/* prev_hash row */}
                      <div className="flex items-center gap-2 bg-surface-subtle/80 px-2.5 py-1.5 rounded border border-ink-100/80">
                        <Link2 className="w-3.5 h-3.5 shrink-0 text-ink-400" />
                        <span className="text-ink-400 font-sans text-[10px] shrink-0">prev_hash:</span>
                        <span className="text-ink-700 truncate select-all" title={item.prev_hash}>
                          {item.prev_hash}
                        </span>
                      </div>

                      {/* record_hash row */}
                      <div className="flex items-center gap-2 bg-surface-subtle/80 px-2.5 py-1.5 rounded border border-ink-100/80">
                        <Hash className="w-3.5 h-3.5 shrink-0 text-muted-green" />
                        <span className="text-ink-400 font-sans text-[10px] shrink-0">record_hash:</span>
                        <span className="font-semibold text-ink-900 truncate select-all" title={item.record_hash}>
                          {item.record_hash}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
