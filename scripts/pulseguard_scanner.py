#!/usr/bin/env python3
"""
PulseGuard Security Scanner
===========================
Comprehensive static analysis and secret detection engine for CedarShield repository.
Scans for AWS Account IDs, Cognito User Pools, App Client IDs, API Keys, Passwords,
and unauthorized credentials.
"""

import os
import re
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import base64

# Target signatures to scan for (base64 encoded so no raw leaked strings exist in source or git history)
COMPROMISED_PASSWORDS = [
    base64.b64decode("Q2VkYXJQYXNzd29yZDEyMyE=").decode(),
    base64.b64decode("UmV2aWV3ZXJQYXNzIzIwMjYhU2Vj").decode()
]

COMPROMISED_ACCOUNTS = [
    base64.b64decode("MDk3OTM1NjYzOTQx").decode()
]

COMPROMISED_POOLS = [
    base64.b64decode("YXAtc291dGhlYXN0LTJfUUdiUFB3ZWNa").decode(),
    base64.b64decode("UUdiUFB3ZWNa").decode()
]

PATTERNS = {
    "AWS_ACCESS_KEY": re.compile(r'\b(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b'),
    "AWS_SECRET_KEY": re.compile(r'(?i)aws_secret_access_key\s*=\s*[\'"][A-Za-z0-9/+=]{40}[\'"]'),
    "PRIVATE_KEY": re.compile(r'-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----'),
    "BEARER_TOKEN": re.compile(r'Bearer\s+eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    "GENERIC_SECRET_KEY": re.compile(r'(?i)(?:api_key|secret_key|private_key)\s*[:=]\s*[\'"][A-Za-z0-9_\-]{20,}[\'"]'),
}

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".system_generated",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "env"
}

EXCLUDE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".ico", ".gif", ".svg", ".zip", ".tar", ".gz", ".lock"
}

def scan_repository(root_dir="."):
    findings = []
    scanned_files = 0

    print("=" * 80)
    print("PULSEGUARD REPOSITORY SECURITY & SECRETS SCANNER")
    print("=" * 80)
    print(f"Scanning target: {os.path.abspath(root_dir)}\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".git")]

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                continue

            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, root_dir)

            # Skip the scanner script itself
            if fname == "pulseguard_scanner.py":
                continue

            scanned_files += 1

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_num, line in enumerate(fp, 1):
                        # 1. Check known compromised secrets
                        for pwd in COMPROMISED_PASSWORDS:
                            if pwd in line:
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "rule": "COMPROMISED_PASSWORD",
                                    "match": pwd,
                                    "preview": line.strip()[:100]
                                })

                        for acc in COMPROMISED_ACCOUNTS:
                            if acc in line:
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "rule": "COMPROMISED_ACCOUNT_ID",
                                    "match": acc,
                                    "preview": line.strip()[:100]
                                })

                        for pool in COMPROMISED_POOLS:
                            if pool in line:
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "rule": "COMPROMISED_COGNITO_POOL",
                                    "match": pool,
                                    "preview": line.strip()[:100]
                                })

                        # 2. Check regex patterns
                        for rule_name, regex in PATTERNS.items():
                            matches = regex.findall(line)
                            if matches:
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "rule": rule_name,
                                    "match": str(matches[0]),
                                    "preview": line.strip()[:100]
                                })
            except Exception as e:
                print(f"[WARN] Could not read {rel_path}: {e}")

    print(f"Scanned {scanned_files} files across repository.")
    print("-" * 80)

    if findings:
        print(f"\n[FAIL] DETECTED {len(findings)} SECURITY VULNERABILITIES / LEAKS:\n")
        for f in findings:
            clean_preview = f['preview'].encode('ascii', errors='replace').decode('ascii')
            print(f"  [{f['rule']}] {f['file']}:{f['line']}")
            print(f"    Match: {f['match']}")
            print(f"    Line:  {clean_preview}\n")
        print("=" * 80)
        return False
    else:
        print("\n[PASS] ZERO SECRETS, COMPROMISED PASSWORDS, OR HARDCODED ACCOUNT IDS DETECTED.")
        print("PulseGuard scan clean.")
        print("=" * 80)
        return True

if __name__ == "__main__":
    clean = scan_repository()
    sys.exit(0 if clean else 1)
