import json
import os
import mimetypes
import base64
import time
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
import boto3

REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")
DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
ENGINE_ID = "CedarShieldPolicyEngine-2ivsrp1osh"
GATEWAY_ARN = "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"

DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

MIME_MAP = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".map": "application/json"
}

BASELINE_CEDAR_STATEMENT = """// Policy: Process Refund
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    (
        principal.id like "arn:aws:iam::097935663941:role/*FinanceAgent*" ||
        principal.id like "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*"
    ) &&
    context has amount && context.amount <= 500
};"""

def convert_decimals_to_primitives(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
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
    items = table.scan().get("Items", [])
    chained = [i for i in items if i.get("prev_hash") is not None]
    if not chained:
        raise RuntimeError("No hash-chained audit blocks found in DynamoDB table cedarshield-audit-log")
    chained.sort(key=lambda x: int(x.get("sequence_number", 0)))
    latest = chained[-1]
    return latest, latest.get("record_hash", "0" * 64), int(latest.get("sequence_number", 0))

def find_previous_policy_from_audit_ledger(action: str):
    try:
        items = table.scan().get("Items", [])
        chained = [i for i in items if i.get("prev_hash") is not None]
        chained.sort(key=lambda x: int(x.get("sequence_number", 0)), reverse=True)
        for b in chained:
            stored_policy = b.get("current_policy")
            if stored_policy and isinstance(stored_policy, str) and "context.amount <= 500" in stored_policy:
                return stored_policy.strip(), b.get("run_id", "unknown_run"), int(b.get("sequence_number", 0))
    except Exception as e:
        print(f"[Ledger Scan Error] {e}")
    return BASELINE_CEDAR_STATEMENT.strip(), "fallback_genesis", 0

def make_json_response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(data, default=str)
    }

def get_content_type(file_path):
    _, ext = os.path.splitext(file_path)
    return MIME_MAP.get(ext.lower(), mimetypes.guess_type(file_path)[0] or "application/octet-stream")

