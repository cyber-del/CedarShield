import boto3

logs = boto3.client("logs", region_name="ap-southeast-2")
log_group = "/aws/lambda/cedarshield-stack-AuditLogFunction-FVmBlG1QtF6g"

try:
    streams = logs.describe_log_streams(
        logGroupName=log_group,
        orderBy="LastEventTime",
        descending=True,
        limit=2
    )["logStreams"]
    
    for s in streams:
        print(f"Log Stream: {s['logStreamName']}")
        events = logs.get_log_events(
            logGroupName=log_group,
            logStreamName=s["logStreamName"],
            limit=15
        )["events"]
        for e in events:
            print(f"  {e['message'].strip()}")
except Exception as e:
    print("Logs error:", e)
