import boto3
import time

cf = boto3.client("cloudfront")
origin_domain = "cedarshield-web-097935663941-ap-southeast-2.s3-website-ap-southeast-2.amazonaws.com"
caller_ref = f"cedarshield-web-{int(time.time())}"

dist_config = {
    "CallerReference": caller_ref,
    "Comment": "CedarShield Web Platform Frontend Distribution",
    "Enabled": True,
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3WebsiteOrigin",
                "DomainName": origin_domain,
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only"
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3WebsiteOrigin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 3,
            "Items": ["GET", "HEAD", "OPTIONS"],
            "CachedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "ForwardedValues": {
            "QueryString": False,
            "Cookies": {"Forward": "none"}
        },
        "MinTTL": 0,
        "DefaultTTL": 86400,
        "MaxTTL": 31536000,
        "Compress": True
    },
    "CustomErrorResponses": {
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/index.html",
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 0
            }
        ]
    }
}

try:
    res = cf.create_distribution(DistributionConfig=dist_config)
    dist = res["Distribution"]
    print("Created CloudFront Distribution ID:", dist["Id"])
    print("HTTPS Public URL:", f"https://{dist['DomainName']}")
except Exception as e:
    print("CloudFront notice:", e)
