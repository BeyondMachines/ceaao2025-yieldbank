FROM python:3.11-alpine

# Install required tools
RUN apk add --no-cache netcat-openbsd curl

# Set working directory
WORKDIR /app

# Create data directory for stolen information
RUN mkdir -p /app/stolen_data

# Copy the evil server script
COPY evil_server.py /app/
COPY start_servers.sh /app/

# Make script executable
RUN chmod +x /app/start_servers.sh

# Expose ports
EXPOSE 5555 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD nc -z localhost 8888 || exit 1

RUN sed -i 's/\r$//' /app/start_servers.sh

# Start the evil servers
CMD ["sh", "/app/start_servers.sh"]