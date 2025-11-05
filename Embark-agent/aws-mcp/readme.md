## Overview
This folder contains a minimal AWS MCP (Model Context Protocol) setup using `google-adk`:
- `adk-tool/agent.py`: ADK agent that launches MCP servers (CloudWatch, Terraform, IAM) via `uvx`.
- `dockerfile`: Container image to run the ADK web server (`adk web`).
- `pyproject.toml`: Python dependencies (`google-adk`, `boto3`).

The container exposes a web UI on port 8000 (visit `http://localhost:8000/dev-ui`).

## Prerequisites
- Docker 24+
- AWS credentials available as environment variables:
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`
- `GOOGLE_API_KEY` (for Google grounding)

## Build the image
```bash
docker build -t adk-tool .
```

## Run locally
```bash
docker run --rm -it \
  -p 8000:8000 \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -e AWS_REGION="us-west-2" \
  -e AWS_ENVIRONMENT="dev" \
  -e ADK_MCP_REQUEST_TIMEOUT="60" \
  adk-tool
```

Access the UI at `http://localhost:8000/dev-ui`.

## Push to Amazon ECR
```bash
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=123456789012   # set your account ID
export REPO_NAME=adk-tool

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$REPO_NAME" .
docker tag "$REPO_NAME:latest" \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
```

## Manage secrets with AWS Secrets Manager (no hardcoded secrets)
First time (create):
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

aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --secret-string "$SECRET_JSON"
```

Subsequent updates:
```bash
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --secret-string "$SECRET_JSON"
```

## Notes and troubleshooting
- `uvx not found`: The container installs `uv` and sets PATH; ensure the image was rebuilt and you’re running the image built from this folder.
- `Tool use unsupported` model errors: Use a model that supports tools (e.g., `gemini-2.0-flash` or another supported version). The sample uses `gemini-2.5-flash` in `agent.py`—switch if needed.
- Warnings like future `google-cloud-storage` versions are informational; you can pin `google-cloud-storage>=3.0.0` if necessary in `pyproject.toml`.

## Security guidance
- Never commit secrets or API keys. Use environment variables and Secrets Manager.
- If a secret was ever committed, rotate it in IAM/Google Console and rewrite git history (e.g., `git filter-repo`) before pushing again.
- Ensure `.gitignore` contains common entries like `.venv/`, `.env`, `__pycache__/`, and do not commit `.terraform/` or provider binaries.

