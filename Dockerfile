# Multi-stage Docker build for Ask-Intercom web app
FROM node:18-alpine as frontend-builder

# Build frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile

COPY frontend/ .
RUN pnpm run build

# Python backend stage
FROM python:3.11-slim as backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy Python dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

# Copy application code
COPY src/ ./src/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create non-root user and app directory with proper permissions
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/.ask-intercom-analytics/logs /app/.ask-intercom-analytics/sessions && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check with dynamic port
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Run the application with dynamic port support
CMD ["sh", "-c", "python -m uvicorn src.web.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
