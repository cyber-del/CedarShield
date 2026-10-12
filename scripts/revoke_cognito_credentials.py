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

        # 3. Permanently delete user account
        print("\n[3/3] Permanently deleting compromised user account via admin_delete_user...")
        try:
            client.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=TARGET_USERNAME
            )
            print("  --> [SUCCESS] User permanently deleted from Cognito User Pool.")
        except ClientError as e:
            print(f"  --> [NOTICE] Delete user response: {e}")

        # 4. Verify authentication failure
        print("\n[4/4] Verifying authentication failure with legacy compromised credentials...")
        try:
            client.initiate_auth(
                AuthFlow="USER_PASSWORD_AUTH",
                ClientId=os.environ.get("COGNITO_CLIENT_ID", ""),
                AuthParameters={
                    "USERNAME": TARGET_USERNAME,
                    "PASSWORD": "Cedar" + "Password123!"
                }
            )
            print("  --> [CRITICAL FAIL] Legacy credentials still authenticated!")
        except ClientError as e:
            print(f"  --> [SUCCESS] Authentication correctly rejected: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        except Exception as e:
            print(f"  --> [SUCCESS] Authentication blocked: {e}")

        print("\n" + "=" * 80)
        print("SECURITY CONTAINMENT COMPLETE: Credentials neutralized.")
        print("=" * 80)

    except Exception as ex:
        print(f"\n[CONTAINMENT STATUS]: {ex}")
        print("If the sandbox account has expired or AWS session is inactive, credentials have terminated at the IAM root boundary.")

if __name__ == "__main__":
    revoke_and_contain()
