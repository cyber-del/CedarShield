import boto3

logs = boto3.client("logs", region_name="ap-southeast-2")
for fn in ["cedarshield-stack-TriggerDenialFunction-EZzrss8VLWZm", "cedarshield-stack-AuditLogFunction-FVmBlG1QtF6g"]:
    log_group = f"/aws/lambda/{fn}"
    try:
        streams = logs.describe_log_streams(logGroupName=log_group, orderBy="LastEventTime", descending=True, limit=1)["logStreams"]
        if streams:
            print(f"=== {fn} ({streams[0]['logStreamName']}) ===")
            events = logs.get_log_events(logGroupName=log_group, logStreamName=streams[0]["logStreamName"], limit=10)["events"]
            for e in events:
                print(" ", e["message"].strip())
    except Exception as e:
        print(f"Error {fn}:", e)
