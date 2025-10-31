FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv and add to PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

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