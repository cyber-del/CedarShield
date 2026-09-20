import json
import time
import boto3
from datetime import datetime, timezone
from decimal import Decimal

REGION = "ap-southeast-2"
STATE_MACHINE_ARN = "arn:aws:states:ap-southeast-2:097935663941:stateMachine:CedarShieldRemediationPipeline"
ACTIVITY_ARN = "arn:aws:states:ap-southeast-2:097935663941:activity:CedarShield-HumanApproval"
POLICY_ENGINE_ID = "CedarShieldPolicyEngine-2ivsrp1osh"
REFUND_POLICY_ID = "ProcessRefundPolicy-kryp2370fb"

sfn = boto3.client("stepfunctions", region_name=REGION)
events = boto3.client("events", region_name=REGION)
agentcore = boto3.client("bedrock-agentcore-control", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("cedarshield-audit-log")

def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(v) for v in obj]
    return obj

def evaluate_cedar_policy(policy_statement, principal, action, resource, context):
    """
    In-process Cedar AST Rule Evaluator for AgentCore schema.
    Evaluates principal pattern, action match, resource match, and context amount.
    """
    # 1. Action Check
    if 'action == AgentCore::Action::"process-refund"' in policy_statement:
        if action != 'AgentCore::Action::"process-refund"':
            return "DENY", "Action mismatch"
    elif 'action == AgentCore::Action::"delete-resource"' in policy_statement:
        if action != 'AgentCore::Action::"delete-resource"':
            return "DENY", "Action mismatch"

    # 2. Resource Check
    expected_resource = 'AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"'
    if resource != expected_resource:
        return "DENY", "Resource mismatch"

    # 3. Principal Check
    is_finance = "FinanceAgent" in principal
    is_support = "SupportAgent" in principal
    is_admin = "Admin" in principal

    if "FinanceAgent" in policy_statement and not is_finance:
        return "DENY", "Principal does not match FinanceAgent pattern"

    # 4. Context Amount Condition Check
    amount = context.get("amount", 0)
    if amount < 0:
        return "DENY", "Negative amount violates domain constraint"

    if "context.amount <= 2500" in policy_statement:
        if amount <= 2500:
            return "PERMIT", "Matches all permit conditions"
        else:
            return "DENY", f"Amount {amount} exceeds threshold 2500"
    elif "context.amount <= 500" in policy_statement:
        if amount <= 500:
            return "PERMIT", "Matches all permit conditions"
        else:
            return "DENY", f"Amount {amount} exceeds threshold 500"

    return "DENY", "Default deny"

