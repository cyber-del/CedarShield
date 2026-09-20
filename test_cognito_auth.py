import requests
import json

COGNITO_ENDPOINT = "https://cognito-idp.ap-southeast-2.amazonaws.com/"
CLIENT_ID = "5v5di986mlbftuo81vvspu1qcd"

payload = {
    "AuthFlow": "USER_PASSWORD_AUTH",
    "ClientId": CLIENT_ID,
    "AuthParameters": {
        "USERNAME": "security-reviewer@example.com",
        "PASSWORD": "CedarPassword123!"
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
