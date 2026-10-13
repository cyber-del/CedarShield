import os
import requests
import json

REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
COGNITO_ENDPOINT = os.environ.get("COGNITO_ENDPOINT", f"https://cognito-idp.{REGION}.amazonaws.com/")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "sample_client_id")
USERNAME = os.environ.get("COGNITO_USERNAME", "security-reviewer@example.com")
PASSWORD = os.environ.get("COGNITO_PASSWORD", "")

if not PASSWORD:
    print("COGNITO_PASSWORD not set in environment. Skipping live authentication.")
    exit(0)

payload = {
    "AuthFlow": "USER_PASSWORD_AUTH",
    "ClientId": CLIENT_ID,
    "AuthParameters": {
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD
    }
}

headers = {
    "Content-Type": "application/x-amz-json-1.1",
    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
}

resp = requests.post(COGNITO_ENDPOINT, json=payload, headers=headers)
print("Cognito Auth HTTP Status:", resp.status_code)
data = resp.json()
auth_res = data.get("AuthenticationResult", {})
print("ID Token received:", bool(auth_res.get("IdToken")))
print("Access Token received:", bool(auth_res.get("AccessToken")))
print("Token Type:", auth_res.get("TokenType"))
print("Expires In:", auth_res.get("ExpiresIn"), "seconds")
