import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

def lambda_handler(event, context):
    """
    Step 3: GenerateAdversarialTests
    Generates a rigorous test battery of edge cases, privilege escalations, and boundary tests
    to evaluate the proposed Cedar policy patch.
    """
    print("GenerateAdversarialTests received event:", json.dumps(event))
    
    run_id = event.get("run_id")
    patch = event.get("patch", {})
    arguments = event.get("arguments", {})
    retry_count = event.get("retry_count", 0)
    
    amount = arguments.get("amount", 2000)
    target_limit = patch.get("target_limit", 2500)
    proposed_policy = patch.get("proposed_policy", "")
    
    prompt = f"""You are CedarShield Adversarial Test Generator.
Given this proposed Cedar policy:
{proposed_policy}

Generate 5 adversarial & boundary test scenarios:
1. Valid baseline transaction under original limit.
2. Valid boundary transaction matching the newly permitted amount (${amount}).
3. Violation above the new threshold (e.g. ${target_limit + 1000}).
4. Negative or zero amount injection attack.
5. Unauthorized role attempting operation (e.g. SupportAgent trying ${amount}).

Return JSON array under key 'test_cases' where each item has:
- id: string
- name: string
- category: BOUNDARY | PRIVILEGE_ESCALATION | INJECTION | BASELINE
- principal: role ARN
- amount: integer
- expected_decision: PERMIT | DENY
- reason: rationale
"""
    
    test_cases = None
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1200,
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
        test_cases = json.loads(text).get("test_cases", [])
    except Exception as e:
        print(f"Bedrock invocation fallback: {e}")
        test_cases = [
            {
                "id": "TC-01",
                "name": "Standard Baseline Transaction ($100)",
                "category": "BASELINE",
                "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
                "amount": 100,
                "expected_decision": "PERMIT",
                "reason": "Legitimate Finance Agent transaction well below authorization ceiling."
            },
            {
                "id": "TC-02",
                "name": "Remediated Original Request ($2000)",
                "category": "BOUNDARY",
                "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
                "amount": amount,
                "expected_decision": "PERMIT",
                "reason": "The exact transaction that originally triggered the denial, now within the new $2500 cap."
            },
            {
                "id": "TC-03",
                "name": "Over-Threshold Exfiltration ($5000)",
                "category": "BOUNDARY",
                "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
                "amount": 5000,
                "expected_decision": "DENY",
                "reason": "Prevents unauthorized super-large refunds from bypassing agent governance."
            },
            {
                "id": "TC-04",
                "name": "Privilege Escalation Attempt by Support Role",
                "category": "PRIVILEGE_ESCALATION",
                "principal": "arn:aws:iam::097935663941:role/CedarShield-SupportAgent-Role",
                "amount": 250,
                "expected_decision": "DENY",
                "reason": "SupportAgent role must NEVER be permitted to execute process-refund regardless of amount."
            },
            {
                "id": "TC-05",
                "name": "Negative Amount Anomaly ($-50)",
                "category": "INJECTION",
                "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
                "amount": -50,
                "expected_decision": "DENY",
                "reason": "Negative values indicate malformed or adversarial input vectors."
            }
        ]

    # Record in DynamoDB
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        table.update_item(
            Key={"run_id": run_id},
            UpdateExpression="SET adversarial_tests = :at, #st = :st",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":at": json.dumps(test_cases),
                ":st": "ADVERSARIAL_TESTS_GENERATED"
            }
        )
    except Exception as dbe:
        print(f"DynamoDB update error: {dbe}")

    return {
        "run_id": run_id,
        "principal": event.get("principal"),
        "action": event.get("action"),
        "resource": event.get("resource"),
        "arguments": arguments,
        "current_policy": event.get("current_policy"),
        "diagnosis": event.get("diagnosis"),
        "patch": patch,
        "adversarial_tests": test_cases,
        "retry_count": retry_count
    }