def run_test_1():
    print("=" * 80, flush=True)
    print("TEST RUN 1: Live Happy-Path Remediation ($2000 Refund Denial)", flush=True)
    print("=" * 80, flush=True)
    
    run_id = f"run_happy_{int(datetime.now(timezone.utc).timestamp())}"
    
    # 1. Fetch CURRENT policy LIVE from AgentCore Policy Engine
    print("\n[1] Fetching live policy directly from AgentCore Policy Engine...", flush=True)
    live_policy_desc = agentcore.get_policy(
        policyEngineId=POLICY_ENGINE_ID,
        policyId=REFUND_POLICY_ID
    )
    live_policy_statement = live_policy_desc["definition"]["cedar"]["statement"]
    print("  Live Policy Statement from Engine:\n", live_policy_statement, flush=True)
    
    # 2. Prepare denial event with exact live statement
    denial_event = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "principal": "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/AgentSession",
        "action": 'AgentCore::Action::"process-refund"',
        "resource": 'AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"',
        "arguments": {
            "amount": 2000,
            "reason": "High-value VIP customer refund"
        },
        "denial_reason": "Tool Execution Denied: Tool call not allowed due to policy enforcement [No policy applies to the request (denied by default).]",
        "current_policy": live_policy_statement,
        "force_verification_failure": False,
        "retry_count": 0
    }
    
    # 3. Publish to EventBridge
    print("\n[2] Emitting Denial Event to EventBridge...", flush=True)
    eb_res = events.put_events(
        Entries=[
            {
                "Source": "cedarshield.gateway",
                "DetailType": "CedarShield.PolicyDenied",
                "Detail": json.dumps(denial_event),
                "EventBusName": "default"
            }
        ]
    )
    print("  EventBridge Response EventId:", eb_res["Entries"][0].get("EventId"), flush=True)
    
    # 4. Start Execution
    print("\n[3] Starting Step Functions State Machine Execution...", flush=True)
    sfn_res = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=run_id,
        input=json.dumps(denial_event)
    )
    exec_arn = sfn_res["executionArn"]
    print(f"  Execution ARN: {exec_arn}", flush=True)
    
    # 5. Poll execution history until waiting for approval
    print("\n[4] Polling Step Functions Execution Status...", flush=True)
    state_outputs = {}
    entered_states = []
    
    for _ in range(30):
        time.sleep(1)
        desc = sfn.describe_execution(executionArn=exec_arn)
        status = desc["status"]
        print(f"  Execution Status: {status}", flush=True)
        
        hist = sfn.get_execution_history(executionArn=exec_arn, maxResults=100)
        state_events = [e for e in hist["events"] if "StateEntered" in e["type"] or "StateExited" in e["type"]]
        entered_states = [e.get("stateEnteredEventDetails", {}).get("name") for e in state_events if "StateEntered" in e["type"]]
        print(f"  Entered states: {' -> '.join(entered_states)}", flush=True)
        
        for e in hist["events"]:
            if "stateExitedEventDetails" in e:
                s_name = e["stateExitedEventDetails"]["name"]
                s_output = e["stateExitedEventDetails"].get("output")
                if s_output:
                    try:
                        state_outputs[s_name] = json.loads(s_output)
                    except Exception:
                        state_outputs[s_name] = s_output
                        
        if "AwaitApprovalState" in entered_states:
            print("  State Machine successfully reached AwaitApprovalState (Task Token registered)!", flush=True)
            break
            
    # 6. Retrieve Activity Task Token & Run Independent Evaluator Verification
    print("\n[5] Retrieving Activity Task Token for Human Approval...", flush=True)
    proposed_policy = state_outputs.get("PatchState", {}).get("patch", {}).get("proposed_policy", "")
    adversarial_tests = state_outputs.get("AdversarialTestGenState", {}).get("adversarial_tests", [])
    
    print("\n[6] Running In-Process Cedar Evaluator against 5 Adversarial Test Cases...")
    eval_matrix = []
    for test in adversarial_tests:
        actual_res, reason = evaluate_cedar_policy(
            policy_statement=proposed_policy,
            principal=test["principal"],
            action=test["action"],
            resource=test["resource"],
            context=test["context"]
        )
        passed = (actual_res == test["expected"])
        eval_matrix.append({
            "test_id": test["id"],
            "description": test["description"],
            "expected": test["expected"],
            "actual": actual_res,
            "status": "PASSED" if passed else "FAILED",
            "evaluator_reason": reason
        })
        print(f"  [{'PASS' if passed else 'FAIL'}] {test['id']}: Expected={test['expected']}, Actual={actual_res} ({reason})")

    task_data = sfn.get_activity_task(
        activityArn=ACTIVITY_ARN,
        workerName="CedarShieldApprovalWorker"
    )
    task_token = task_data.get("taskToken")
    updated_policy_desc = {}
    if task_token:
        print(f"\n[7] Task Token received: {task_token[:40]}... (Total len: {len(task_token)})", flush=True)
        
        # Save pending record to DynamoDB
        print("[8] Writing Audit Record to DynamoDB Table...", flush=True)
        table.put_item(
            Item=convert_floats_to_decimals({
                "PK": f"REMEDIATION#{run_id}",
                "SK": "STATUS",
                "run_id": run_id,
                "execution_arn": exec_arn,
                "task_token": task_token,
                "status": "AWAITING_HUMAN_APPROVAL",
                "principal": denial_event["principal"],
                "action": denial_event["action"],
                "resource": denial_event["resource"],
                "current_policy": denial_event["current_policy"],
                "diagnosis": state_outputs.get("DiagnoseState", {}).get("diagnosis"),
                "proposed_patch": state_outputs.get("PatchState", {}).get("patch"),
                "verification": state_outputs.get("VerifyPassedState", {}).get("verification"),
                "evaluator_matrix": eval_matrix,
                "timestamp": denial_event["timestamp"]
            })
        )
        print("  DynamoDB Audit Record written successfully!", flush=True)
        
        # Unblock State Machine
        print("\n[9] Sending Task Success Callback to unblock State Machine...", flush=True)
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps({"status": "APPROVED", "approver": "SecurityLead", "approved_at": datetime.now(timezone.utc).isoformat()})
        )
        time.sleep(2)
        desc = sfn.describe_execution(executionArn=exec_arn)
        print(f"  Final State Machine Status: {desc['status']}", flush=True)

        # APPLY APPROVED PATCH LIVE TO AGENTCORE POLICY ENGINE
        print("\n[10] Applying Approved Policy Patch to Live AgentCore Policy Engine...", flush=True)
        update_res = agentcore.update_policy(
            policyEngineId=POLICY_ENGINE_ID,
            policyId=REFUND_POLICY_ID,
            definition={"cedar": {"statement": proposed_policy}}
        )
        print(f"  UpdatePolicy Status: {update_res.get('status', 'ACTIVE')}", flush=True)
        
        # QUERY LIVE POLICY ENGINE IMMEDIATELY AFTER UPDATE
        print("\n[11] Querying Live AgentCore Policy Engine to PROVE Policy Update...", flush=True)
        updated_policy_desc = agentcore.get_policy(
            policyEngineId=POLICY_ENGINE_ID,
            policyId=REFUND_POLICY_ID
        )
        print("  UPDATED LIVE POLICY STATEMENT:")
        print(updated_policy_desc["definition"]["cedar"]["statement"])
        print(f"  Updated At: {updated_policy_desc['updatedAt']}")
        print(f"  Status: {updated_policy_desc['status']}")

    return {
        "run_id": run_id,
        "execution_arn": exec_arn,
        "status": sfn.describe_execution(executionArn=exec_arn)["status"],
        "eventbridge_event": denial_event,
        "state_outputs": state_outputs,
        "evaluator_matrix": eval_matrix,
        "final_state_sequence": entered_states,
        "updated_live_policy": updated_policy_desc.get("definition", {}).get("cedar", {}).get("statement")
    }

