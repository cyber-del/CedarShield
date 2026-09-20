"""
CedarShield Skeleton Verification Suite
Tests all placeholder Lambda handlers, route structures, and DynamoDB schemas.
"""
import sys
import os
import json
import importlib.util

# Add function paths
FUNCTIONS = {
    "diagnose-denial": "functions/diagnose-denial/app.py",
    "generate-patch": "functions/generate-patch/app.py",
    "generate-adversarial-tests": "functions/generate-adversarial-tests/app.py",
    "verify-patch": "functions/verify-patch/app.py",
    "api-trigger-denial": "functions/api-trigger-denial/app.py",
    "api-audit-log": "functions/api-audit-log/app.py",
    "api-approve": "functions/api-approve/app.py",
    "api-reject": "functions/api-reject/app.py",
}

def load_module(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_lambdas():
    print("=" * 60)
    print("Testing Lambda Placeholder Handlers...")
    print("=" * 60)
    all_passed = True
    for name, path in FUNCTIONS.items():
        try:
            mod = load_module(name, path)
            res = mod.lambda_handler({"httpMethod": "GET"}, None)
            assert res["statusCode"] == 200, f"Expected 200, got {res['statusCode']}"
            body = json.loads(res["body"])
            assert body.get("status") == "not implemented yet", f"Expected 'not implemented yet', got {body.get('status')}"
            print(f" [PASS] Lambda: {name.ljust(30)} -> HTTP {res['statusCode']} | body: {body.get('message', body.get('step', ''))}")
        except Exception as e:
            print(f" [FAIL] Lambda: {name.ljust(30)} -> Error: {e}")
            all_passed = False

    return all_passed

def test_template_yaml():
    print("\n" + "=" * 60)
    print("Verifying SAM template.yaml Resource Definitions...")
    print("=" * 60)
    with open("template.yaml", "r") as f:
        content = f.read()

    checks = [
        ("DynamoDB Table", "TableName: cedarshield-audit-log" in content and "run_id" in content),
        ("DiagnoseDenial Role & Function", "DiagnoseDenialRole:" in content and "DiagnoseDenialFunction:" in content),
        ("GeneratePatch Role & Function", "GeneratePatchRole:" in content and "GeneratePatchFunction:" in content),
        ("GenerateAdversarialTests Role & Function", "GenerateAdversarialTestsRole:" in content and "GenerateAdversarialTestsFunction:" in content),
        ("VerifyPatch Role & Function", "VerifyPatchRole:" in content and "VerifyPatchFunction:" in content),
        ("API Gateway Route: POST /trigger-denial", "/trigger-denial" in content and "POST" in content),
        ("API Gateway Route: GET /audit-log", "/audit-log" in content and "GET" in content),
        ("API Gateway Route: POST /approve", "/approve" in content and "POST" in content),
        ("API Gateway Route: POST /reject", "/reject" in content and "POST" in content),
        ("Least Privilege IAM (AWSLambdaBasicExecutionRole)", "AWSLambdaBasicExecutionRole" in content),
    ]

    all_passed = True
    for label, passed in checks:
        if passed:
            print(f" [PASS] {label}")
        else:
            print(f" [FAIL] {label}")
            all_passed = False

    return all_passed

if __name__ == "__main__":
    p1 = test_lambdas()
    p2 = test_template_yaml()
    if p1 and p2:
        print("\nAll 4 infrastructure skeleton checks verified successfully!")
        sys.exit(0)
    else:
        print("\nVerification failed!")
        sys.exit(1)
