# CedarShield AWS SAM Deployment Guide

This guide walks through deploying the complete CedarShield serverless infrastructure to your dedicated AWS account using AWS Serverless Application Model (SAM).

---

## 1. Prerequisites

Before deploying, ensure you have installed and configured the following tools:

- **AWS CLI v2**: [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS SAM CLI**: [Install SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **Python 3.11+**: Lambda runtime environment
- **Node.js 18+ & npm**: Required for building the frontend dashboard
- **Active AWS Account**: With administrative permissions for IAM, Lambda, API Gateway, Step Functions, DynamoDB, Cognito, and Bedrock.

Verify your local AWS session:
```bash
aws sts get-caller-identity
```

---

## 2. Repository Structure

Infrastructure and application code are structured as follows:

```
├── infra/
│   ├── template.yaml             # AWS SAM Infrastructure as Code template
│   ├── samconfig.toml            # SAM deployment configuration
│   └── *.json                    # IAM trust & permission policy definitions
├── src/
│   ├── functions/                # Lambda handlers (Diagnose, Patch, Verify, API)
│   ├── anomaly_monitor.py        # EventBridge velocity & rollback handler
│   └── server.py                 # Local development & mock backend server
├── frontend/                     # React / Vite dashboard
└── tests/                        # Regression & verification suites
```

---

## 3. Build & Deploy via AWS SAM

### Step 1: Validate SAM Template
Validate the SAM template syntax:
```bash
sam validate -t infra/template.yaml
```

### Step 2: Build Application Artifacts
Build the Python Lambda function packages:
```bash
sam build -t infra/template.yaml
```

### Step 3: Guided Deployment
Deploy the CloudFormation stack to your AWS account:
```bash
sam deploy --guided -t infra/template.yaml
```

During the guided deployment prompt, configure the parameters:
```
Setting default arguments for 'sam deploy'
=========================================
Stack Name [cedarshield-stack]: cedarshield-stack
AWS Region [us-east-1]: us-east-1 (or your preferred Bedrock-supported region)
Parameter AdminAlertEmail []: your-email@example.com (receives AWS Budget and escalation alerts)
Confirm changes before deploy [y/N]: y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: infra/samconfig.toml
SAM configuration environment [default]: default
```

---

## 4. Deployed Cloud Resources

Upon successful deployment, SAM provisions:

1. **Amazon Cognito User Pool & App Client**:
   - RBAC directory for human-in-the-loop security reviewers.
2. **Amazon API Gateway (HTTP API)**:
   - Secured endpoints with built-in route throttling (`5 req/sec`, burst `10`).
3. **AWS Step Functions State Machine**:
   - `CedarShieldRemediationPipeline` orchestrating the 7-stage remediation workflow with hard `$2,500` ceiling enforcement.
4. **AWS Lambda Functions**:
   - `DiagnoseDenialFunction`, `GeneratePatchFunction`, `VerifyPatchFunction`, `AwaitApprovalHandler`, and API router handlers.
5. **Amazon DynamoDB Table**:
   - `cedarshield-audit-log` maintaining the cryptographic SHA-256 Merkle chain.
6. **AWS Budgets**:
   - `$20 USD` monthly budget with automated email alerts at 80% ($16) and 100% ($20).

---

## 5. Post-Deployment Verification

Verify stack outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name cedarshield-stack \
  --query "Stacks[0].Outputs" \
  --output table
```

Confirm budget subscription email:
- Check your inbox for the **AWS Notification - Subscription Confirmation** email from Amazon SNS and click the confirmation link to activate budget alerts.

---

## 6. Running Local Frontend Against Deployed Backend

To point the frontend dashboard to your newly deployed API Gateway:

1. Create `frontend/.env.local`:
   ```bash
   VITE_API_BASE_URL=https://<API_ID>.execute-api.<REGION>.amazonaws.com
   VITE_COGNITO_USER_POOL_ID=<USER_POOL_ID>
   VITE_COGNITO_CLIENT_ID=<CLIENT_ID>
   VITE_AWS_REGION=<REGION>
   ```
2. Build and launch the local dashboard:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:3000` to interact with your live infrastructure.
