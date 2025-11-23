# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including curl and netcat
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# # Create non-root user for security
# RUN useradd -m -u 1000 bankapp && chown -R bankapp:bankapp /app
# USER bankapp

# Set environment variables
ENV FLASK_APP=python/app.py
ENV PYTHONPATH=/app/python

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command
CMD ["python", "python/app.py"]