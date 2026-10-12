import boto3

apigw = boto3.client("apigatewayv2", region_name="ap-southeast-2")
api_id = "mwrzzbhzu8"

routes = apigw.get_routes(ApiId=api_id)["Items"]
print(f"API {api_id} has {len(routes)} routes:")
for r in routes:
    print(f"  {r.get('RouteKey')} -> Target: {r.get('Target')}")

integrations = apigw.get_integrations(ApiId=api_id)["Items"]
print(f"\nAPI {api_id} has {len(integrations)} integrations:")
for i in integrations:
    print(f"  {i.get('IntegrationId')} -> Type: {i.get('IntegrationType')} | URI: {i.get('IntegrationUri')}")
