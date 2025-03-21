FROM mcr.microsoft.com/devcontainers/python:3.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create workspace and set permissions
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Switch to vscode user for remaining operations
USER vscode

# Copy requirements and install dependencies
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r /workspace/requirements.txt

WORKDIR /workspace
