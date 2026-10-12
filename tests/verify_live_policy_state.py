import json
import boto3
from decimal import Decimal

REGION = "ap-southeast-2"
ENGINE_ID = "CedarShieldPolicyEngine-2ivsrp1osh"
POLICY_ID = "ProcessRefundPolicy-kryp2370fb"
TABLE_NAME = "cedarshield-audit-log"

sts = boto3.client("sts", region_name=REGION)
control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    return obj

print("=" * 80)
print("1. CALLER IDENTITY (VALID CREDENTIALS CHECK)")
print("=" * 80)
identity = sts.get_caller_identity()
print(f"Arn: {identity['Arn']}")
print(f"Account: {identity['Account']}")
print(f"UserId: {identity['UserId']}")

print("\n" + "=" * 80)
print(f"2. LIVE get_policy ON ENGINE '{ENGINE_ID}', POLICY '{POLICY_ID}' (RAW CURRENT STATEMENT)")
print("=" * 80)
pol_resp = control_client.get_policy(
    policyEngineId=ENGINE_ID,
    policyId=POLICY_ID
)
clean_pol = convert_decimals(pol_resp)
print(json.dumps(clean_pol, indent=2, default=str))

statement = clean_pol.get("definition", {}).get("cedar", {}).get("statement", "")
print("\n--- EXTRACTED LIVE STATEMENT ---")
print(statement)

print("\n" + "=" * 80)
print("3. RAW DYNAMODB ITEMS IN cedarshield-audit-log")
print("=" * 80)
items = table.scan().get("Items", [])
items = [convert_decimals(it) for it in items]
items.sort(key=lambda x: int(x.get("sequence_number", 0)) if str(x.get("sequence_number", 0)).isdigit() else 0)

for it in items:
    seq = it.get("sequence_number")
    run_id = it.get("run_id")
    print(f"\n--- BLOCK #{seq} (Run ID: {run_id}) ---")
    print(f"final_decision: {it.get('final_decision')}")
    print(f"has current_policy: {'current_policy' in it}")
    if "current_policy" in it:
        print(f"current_policy:\n{it['current_policy']}")