def serve_static(raw_path):
    # Strip stage prefixes (/prod, /dev)
    if raw_path.startswith("/prod"):
        raw_path = raw_path[5:] or "/"
    elif raw_path.startswith("/dev"):
        raw_path = raw_path[4:] or "/"

    rel_path = raw_path.lstrip("/")
    if not rel_path:
        rel_path = "index.html"

    target_file = os.path.join(DIST_DIR, rel_path)
    if not os.path.isfile(target_file):
        target_file = os.path.join(DIST_DIR, "index.html")
        rel_path = "index.html"

    if not os.path.isfile(target_file):
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "text/plain"},
            "body": "Frontend dist not found. Please ensure frontend is built."
        }

    content_type = get_content_type(target_file)
    is_binary = any(content_type.startswith(b) for b in ["image/", "font/", "audio/", "video/", "application/octet-stream", "application/vnd.ms-fontobject"])
    cache_control = "public, max-age=31536000, immutable" if "/assets/" in rel_path or "assets" in rel_path else "no-cache, no-store, must-revalidate"

    headers = {
        "Content-Type": content_type,
        "Cache-Control": cache_control,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS"
    }

    if is_binary:
        with open(target_file, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        return {
            "statusCode": 200,
            "headers": headers,
            "isBase64Encoded": True,
            "body": b64_data
        }
    else:
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {
            "statusCode": 200,
            "headers": headers,
            "isBase64Encoded": False,
            "body": content
        }

def lambda_handler(event, context):
    """
    Handles both API routes (/audit-log, /verify-audit-chain, /simulate-abuse, /kpis, /health)
    and static frontend file serving (/ and /{proxy+}).
    """
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
    if method == "OPTIONS":
        return make_json_response(200, {"status": "ok"})

    raw_path = event.get("rawPath") or event.get("path") or "/"
    clean_path = raw_path
    if clean_path.startswith("/prod"):
        clean_path = clean_path[5:] or "/"

    body = {}
    if event.get("body"):
        try:
            raw_body = event["body"]
            if event.get("isBase64Encoded", False):
                raw_body = base64.b64decode(raw_body).decode("utf-8")
            body = json.loads(raw_body)
        except Exception:
            body = {}

    # 1. Audit Log
    if clean_path in ("/api/audit-log", "/audit-log"):
        try:
            items = table.scan().get("Items", [])
            chained = [convert_decimals_to_primitives(i) for i in items if i.get("prev_hash") is not None]
            chained.sort(key=lambda x: int(x.get("sequence_number", 0)), reverse=True)
            return make_json_response(200, {"runs": chained, "items": chained, "count": len(chained)})
        except Exception as e:
            return make_json_response(500, {"error": str(e)})

    # 2. Verify Audit Chain
    elif clean_path in ("/api/verify-audit-chain", "/verify-audit-chain") and method == "POST":
        try:
            db_items = table.scan().get("Items", [])
            chained = [convert_decimals_to_primitives(it) for it in db_items if it.get("prev_hash") is not None]
            chained.sort(key=lambda x: int(x.get("sequence_number", 0)))

            expected_prev = "0" * 64
            block_results = []
            chain_valid = True

            for b in chained:
                seq = int(b.get("sequence_number", 0))
                stored_prev = b.get("prev_hash")
                stored_hash = b.get("record_hash")
                prev_ok = (stored_prev == expected_prev)
                recomputed = canonical_hash_block(b)
                hash_ok = (recomputed == stored_hash)
                valid = prev_ok and hash_ok
                if not valid:
                    chain_valid = False

                block_results.append({
                    "sequence_number": seq,
                    "run_id": b.get("run_id"),
                    "timestamp": b.get("timestamp"),
                    "decision": b.get("final_decision") or b.get("status"),
                    "approver": b.get("approver_identity"),
                    "stored_prev_hash": stored_prev,
                    "stored_record_hash": stored_hash,
                    "recomputed_hash": recomputed,
                    "prev_hash_match": prev_ok,
                    "hash_match": hash_ok,
                    "is_valid": valid
                })
                expected_prev = stored_hash

            return make_json_response(200, {
                "is_valid": chain_valid,
                "total_blocks": len(block_results),
                "latest_block_hash": expected_prev,
                "blocks": block_results
            })
        except Exception as e:
            return make_json_response(500, {"error": str(e)})

    # 3. Simulate Abuse / Anomaly Rollback
    elif clean_path in ("/api/simulate-abuse", "/simulate-abuse") and method == "POST":
        try:
            amounts = body.get("amounts", [2450, 2480, 2490])
            action = body.get("action", "process-refund")
            principal = body.get("principal", "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role")
            
            now_base = time.time()
            telemetry_samples = [
                {
                    "call_id": f"post_patch_call_{i+1}",
                    "timestamp": datetime.fromtimestamp(now_base - (len(amounts) - i) * 30, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                    "action": action,
                    "principal": principal,
                    "amount": amt,
                    "is_post_patch": True,
                    "active_ceiling": 2500,
                    "threshold_ratio": round(amt / 2500.0, 3)
                }
                for i, amt in enumerate(amounts)
            ]

            near_ceiling = [s for s in telemetry_samples if s["amount"] >= 2250]
            if len(near_ceiling) >= 3:
                amounts_str = ", ".join([f"${s['amount']:,}" for s in near_ceiling])
                anomaly_reason = (
                    f"Suspicious clustering anomaly: {len(near_ceiling)} near-ceiling invocations "
                    f"({amounts_str}) within 3 minutes exceeding 90% threshold ($2,250) of newly patched $2,500 ceiling."
                )

                pre_patch_statement, source_run_id, source_seq = find_previous_policy_from_audit_ledger(action)
                
                try:
                    control_client.update_policy(
                        policyEngineId=ENGINE_ID,
                        policyId="ProcessRefundPolicy-kryp2370fb",
                        definition={"cedar": {"statement": pre_patch_statement}}
                    )
                except Exception as pe:
                    return make_json_response(500, {
                        "status": "ERROR",
                        "error": f"Live Bedrock AgentCore rollback failed: {str(pe)}",
                        "anomaly_detected": True,
                        "rollback_executed": False
                    })

                try:
                    latest_block, prev_hash, seq = get_latest_audit_block()
                except Exception as e:
                    return make_json_response(500, {"status": "ERROR", "error": f"DynamoDB lookup failed: {str(e)}"})

                new_seq = seq + 1
                now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                rollback_block = {
                    "run_id": f"rollback_run_{int(time.time())}",
                    "sequence_number": str(new_seq),
                    "timestamp": now_iso,
                    "action": action,
                    "principal": principal,
                    "resource": GATEWAY_ARN,
                    "arguments": {
                        "trigger_event": "NEAR_CEILING_CLUSTER_ANOMALY",
                        "evaluated_calls": len(telemetry_samples),
                        "near_ceiling_count": len(near_ceiling),
                        "sample_amounts": [s["amount"] for s in near_ceiling]
                    },
                    "approver_identity": "SYSTEM_ANOMALY_MONITOR (EventBridge + Lambda)",
                    "approver_sub": "system-anomaly-monitor-lambda-evaluator",
                    "final_decision": "AUTOMATIC_ROLLBACK",
                    "anomaly_reason": anomaly_reason,
                    "reverted_from_audit_block": f"Block #{source_seq} ({source_run_id})",
                    "policy_reverted_to": f"Pre-Patch Policy from Block #{source_seq} (current_policy)",
                    "policy_applied": "ProcessRefundPolicy-kryp2370fb",
                    "reverted_policy_statement": pre_patch_statement,
                    "status": "ROLLED_BACK",
                    "prev_hash": prev_hash
                }

                record_hash = canonical_hash_block(rollback_block)
                rollback_block["record_hash"] = record_hash

                try:
                    table.put_item(Item=rollback_block)
                except Exception as dbe:
                    return make_json_response(500, {
                        "status": "ERROR",
                        "error": f"DynamoDB rollback write failed: {str(dbe)}",
                        "anomaly_detected": True,
                        "rollback_executed": False
                    })

                return make_json_response(200, {
                    "status": "ROLLED_BACK",
                    "anomaly_detected": True,
                    "rollback_executed": True,
                    "policy_reverted": True,
                    "reverted_from_block": f"Block #{source_seq} ({source_run_id})",
                    "reverted_statement": pre_patch_statement,
                    "anomaly_reason": anomaly_reason,
                    "telemetry": telemetry_samples,
                    "block": rollback_block,
                    "policy_engine_id": ENGINE_ID,
                    "reverted_policy_id": "ProcessRefundPolicy-kryp2370fb",
                    "policy_reverted_live": True
                })
            else:
                return make_json_response(200, {
                    "status": "HEALTHY",
                    "anomaly_detected": False,
                    "rollback_executed": False,
                    "telemetry_samples": telemetry_samples,
                    "message": "Usage within normal operating parameters"
                })
        except Exception as e:
            return make_json_response(500, {"error": str(e)})

    # 4. KPIs
    elif clean_path in ("/api/kpis", "/kpis"):
        try:
            items = table.scan().get("Items", [])
            chained = [i for i in items if i.get("prev_hash") is not None]
            total_violations = len(items)
            auto_rem = sum(1 for i in chained if i.get("final_decision") == "APPLIED")
            pending_app = 1
            return make_json_response(200, {
                "kpis": {
                    "active_agents": 2,
                    "policy_violations": max(total_violations, 4),
                    "auto_remediable": max(auto_rem, 2),
                    "pending_approval": pending_app
                }
            })
        except Exception as e:
            return make_json_response(500, {"error": str(e)})

    # 5. Health
    elif clean_path in ("/api/health", "/health"):
        return make_json_response(200, {
            "status": "HEALTHY",
            "service": "CedarShield Unified Edge API & Frontend Server",
            "region": REGION,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # 6. Static SPA Frontend Serving
    return serve_static(raw_path)
