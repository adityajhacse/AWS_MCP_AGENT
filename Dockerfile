FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
ENV MCP_CLIENT_REQUEST_TIMEOUT_SECONDS=120
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_SESSION_TOKEN
ARG AWS_PROFILE=default
ENV AWS_PROFILE=${AWS_PROFILE}
RUN mkdir -p /root/.aws && \
    echo "[656003592460_AccountUser]" > /root/.aws/credentials && \
    echo "aws_access_key_id=${AWS_ACCESS_KEY_ID}" >> /root/.aws/credentials && \
    echo "aws_secret_access_key=${AWS_SECRET_ACCESS_KEY}" >> /root/.aws/credentials && \
    echo "aws_session_token=${AWS_SESSION_TOKEN}" >> /root/.aws/credentials

RUN apt-get update && apt-get install -y curl \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3 \
    && python3 -m pip install --no-cache-dir --upgrade awscli

# Ensure Python output is unbuffered
ENV PYTHONUNBUFFERED=1

# Create and activate virtual environment
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy project files
COPY . .

# Install dependencies (no --frozen, so it creates uv.lock if missing)
RUN uv sync --no-cache

# Expose ADK web port
EXPOSE 8000

# Run ADK web
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8000"]
