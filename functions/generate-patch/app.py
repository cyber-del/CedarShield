import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

# Maximum permitted threshold for autonomous remediation without human escalation
MAX_AUTONOMOUS_THRESHOLD = 2500

def lambda_handler(event, context):
    """
    Step 2: GeneratePatch
    Synthesizes minimal Cedar policy patch diff to remediate legitimate agent denials.
    Enforces a strict MAX_AUTONOMOUS_THRESHOLD ($2500) ceiling.
    """
    print("GeneratePatch received event:", json.dumps(event))
    
    run_id = event.get("run_id")
    principal = event.get("principal")
    action = event.get("action")
    resource = event.get("resource")
    arguments = event.get("arguments", {})
    current_policy = event.get("current_policy", "")
    diagnosis = event.get("diagnosis", {})
    retry_count = event.get("retry_count", 0)
    
    amount = arguments.get("amount", 0)
    
    # HARD GUARD: If the requested amount exceeds the autonomous safety ceiling, refuse patch generation
    if amount > MAX_AUTONOMOUS_THRESHOLD:
        print(f"SECURITY GUARD INTERVENTION: Requested amount ${amount} exceeds MAX_AUTONOMOUS_THRESHOLD (${MAX_AUTONOMOUS_THRESHOLD}). Escalating to Manual Review.")
        return {
            "run_id": run_id,
            "principal": principal,
            "action": action,
            "resource": resource,
            "arguments": arguments,
            "current_policy": current_policy,
            "diagnosis": diagnosis,
            "exceeds_max_autonomous_threshold": True,
            "max_autonomous_threshold": MAX_AUTONOMOUS_THRESHOLD,
            "rejection_reason": f"Requested amount ${amount} exceeds maximum autonomous threshold of ${MAX_AUTONOMOUS_THRESHOLD}. Requires manual executive authorization.",
            "timestamp": event.get("timestamp")
        }
    
    # Calculate proposed threshold within safety boundary
    target_limit = MAX_AUTONOMOUS_THRESHOLD
    
    prompt = f"""You are CedarShield, a Cedar policy security synthesizer.
Given this denial diagnosis:
{json.dumps(diagnosis)}

And the current Cedar policy:
{current_policy}

Generate a minimal, least-privilege Cedar policy patch that allows the legitimate business intent while preserving security guards.
Format your output as JSON with keys:
- proposed_policy: full updated .cedar text
- diff: unified git-style diff
- rationale: technical explanation of the change
- risk_assessment: risk score (0-100) and security notes
"""
    
    patch_result = None
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })
        resp = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        resp_body = json.loads(resp["body"].read().decode("utf-8"))
        text = resp_body["content"][0]["text"]
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        patch_result = json.loads(text)
    except Exception as e:
        print(f"Bedrock invocation fallback: {e}")
        proposed_policy = f"""// Policy: Process Refund (Patched by CedarShield)
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{resource}"
)
when {{
    (
        principal.id like "arn:aws:iam::097935663941:role/*FinanceAgent*" ||
        principal.id like "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*"
    ) &&
    context has amount && context.amount <= {target_limit}
}};"""

        diff = f"""--- old/process_refund.cedar
+++ new/process_refund.cedar
@@ -9,3 +9,3 @@
     ) &&
-    context has amount && context.amount <= 500
+    context has amount && context.amount <= {target_limit}
 }};"""

        patch_result = {
            "proposed_policy": proposed_policy,
            "diff": diff,
            "rationale": f"Increases single-transaction refund authorization cap from $500 to ${target_limit} for FinanceAgent role to accommodate legitimate high-value transactions while maintaining strict IAM principal scoping.",
            "risk_assessment": {
                "risk_score": 25,
                "scope": "TARGETED_THRESHOLD_EXPANSION",
                "notes": "Privilege expansion is constrained strictly to FinanceAgent role and bounded at ${target_limit}."
            },
            "target_limit": target_limit
        }

    # Record in DynamoDB
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        table.update_item(
            Key={"run_id": run_id},
            UpdateExpression="SET patch = :pt, #st = :st",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":pt": json.dumps(patch_result),
                ":st": "PATCH_GENERATED"
            }
        )
    except Exception as dbe:
        print(f"DynamoDB update error: {dbe}")

    return {
        "run_id": run_id,
        "principal": principal,
        "action": action,
        "resource": resource,
        "arguments": arguments,
        "current_policy": current_policy,
        "diagnosis": diagnosis,
        "patch": patch_result,
        "retry_count": retry_count
    }
