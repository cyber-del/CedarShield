"""
CedarShield End-to-End Regression Test Suite
============================================
Runs the full pipeline end-to-end and asserts against real CedarShield response shapes:
1. Real AgentCore Gateway MCP denial (-32002) for $2,000 refund
2. Live Bedrock diagnosis root_cause containing actual request values (500 & 2000)
3. Proposed Cedar patch diff containing updated threshold ($2,500), AgentCore::IamEntity, and process-refund (hyphenated)
4. Verification matrix with exactly 5 adversarial/boundary tests, all PASSED
5. Autonomous ceiling check passing for $2,000 (<= $2,500)
6. Trigger $99,999 refund and assert routing to ManualReviewState (not PatchState)
7. Tamper-evident cryptographic audit chain validation
"""

import sys
import json
import time
import requests

API_BASE = "http://localhost:3001/api"
GATEWAY_ARN = "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
FINANCE_ROLE_ARN = "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role"

def run_regression_tests():
    print("=" * 80)
    print("CEDARSHIELD END-TO-END AUTOMATED REGRESSION SUITE")
    print("=" * 80)
    
    results = []

    # ------------------------------------------------------------------------
    # Test 1-5: Trigger $2,000 Refund Denial & Assert Full Pipeline
    # ------------------------------------------------------------------------
    print("\n[1/7] Testing Live AgentCore Gateway MCP Enforcement ($2,000 refund)...")
    try:
        run_id_2000 = f"regression_2000_{int(time.time())}"
        denial_resp = requests.post(
            f"{API_BASE}/trigger-denial",
            json={
                "run_id": run_id_2000,
                "principal": FINANCE_ROLE_ARN,
                "action": "process-refund",
                "amount": 2000,
                "reason": "VIP customer refund attempt"
            },
            timeout=10
        ).json()
        
        raw_resp = denial_resp.get("gateway_raw_response", {})
        print(f"      Gateway Raw Response: {json.dumps(raw_resp)}")
        
        error_obj = raw_resp.get("error", {})
        assert error_obj.get("code") == -32002, f"Expected code -32002, got {error_obj.get('code')}"
        assert "DENY" in error_obj.get("message", "") or "Denied" in error_obj.get("message", ""), f"Unexpected error message: {error_obj.get('message')}"
        
        print("  --> [PASS] AgentCore Gateway returned structured JSON-RPC -32002 policy denial!")
        results.append(("1. Gateway -32002 Denial Shape", "PASS", f"Error Code: {error_obj.get('code')}"))
        
        # ------------------------------------------------------------------------
        # Test 2: Bedrock Diagnosis Real Number Extraction (500 & 2000)
        # ------------------------------------------------------------------------
        print("\n[2/7] Testing Remediation Pipeline Bedrock Diagnosis ($2,000)...")
        denial_rec = denial_resp.get("denial", {})
        diagnosis = denial_rec.get("diagnosis", {})
        root_cause = diagnosis.get("root_cause", "")
        print(f"      Diagnosed Root Cause: {root_cause}")
        assert "500" in root_cause, f"root_cause missing '500': {root_cause}"
        assert "2,000" in root_cause or "2000" in root_cause, f"root_cause missing '2000': {root_cause}"
        print("  --> [PASS] Diagnosis root cause dynamically references 500 & 2000 bounds!")
        results.append(("2. Diagnosis Numbers Grounding (500 & 2000)", "PASS", root_cause[:60] + "..."))

        # ------------------------------------------------------------------------
        # Test 3: Proposed Patch Diff Schema & Threshold Assertions
        # ------------------------------------------------------------------------
        print("\n[3/7] Testing Proposed Patch Diff Schema (AgentCore::IamEntity, process-refund, $2,500)...")
        diff_text = denial_rec.get("diff", "")
        print(f"      Proposed Diff:\n{diff_text}")
        
        assert "2500" in diff_text, f"Diff missing '2500': {diff_text}"
        assert "AgentCore::IamEntity" in diff_text, f"Diff missing 'AgentCore::IamEntity': {diff_text}"
        assert 'process-refund' in diff_text, f"Diff missing hyphenated 'process-refund': {diff_text}"
        assert "CedarShield::Role" not in diff_text, f"Diff contains legacy schema 'CedarShield::Role': {diff_text}"
        assert 'process_refund"' not in diff_text, f"Diff contains unhyphenated action name: {diff_text}"
        
        print("  --> [PASS] Proposed patch correctly uses real AgentCore schema and expands boundary safely to $2,500!")
        results.append(("3. Patch Diff Real Schema (AgentCore & 2500)", "PASS", "AgentCore::IamEntity & process-refund"))

        # ------------------------------------------------------------------------
        # Test 4: Verification Matrix has exactly 5 entries, all PASSED
        # ------------------------------------------------------------------------
        print("\n[4/7] Testing Adversarial Verification Matrix...")
        matrix = denial_rec.get("test_matrix", [])
        print(f"      Matrix Size: {len(matrix)} tests")
        for t in matrix:
            print(f"        - {t.get('test_id')}: Expected {t.get('expected')} -> Actual {t.get('actual')} ({t.get('status')})")
        
        assert len(matrix) == 5, f"Expected exactly 5 verification tests, got {len(matrix)}"
        for t in matrix:
            assert t.get("status") == "PASSED", f"Test {t.get('test_id')} status is not PASSED: {t.get('status')}"
        print("  --> [PASS] All 5 adversarial and boundary verification tests PASSED!")
        results.append(("4. Adversarial Verification Matrix (5 PASSED)", "PASS", "5/5 tests PASSED"))

        # ------------------------------------------------------------------------
        # Test 5: Ceiling Check Passes for $2,000 (<= $2,500)
        # ------------------------------------------------------------------------
        print("\n[5/7] Testing Ceiling Check for $2,000...")
        status = denial_rec.get("status", "")
        is_ceiling = denial_rec.get("is_ceiling_triggered", False)
        print(f"      Status: {status} | Ceiling Triggered: {is_ceiling}")
        assert status == "AWAITING_APPROVAL" and not is_ceiling, f"Unexpected status for $2,000: {status}"
        print("  --> [PASS] $2,000 is within $2,500 ceiling, correctly routed to automated Patch & Verify!")
        results.append(("5. Autonomous Ceiling Check ($2,000 <= $2,500)", "PASS", "Routed to Auto-Remediation"))

    except Exception as e:
        print(f"  --> [FAIL] Pipeline assertion failed: {e}")
        results.append(("Pipeline Execution ($2,000)", "FAIL", str(e)))

    # ------------------------------------------------------------------------
    # Test 6: Trigger $99,999 and assert routing to MANUAL_REVIEW_REQUIRED
    # ------------------------------------------------------------------------
    print("\n[6/7] Testing Autonomous Ceiling Breach ($99,999 refund)...")
    run_id_99999 = f"regression_99999_{int(time.time())}"
    try:
        denial_resp_99k = requests.post(
            f"{API_BASE}/trigger-denial",
            json={
                "run_id": run_id_99999,
                "principal": FINANCE_ROLE_ARN,
                "action": "process-refund",
                "amount": 99999,
                "reason": "Massive unapproved refund breach"
            },
            timeout=10
        ).json()
        
        denial_rec_99k = denial_resp_99k.get("denial", {})
        status_99k = denial_rec_99k.get("status", "")
        is_ceiling_99k = denial_rec_99k.get("is_ceiling_triggered", False)
        print(f"      Status for $99,999: {status_99k} | Ceiling Triggered: {is_ceiling_99k}")
        
        assert status_99k == "MANUAL_REVIEW_REQUIRED" and is_ceiling_99k is True, f"Expected MANUAL_REVIEW_REQUIRED for $99,999, got {status_99k}"
        print("  --> [PASS] $99,999 strictly blocked by hard ceiling guardrail -> Routed to Manual Review!")
        results.append(("6. Ceiling Guardrail Routing ($99,999 -> ManualReview)", "PASS", "Blocked from Autonomous Patch"))
    except Exception as e:
        print(f"  --> [FAIL] Ceiling breach assertion failed: {e}")
        results.append(("6. Ceiling Guardrail Routing ($99,999)", "FAIL", str(e)))

    # ------------------------------------------------------------------------
    # Test 7: Verify Tamper-Evident Audit Hash Chain
    # ------------------------------------------------------------------------
    print("\n[7/7] Verifying Cryptographic Audit Log Chain...")
    try:
        verify_resp = requests.post(f"{API_BASE}/verify-audit-chain", json={}, timeout=5).json()
        chain_valid = verify_resp.get("is_valid", False)
        assert chain_valid is True, f"Audit chain verification returned False: {verify_resp}"
        print(f"  --> [PASS] Full audit chain verified cryptographically valid ({verify_resp.get('total_blocks')} blocks scanned)!")
        results.append(("7. Tamper-Evident Audit Chain Integrity", "PASS", "Cryptographically Valid"))
    except Exception as e:
        print(f"  --> [FAIL] Audit chain verification failed: {e}")
        results.append(("7. Tamper-Evident Audit Chain Integrity", "FAIL", str(e)))

    # ------------------------------------------------------------------------
    # Summary Table
    # ------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("REGRESSION TEST RESULTS SUMMARY")
    print("=" * 80)
    all_passed = True
    for name, status, details in results:
        print(f"  [{status}] {name:<50} | {details}")
        if status != "PASS":
            all_passed = False
    print("=" * 80)
    
    if all_passed:
        print("OVERALL RESULT: ALL 7 END-TO-END ASSERTIONS PASSED WITH ZERO REGRESSIONS.")
        sys.exit(0)
    else:
        print("OVERALL RESULT: REGRESSION DETECTED. ONE OR MORE ASSERTIONS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_regression_tests()
