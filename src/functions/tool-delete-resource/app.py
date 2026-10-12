import json

def lambda_handler(event, context):
    resource_id = event.get("resource_id", "res_default")
    return {
        "status": "SUCCESS",
        "tool": "delete_resource",
        "resource_id": resource_id,
        "message": f"Resource '{resource_id}' successfully deleted by Admin."
    }
