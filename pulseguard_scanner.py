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

PATTERNS = {
    "COMPROMISED_PASSWORD": re.compile(r'([REDACTED_PASSWORD]|[REDACTED_PASSWORD])', re.I),
    "HARDCODED_ACCOUNT_ID": re.compile(r'\b123456789012\b'),
    "COGNITO_USER_POOL": re.compile(r'us-east-1_sample_pool'),
    "COGNITO_CLIENT_ID": re.compile(r'sample_app_client'),
    "AWS_ACCESS_KEY": re.compile(r'(A3T[A-Z0-9]|AKIA|ABIA|ACCA)[A-Z0-9]{16}'),
    "AWS_SECRET_KEY": re.compile(r'(?i)aws_secret_access_key\s*=\s*[\'"][A-Za-z0-9/+=]{40}[\'"]'),
    "PRIVATE_KEY": re.compile(r'-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----'),
    "BEARER_TOKEN": re.compile(r'Bearer\s+eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+'),
}

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".system_generated",
    "__pycache__",
    ".pytest_cache"
}

EXCLUDE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".ico", ".gif", ".svg", ".zip", ".tar", ".gz"
}

def scan_repository(root_dir="."):
    findings = []
    scanned_files = 0

    print("=" * 80)
    print("PULSEGUARD REPOSITORY SECURITY & SECRETS SCANNER")
    print("=" * 80)
    print(f"Scanning target: {os.path.abspath(root_dir)}\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                continue

            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, root_dir)
            
            # Skip the scanner script itself from reporting its own search patterns
            if fname == "pulseguard_scanner.py":
                continue

            scanned_files += 1

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_num, line in enumerate(fp, 1):
                        for rule_name, regex in PATTERNS.items():
                            matches = regex.findall(line)
                            if matches:
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "rule": rule_name,
                                    "match": matches[0],
                                    "preview": line.strip()[:100]
                                })
            except Exception as e:
                print(f"[WARN] Could not read {rel_path}: {e}")

    print(f"Scanned {scanned_files} files across repository.")
    print("-" * 80)

    if findings:
        print(f"\n[FAIL] DETECTED {len(findings)} SECURITY VULNERABILITIES / LEAKS:\n")
        for f in findings:
            print(f"  [{f['rule']}] {f['file']}:{f['line']}")
            print(f"    Match: {f['match']}")
            print(f"    Line:  {f['preview']}\n")
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
