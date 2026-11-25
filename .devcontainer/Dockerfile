FROM mcr.microsoft.com/devcontainers/base:debian

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
ENV UV_INSTALL_DIR="/usr/local/bin"
ENV UV_NO_MODIFY_PATH=1

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/usr/local/bin:${PATH}"
ENV UV_LINK_MODE=copy