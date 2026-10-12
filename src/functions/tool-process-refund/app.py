import json

def lambda_handler(event, context):
    amount = event.get("amount", 0)
    refund_id = f"ref_{context.aws_request_id[:8]}" if context and hasattr(context, 'aws_request_id') else "ref_demo123"
    return {
        "status": "SUCCESS",
        "tool": "process_refund",
        "refund_id": refund_id,
        "amount": amount,
        "message": f"Refund of ${amount} processed successfully."
    }
