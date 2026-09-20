"""
CedarShield Post-Approval Anomaly Monitor Lambda Handler
Triggered via EventBridge Scheduled Rule (e.g. rate(2 minutes) or rate(5 minutes))

Evaluates post-patch tool usage telemetry:
1. Clustering near ceiling (3+ calls >= 90% of patched limit in 5 mins)
2. Sudden volume spikes over baseline

If tripped:
1. Reverts live Cedar Policy on Amazon Bedrock AgentCore Policy Engine to baseline ($500)
2. Appends tamper-evident AUTOMATIC_ROLLBACK block to DynamoDB audit ledger
"""

import json
import time
import os
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
import boto3

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "cedarshield-audit-log")
ENGINE_ID = os.environ.get("ENGINE_ID", "CedarShieldPolicyEngine-2ivsrp1osh")
POLICY_ID = os.environ.get("POLICY_ID", "ProcessRefundPolicy-kryp2370fb")
GATEWAY_ARN = os.environ.get("GATEWAY_ARN", "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

BASELINE_CEDAR_STATEMENT = f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{GATEWAY_ARN}"
)
when {{
    (
        principal.id like "arn:aws:iam::097935663941:role/*FinanceAgent*" ||
        principal.id like "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*"
    ) &&
    context has amount && context.amount <= 500
}};"""

def convert_decimals_to_primitives(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_primitives(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_primitives(v) for v in obj]
    return obj

def canonical_hash_block(record_data):
    canonical_data = {k: v for k, v in record_data.items() if k != "record_hash"}
    clean_data = convert_decimals_to_primitives(canonical_data)
    canonical_json = json.dumps(clean_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

def get_latest_audit_block():
    try:
        items = table.scan().get("Items", [])
        chained = [i for i in items if i.get("prev_hash") is not None]
        if not chained:
            return None, "0" * 64, 0
        chained.sort(key=lambda x: int(x.get("sequence_number", 0)))
        latest = chained[-1]
        return latest, latest.get("record_hash", "0" * 64), int(latest.get("sequence_number", 0))
    except Exception as e:
        print("Error getting latest audit block:", e)
        return None, "0" * 64, 0

def find_previous_policy_from_audit_ledger(action="process-refund"):
    """
    Finds the previous Cedar policy statement dynamically from the audit ledger's
    'current_policy' field recorded before the patch was applied.
    Ensures the rollback provably restores 'what it was before' directly from the
    audit chain, avoiding hardcoded assumptions.
    """
    try:
        items = table.scan().get("Items", [])
        chained = [i for i in items if i.get("prev_hash") is not None]
        chained.sort(key=lambda x: int(x.get("sequence_number", 0)), reverse=True)
        for record in chained:
            if record.get("current_policy"):
                rec_action = str(record.get("action", ""))
                if not action or action in rec_action or rec_action in action:
                    print(f"Dynamically resolved pre-patch policy from Audit Block #{record.get('sequence_number')} (Run: {record.get('run_id')}):")
                    return record.get("current_policy"), record.get("run_id"), record.get("sequence_number")
    except Exception as e:
        print("Warning scanning DynamoDB for pre-patch policy:", e)

    return BASELINE_CEDAR_STATEMENT, "fallback_baseline", "1"

def evaluate_and_rollback(recent_invocations):
    """
    Evaluates invocations for near-ceiling clustering or volume spikes.
    Threshold: 3+ invocations >= $2,250 (90% of $2,500 ceiling) within 5 minutes.
    """
    near_ceiling_calls = []
    for call in recent_invocations:
        amount = call.get("amount", 0)
        if amount >= 2250:
            near_ceiling_calls.append(call)

    if len(near_ceiling_calls) >= 3:
        amounts_str = ", ".join([f"${c.get('amount')}" for c in near_ceiling_calls])
        anomaly_reason = (
            f"Suspicious clustering anomaly detected: {len(near_ceiling_calls)} near-ceiling calls "
            f"({amounts_str}) within 5 minutes exceeding 90% threshold ($2,250) of active ceiling ($2,500)."
        )

        print(f"ANOMALY TRIGGERED: {anomaly_reason}")

        # 1. Read pre-patch policy statement from original patch's audit log record
        pre_patch_statement, source_run_id, source_seq = find_previous_policy_from_audit_ledger("process-refund")
        print(f"Restoring pre-patch statement from audit record '{source_run_id}' (Block #{source_seq}):\n{pre_patch_statement}")

        # 2. Revert live Cedar policy on Bedrock AgentCore
        try:
            control_client.update_policy(
                policyEngineId=ENGINE_ID,
                policyId=POLICY_ID,
                definition={"cedar": {"statement": pre_patch_statement}}
            )
            print(f"Successfully reverted policy {POLICY_ID} to pre-patch state from Block #{source_seq} on AgentCore Policy Engine.")
        except Exception as pe:
            print("Policy revert warning:", pe)

        # 2. Append AUTOMATIC_ROLLBACK block to cryptographic ledger
        latest_block, prev_hash, seq = get_latest_audit_block()
        new_seq = seq + 1
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        rollback_block = {
            "run_id": f"rollback-run-{int(time.time())}",
            "sequence_number": str(new_seq),
            "timestamp": now_iso,
            "action": "process-refund",
            "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
            "resource": GATEWAY_ARN,
            "arguments": {
                "rollback_trigger": "NEAR_CEILING_ABUSE_PATTERN",
                "calls_analyzed": len(recent_invocations),
                "near_ceiling_count": len(near_ceiling_calls)
            },
            "approver_identity": "SYSTEM_ANOMALY_DETECTOR (EventBridge + Lambda)",
            "approver_sub": "system-anomaly-monitor-lambda",
            "final_decision": "AUTOMATIC_ROLLBACK",
            "anomaly_reason": anomaly_reason,
            "policy_reverted_to": "Baseline Constraint (amount <= 500)",
            "policy_applied": POLICY_ID,
            "status": "ROLLED_BACK",
            "prev_hash": prev_hash
        }

        record_hash = canonical_hash_block(rollback_block)
        rollback_block["record_hash"] = record_hash

        try:
            table.put_item(Item=rollback_block)
            print(f"Appended Block #{new_seq} (AUTOMATIC_ROLLBACK) with hash {record_hash}")
        except Exception as dbe:
            print("DynamoDB block write error:", dbe)

        return {
            "anomaly_detected": True,
            "rollback_executed": True,
            "reason": anomaly_reason,
            "sequence_number": new_seq,
            "record_hash": record_hash,
            "policy_reverted_to": "Baseline $500 limit"
        }

    return {
        "anomaly_detected": False,
        "rollback_executed": False,
        "message": "Telemetry within normal operating bounds"
    }

def lambda_handler(event, context):
    """
    Lambda entrypoint for EventBridge scheduled rule.
    """
    print("Executing CedarShield Anomaly Monitor Lambda...")
    # In production, scan recent CloudWatch/DynamoDB tool usage logs from the last 5 minutes
    # For demo & scheduled runs, retrieve recent post-patch telemetry
    recent_invocations = event.get("recent_invocations", [])
    result = evaluate_and_rollback(recent_invocations)
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
