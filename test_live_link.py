import urllib.request
import json
import re

url = "http://cedarshield-web-097935663941-ap-southeast-2.s3-website-ap-southeast-2.amazonaws.com/"
print("=" * 70)
print("CHECKING LIVE CEDARSHIELD S3 WEBSITE")
print("=" * 70)
print("Target URL:", url)

try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        status = resp.getcode()
        headers = dict(resp.headers)
        body = resp.read().decode("utf-8")
        print(f"\n[PASS] Root index.html: HTTP {status} OK")
        print(f"       Content-Type: {headers.get('Content-Type')}")
        print(f"       HTML Length: {len(body)} bytes")

    # Check JS & CSS
    js_files = re.findall(r'src=["\']\./(assets/[^"\']+)["\']', body)
    css_files = re.findall(r'href=["\']\./(assets/[^"\']+)["\']', body)

    print("\nAssets Check:")
    for asset in js_files + css_files:
        asset_url = f"{url}{asset}"
        with urllib.request.urlopen(urllib.request.Request(asset_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10) as a_resp:
            content = a_resp.read()
            print(f"  [PASS] {asset:<35} -> HTTP {a_resp.getcode()} ({a_resp.headers.get('Content-Type')}, {len(content):,} bytes)")

    # Check AWS Cognito Endpoint
    print("\nAWS Cognito Cloud Authentication Check:")
    cognito_url = "https://cognito-idp.ap-southeast-2.amazonaws.com/"
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": "5v5di986mlbftuo81vvspu1qcd",
        "AuthParameters": {
            "USERNAME": "security-reviewer@example.com",
            "PASSWORD": "CedarPassword123!"
        }
    }
    req = urllib.request.Request(
        cognito_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as c_resp:
        c_data = json.loads(c_resp.read().decode("utf-8"))
        auth_res = c_data.get("AuthenticationResult", {})
        print(f"  [PASS] Cognito Endpoint Status: HTTP {c_resp.getcode()} OK")
        print(f"         JWT ID Token Issued: {bool(auth_res.get('IdToken'))}")
        print(f"         JWT Access Token Issued: {bool(auth_res.get('AccessToken'))}")
        print(f"         Token Expiration: {auth_res.get('ExpiresIn')}s")

    print("\n" + "=" * 70)
    print("ALL CHECKS PASSED: Live link is 100% ONLINE, healthy, and operational!")
    print("=" * 70)

except Exception as e:
    print(f"\n[FAIL] Error occurred during check: {e}")
