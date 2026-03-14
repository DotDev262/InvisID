# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first for better caching
COPY app/pyproject.toml app/uv.lock ./

# Install dependencies into a virtual environment
# We use --frozen to ensure consistent builds
RUN uv sync --frozen --no-install-project --no-dev

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PATH="/invisid/.venv/bin:$PATH"

WORKDIR /invisid

# Install runtime system dependencies
# libmagic1: for file type detection
# libgl1 & libglib2.0-0: required for OpenCV (cv2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /invisid/.venv

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
