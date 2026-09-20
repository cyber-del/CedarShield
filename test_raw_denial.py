import requests
import json

resp = requests.post(
    "https://mwrzzbhzu8.execute-api.ap-southeast-2.amazonaws.com/prod/trigger-denial",
    json={
        "run_id": "test_1",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
        "action": "process-refund",
        "amount": 2000,
        "reason": "test"
    },
    headers={"Content-Type": "application/json"}
)

print("Status code:", resp.status_code)
print("Headers:", dict(resp.headers))
print("Response text:", resp.text)
