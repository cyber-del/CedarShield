import json

def lambda_handler(event, context):
    record_id = event.get("record_id", "rec_001")
    return {
        "status": "SUCCESS",
        "tool": "read_record",
        "record_id": record_id,
        "data": {
            "customer": "Bharat Enterprise Corp",
            "tier": "Tier-1",
            "status": "Active"
        }
    }
