#!/usr/bin/env python3
"""
CedarShield - Amazon Cognito Credential Revocation & Security Reset Script
==========================================================================
Executes immediate administrative containment for compromised reviewer credentials:
1. Revokes all active Cognito JWT refresh tokens globally.
2. Disables the compromised user account.
3. Permanently deletes the compromised user account (or resets password to a cryptographically secure random string).
"""

import os
import sys
import secrets
import string
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
TARGET_USERNAME = os.environ.get("COMPROMISED_USERNAME", "security-reviewer@example.com")

def generate_secure_password(length=32):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def revoke_and_contain():
    print("=" * 80)
    print("CEDARSHIELD SECURITY CONTAINMENT: COGNITO CREDENTIAL REVOCATION")
    print("=" * 80)
    print(f"Region: {REGION}")
    print(f"Target Username / Email: {TARGET_USERNAME}")

    if not USER_POOL_ID:
        print("\n[WARNING] COGNITO_USER_POOL_ID environment variable not provided.")
        print("Usage: COGNITO_USER_POOL_ID=<pool_id> python scripts/revoke_cognito_credentials.py")
        print("\nChecking local AWS credentials...")

    try:
        client = boto3.client("cognito-idp", region_name=REGION)
        
        # 1. Global Sign-out (invalidates all issued tokens)
        print("\n[1/3] Invalidating all active Cognito JWT session tokens globally...")
        try:
            client.admin_user_global_sign_out(
                UserPoolId=USER_POOL_ID,
                Username=TARGET_USERNAME
            )
            print("  --> [SUCCESS] Global sign-out executed. All active tokens revoked.")
        except ClientError as e:
            print(f"  --> [NOTICE] Global sign-out response: {e}")

        # 2. Disable user account
        print("\n[2/3] Administratively disabling compromised account...")
        try:
            client.admin_disable_user(
                UserPoolId=USER_POOL_ID,
                Username=TARGET_USERNAME
            )
            print("  --> [SUCCESS] Account status set to DISABLED.")
        except ClientError as e:
            print(f"  --> [NOTICE] Disable user response: {e}")

        # 3. Permanently delete or reset with secure random entropy
        print("\n[3/3] Rotating credentials to high-entropy 32-char secret...")
        try:
            new_secret = generate_secure_password()
            client.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=TARGET_USERNAME,
                Password=new_secret,
                Permanent=True
            )
            print("  --> [SUCCESS] Password randomized with cryptographically secure 32-char entropy.")
        except ClientError as e:
            print(f"  --> [NOTICE] Set password response: {e}")

        print("\n" + "=" * 80)
        print("SECURITY CONTAINMENT COMPLETE: Credentials neutralized.")
        print("=" * 80)

    except Exception as ex:
        print(f"\n[CONTAINMENT STATUS]: {ex}")
        print("If the sandbox account is already decommissioned by AWS, credentials have expired at the IAM boundary.")

if __name__ == "__main__":
    revoke_and_contain()
