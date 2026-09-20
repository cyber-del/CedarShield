# CedarShield Infrastructure Deployment Script (PowerShell)
# Usage: .\deploy.ps1 [-Region <region>] [-StackName <stack-name>]

param (
    [string]$Region = "us-east-1",
    [string]$StackName = "cedarshield-stack"
)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  CedarShield AWS SAM Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Check AWS CLI and SAM CLI
if (-not (Get-Command sam -ErrorAction SilentlyContinue)) {
    Write-Error "AWS SAM CLI is not installed or not in PATH. Please install SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
}

# 2. Build SAM Application
Write-Host "`n[1/3] Building SAM application..." -ForegroundColor Yellow
sam build
if ($LASTEXITCODE -ne 0) {
    Write-Error "SAM build failed."
    exit 1
}

# 3. Validate SAM Template
Write-Host "`n[2/3] Validating template..." -ForegroundColor Yellow
sam validate
if ($LASTEXITCODE -ne 0) {
    Write-Error "SAM template validation failed."
    exit 1
}

# 4. Deploy SAM Stack
Write-Host "`n[3/3] Deploying CloudFormation Stack ($StackName) to $Region..." -ForegroundColor Yellow
sam deploy `
    --stack-name $StackName `
    --region $Region `
    --capabilities CAPABILITY_NAMED_IAM `
    --resolve-s3 `
    --no-confirm-changeset

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
} else {
    Write-Error "Deployment failed."
    exit 1
}
