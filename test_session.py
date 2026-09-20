import boto3

session = boto3.Session(region_name="ap-southeast-2")
lambda_client = session.client("lambda")
try:
    resp = lambda_client.list_functions()
    print("Lambda list_functions success! Found:", len(resp.get("Functions", [])))
except Exception as e:
    print("Error:", e)

apigw = session.client("apigatewayv2")
try:
    apis = apigw.get_apis()
    print("APIGW get_apis success! Found:", [a["ApiId"] for a in apis.get("Items", [])])
except Exception as e:
    print("APIGW error:", e)