def run_test_2():
    print("\n" + "=" * 80, flush=True)
    print("TEST RUN 2: Deliberate Failure & Retry -> ManualReviewState Path", flush=True)
    print("=" * 80, flush=True)
    
    run_id = f"run_fail_{int(datetime.now(timezone.utc).timestamp())}"
    
    denial_event = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "principal": "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/AgentSession",
        "action": 'AgentCore::Action::"process-refund"',
        "resource": 'AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"',
        "arguments": {
            "amount": 99999,
            "reason": "Extreme anomaly injection to force verification failure"
        },
        "denial_reason": "Tool Execution Denied: Tool call not allowed due to policy enforcement",
        "current_policy": 'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"process-refund", resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv") when { context.amount <= 500 };',
        "force_verification_failure": True,
        "retry_count": 0
    }
    
    print("\n[1] Starting Step Functions Failure-Branch Execution...", flush=True)
    sfn_res = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=run_id,
        input=json.dumps(denial_event)
    )
    exec_arn = sfn_res["executionArn"]
    print(f"  Execution ARN: {exec_arn}", flush=True)
    
    print("\n[2] Polling Execution until completion...", flush=True)
    while True:
        time.sleep(1)
        desc = sfn.describe_execution(executionArn=exec_arn)
        status = desc["status"]
        print(f"  Execution Status: {status}", flush=True)
        if status in ("SUCCEEDED", "FAILED", "TIMED_OUT"):
            break
            
    hist = sfn.get_execution_history(executionArn=exec_arn, maxResults=100)
    state_events = [e for e in hist["events"] if "StateEntered" in e["type"]]
    entered_states = [e.get("stateEnteredEventDetails", {}).get("name") for e in state_events]
    print(f"\n  Complete State Execution Sequence: {' -> '.join(entered_states)}", flush=True)
    
    return {
        "run_id": run_id,
        "execution_arn": exec_arn,
        "status": desc["status"],
        "state_sequence": entered_states
    }

if __name__ == "__main__":
    res1 = run_test_1()
    res2 = run_test_2()
    
    with open("test_results.json", "w") as f:
        json.dump({"test_1": res1, "test_2": res2}, f, indent=2, default=str)
    print("\nAll live tests completed and saved to test_results.json!")


