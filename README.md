## AWS MCP Agent - Overview

This repository contains:
- An MCP Agent (via `google-adk`) runnable in Docker: `Embark-agent/aws-mcp`
- Terraform to deploy infrastructure (ECR, Secrets Manager, ECS/Fargate, logging): `Terraform-ECS`

Use this guide to run the agent locally, push images to ECR, manage secrets safely, and deploy with Terraform.

## Repository layout
- `Embark-agent/aws-mcp/`
  - `dockerfile`: Builds a container that runs the ADK web server (port 8000)
  - `pyproject.toml`: Python deps (includes `google-adk`)
  - `adk-tool/agent.py`: Agent definition using McpToolset (CloudWatch, Terraform, IAM MCP servers)
- `Terraform-ECS/`
  - `main.tf`: ECR, Secrets Manager, ECS Task/Service, CloudWatch Logs, Security Group
  - `variables.tf`, `backend.tf`, `outputs.tf`

## Prerequisites
- Docker 24+
- Terraform >= 1.5
- AWS credentials available as environment variables (recommended):
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`
  - `AWS_REGION` (e.g., `us-west-2`)
- A Google API key for web grounding (optional): `GOOGLE_API_KEY`

## Run the MCP Agent locally (Docker)
From `Embark-agent/aws-mcp`:
```bash
docker build -t adk-tool .

docker run --rm -it \
  -p 8000:8000 \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -e AWS_REGION="${AWS_REGION:-us-west-2}" \
  -e AWS_ENVIRONMENT="dev" \
  -e ADK_MCP_REQUEST_TIMEOUT="60" \
  adk-tool
```

Then open `http://localhost:8000/dev-ui` in your browser. The agent can call the MCP servers (CloudWatch, Terraform, IAM) via `uvx` inside the container.

## Push the image to Amazon ECR
```bash
export AWS_REGION=${AWS_REGION:-us-west-2}
export AWS_ACCOUNT_ID=<YOUR_ACCOUNT_ID>
export REPO_NAME=adk-tool

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$REPO_NAME" ./Embark-agent/aws-mcp
docker tag "$REPO_NAME:latest" \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
```

## Manage secrets with AWS Secrets Manager (no hardcoded secrets)
Build the JSON from environment variables to avoid committing credentials:
```bash
SECRET_NAME=adk-mcp-demo-sm

SECRET_JSON=$(jq -n \
  --arg GOOGLE_API_KEY "$GOOGLE_API_KEY" \
  --arg AWS_REGION "${AWS_REGION:-us-west-2}" \
  --arg AWS_ENVIRONMENT "${AWS_ENVIRONMENT:-dev}" \
  --arg ADK_MCP_REQUEST_TIMEOUT "${ADK_MCP_REQUEST_TIMEOUT:-60}" \
  --arg GOOGLE_GENAI_USE_VERTEXAI "${GOOGLE_GENAI_USE_VERTEXAI:-0}" \
  --arg AWS_ACCESS_KEY_ID "$AWS_ACCESS_KEY_ID" \
  --arg AWS_SECRET_ACCESS_KEY "$AWS_SECRET_ACCESS_KEY" \
  '{
    GOOGLE_API_KEY: $GOOGLE_API_KEY,
    AWS_REGION: $AWS_REGION,
    AWS_ENVIRONMENT: $AWS_ENVIRONMENT,
    ADK_MCP_REQUEST_TIMEOUT: $ADK_MCP_REQUEST_TIMEOUT,
    GOOGLE_GENAI_USE_VERTEXAI: $GOOGLE_GENAI_USE_VERTEXAI,
    AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
  }')

# First time (create)
aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --secret-string "$SECRET_JSON"

# Subsequent updates
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --secret-string "$SECRET_JSON"
```

## Deploy with Terraform (ECS/Fargate + CloudWatch Logs)
From `Terraform-ECS`:
```bash
cd Terraform-ECS
terraform init

# Provide required variables (subnets, etc.) via tfvars or CLI
terraform plan \
  -var "region=${AWS_REGION:-us-west-2}" \
  -var 'subnet_ids=["subnet-xxxx","subnet-yyyy"]'

terraform apply \
  -var "region=${AWS_REGION:-us-west-2}" \
  -var 'subnet_ids=["subnet-xxxx","subnet-yyyy"]'
```

Notes:
- The configuration provisions: ECR repo, Secrets Manager secret, ECS task/service (Fargate, awsvpc), CloudWatch log group, and a Security Group.
- If you prefer to use an existing Security Group, update `main.tf` accordingly; otherwise it creates one and attaches it to the service.
- The task definition includes `awslogs` logging to the created log group and expects secrets in Secrets Manager.

## Troubleshooting
- Model/tool calling errors: Use a model that supports tools (e.g., `gemini-2.0-flash`) if `gemini-2.5-flash` fails in your environment.
- `uvx` not found: The container installs `uv` and exposes it in PATH. Ensure you are running the image built from `Embark-agent/aws-mcp`.
- Terraform large files in git: add `.terraform/` to `.gitignore` and do not commit provider binaries.

## Security
- Never commit API keys or AWS credentials. Use environment variables and Secrets Manager.
- If credentials were committed in history, rotate them in AWS IAM and rewrite history (e.g., `git filter-repo`) before pushing again.


