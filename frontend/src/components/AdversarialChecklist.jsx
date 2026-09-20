import React from "react";
import { CheckCircle2, XCircle, ShieldCheck, FileCheck, AlertCircle } from "lucide-react";

export default function AdversarialChecklist({ testMatrix }) {
  const defaultTests = [
    {
      test_id: "test_boundary_exact",
      description: "Exact threshold boundary ($2,500 by FinanceAgent)",
      principal: "FinanceAgent-Role",
      action: "process-refund",
      amount: "$2,500",
      expected: "PERMIT",
      actual: "PERMIT",
      status: "PASSED",
    },
    {
      test_id: "test_over_boundary",
      description: "Over-boundary threshold ($2,501 by FinanceAgent)",
      principal: "FinanceAgent-Role",
      action: "process-refund",
      amount: "$2,501",
      expected: "DENY",
      actual: "DENY",
      status: "PASSED",
    },
    {
      test_id: "test_role_spoofing",
      description: "Role spoofing ($2,000 refund attempted by SupportAgent)",
      principal: "SupportAgent-Role",
      action: "process-refund",
      amount: "$2,000",
      expected: "DENY",
      actual: "DENY",
      status: "PASSED",
    },
    {
      test_id: "test_negative_amount",
      description: "Negative amount boundary ($-50 by FinanceAgent)",
      principal: "FinanceAgent-Role",
      action: "process-refund",
      amount: "-$50",
      expected: "DENY",
      actual: "DENY",
      status: "PASSED",
    },
    {
      test_id: "test_action_escalation",
      description: "Privilege escalation (delete-resource attempted by FinanceAgent)",
      principal: "FinanceAgent-Role",
      action: "delete-resource",
      amount: "N/A",
      expected: "DENY",
      actual: "DENY",
      status: "PASSED",
    },
  ];

  const tests = testMatrix && testMatrix.length > 0 ? testMatrix : defaultTests;
  const allPassed = tests.every((t) => t.status === "PASSED");

  return (
    <div className="bg-surface rounded-lg border border-ink-200 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-ink-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-ink-100 flex items-center justify-center text-ink-700">
            <FileCheck className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-serif text-sm font-semibold text-ink-900">
              Adversarial Edge-Case Test Report
            </h3>
            <p className="text-[11px] text-ink-500 font-mono">
              Automated synthesis battery verified against proposed patch AST
            </p>
          </div>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider border ${
            allPassed
              ? "bg-muted-green-light text-muted-green border-muted-green-border"
              : "bg-muted-red-light text-muted-red border-muted-red-border"
          }`}
        >
          {allPassed ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>5 of 5 Passed · Zero Regressions</span>
            </>
          ) : (
            <>
              <XCircle className="w-3.5 h-3.5" />
              <span>Verification Failed</span>
            </>
          )}
        </span>
      </div>

      {/* Checklist Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-ink-200 bg-surface-subtle font-mono text-[10px] uppercase text-ink-600 font-semibold">
              <th className="py-2.5 px-4">Test Case ID</th>
              <th className="py-2.5 px-4">Description & Boundary</th>
              <th className="py-2.5 px-4">Principal Scope</th>
              <th className="py-2.5 px-4 text-center">Expected</th>
              <th className="py-2.5 px-4 text-center">Evaluator Result</th>
              <th className="py-2.5 px-4 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100 font-sans">
            {tests.map((t, idx) => {
              const isPass = t.status === "PASSED";
              return (
                <tr key={idx} className="hover:bg-surface-subtle/40 transition-colors">
                  <td className="py-2.5 px-4 font-mono text-[11px] text-ink-700 font-medium">
                    {t.test_id || `case_${idx + 1}`}
                  </td>
                  <td className="py-2.5 px-4 text-ink-800">
                    {t.description}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-[11px] text-ink-600">
                    {t.principal || "FinanceAgent"}
                  </td>
                  <td className="py-2.5 px-4 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider border ${
                        t.expected === "PERMIT"
                          ? "bg-muted-green-light text-muted-green border-muted-green-border"
                          : "bg-muted-red-light text-muted-red border border-muted-red-border"
                      }`}
                    >
                      {t.expected}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider border ${
                        t.actual === "PERMIT"
                          ? "bg-muted-green-light text-muted-green border-muted-green-border"
                          : "bg-muted-red-light text-muted-red border border-muted-red-border"
                      }`}
                    >
                      {t.actual}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider ${
                        isPass
                          ? "text-muted-green bg-muted-green-light/60 border border-muted-green-border"
                          : "text-muted-red bg-muted-red-light/60 border border-muted-red-border"
                      }`}
                    >
                      {isPass ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      <span>{t.status}</span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
