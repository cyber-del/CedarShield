import boto3

apigw = boto3.client("apigatewayv2", region_name="ap-southeast-2")
api_id = "mwrzzbhzu8"

integrations = apigw.get_integrations(ApiId=api_id)["Items"]
int_map = {i["IntegrationId"]: i for i in integrations}
print("Integrations:", int_map)

# Existing routes
existing_routes = {r["RouteKey"]: r for r in apigw.get_routes(ApiId=api_id)["Items"]}
print("Existing routes:", list(existing_routes.keys()))

desired_routes = {
    "GET /": "qz1onmj",
    "GET /{proxy+}": "qz1onmj",
    "GET /api/audit-log": "qz1onmj",
    "GET /audit-log": "qz1onmj",
    "POST /api/verify-audit-chain": "qz1onmj",
    "POST /verify-audit-chain": "qz1onmj",
    "POST /api/simulate-abuse": "qz1onmj",
    "POST /simulate-abuse": "qz1onmj",
    "GET /api/kpis": "qz1onmj",
    "GET /kpis": "qz1onmj",
    "GET /api/health": "qz1onmj",
    "GET /health": "qz1onmj",
    "POST /api/trigger-denial": "mikjogj",
    "POST /trigger-denial": "mikjogj",
    "POST /api/approve": "3xc3712",
    "POST /approve": "3xc3712",
    "POST /api/reject": "rij3y3g",
    "POST /reject": "rij3y3g",
}

for route_key, target_int in desired_routes.items():
    if route_key not in existing_routes:
        try:
            r = apigw.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{target_int}"
            )
            print(f"Created route: {route_key} -> integrations/{target_int}")
        except Exception as e:
            print(f"Error creating route {route_key}: {e}")
    else:
        print(f"Route already exists: {route_key}")

print("\nAll routes successfully mapped on API Gateway!")
