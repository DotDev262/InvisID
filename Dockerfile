# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /invisid

# Install system dependencies
# libmagic1: for MIME type detection
# libgl1 & libglib2.0-0: for OpenCV (cv2)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY app/pyproject.toml app/uv.lock ./

# Install dependencies (frozen for consistency)
RUN uv sync --frozen

# Copy project files
COPY . .

# Ensure storage directories exist in the root (where the app expects them)
RUN mkdir -p storage/uploads storage/processed storage/results

# Expose the API port
EXPOSE 8000

# Run the application using the synced virtual environment
CMD ["uv", "run", "app/main.py"]
