# --- Stage 1: Builder ---
# Use the same base image as runtime for absolute python version parity
FROM python:3.12-slim AS builder

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:$PATH"

# Enable bytecode compilation and use copy mode for efficiency
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /invisid

# Install dependencies into a virtual environment
# We keep the pyproject.toml and uv.lock in their original locations relative to WORKDIR
RUN --mount=type=bind,source=app/pyproject.toml,target=app/pyproject.toml \
    --mount=type=bind,source=app/uv.lock,target=app/uv.lock \
    --mount=type=cache,target=/root/.cache/uv \
    cd app && uv sync --frozen --no-install-project --no-dev

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# The venv is created inside the 'app' directory by default if we cd into it
ENV PATH="/invisid/app/.venv/bin:$PATH"

WORKDIR /invisid

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /invisid/app/.venv /invisid/app/.venv

# Copy application code
COPY . .

# Ensure storage structure exists
RUN mkdir -p storage/uploads storage/processed storage/results

# Security: Run as non-root user
RUN useradd -m invisuser && \
    chown -R invisuser:invisuser /invisid
USER invisuser

EXPOSE 8000

# Start application using the virtual environment's python
CMD ["python", "app/main.py"]
