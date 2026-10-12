#!/usr/bin/env bash
set -e

REGION="${1:-us-east-1}"
STACK_NAME="${2:-cedarshield-stack}"

echo "===================================================="
echo "  CedarShield AWS SAM Infrastructure Deployment"
echo "===================================================="

if ! command -v sam &> /dev/null; then
    echo "Error: AWS SAM CLI is not installed." >&2
    exit 1
fi

echo "[1/3] Building SAM application..."
sam build

echo "[2/3] Validating template..."
sam validate

echo "[3/3] Deploying CloudFormation Stack ($STACK_NAME) to $REGION..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --resolve-s3 \
    --no-confirm-changeset

echo "Deployment completed successfully!"
