import os
import urllib.request
import re

url = os.environ.get("TARGET_DASHBOARD_URL", "https://cyber-del.github.io/CedarShield/")
print("=" * 70)
print("CHECKING LIVE CEDARSHIELD GITHUB PAGES")
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

    print("\n" + "=" * 70)
    print("ALL CHECKS PASSED: Live link is 100% ONLINE, healthy, and operational!")
    print("=" * 70)

except Exception as e:
    print(f"\n[FAIL] Error occurred during check: {e}")
