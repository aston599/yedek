# 🤖 KirveHub Bot - Dockerfile
# Python 3.12+ uyumlu, Ubuntu 24.04 production-ready

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Create non-root user
RUN groupadd -r kirvehub && useradd -r -g kirvehub kirvehub
RUN chown -R kirvehub:kirvehub /app
USER kirvehub

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python main.py" || exit 1

# Run the application
CMD ["python", "main.py"] 