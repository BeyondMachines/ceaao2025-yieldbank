#!/bin/sh

echo "🦹 evilcorp-server: Initializing malicious infrastructure..."

# Create stolen data directory with proper permissions
mkdir -p /app/stolen_data
chmod 777 /app/stolen_data

# Create initial log files
touch /app/stolen_data/http_access.log
touch /app/stolen_data/netcat_connections.log

echo "📡 Starting data exfiltration servers..."
echo "🌐 HTTP Command & Control: Port 8888"
echo "📡 Netcat Backdoor Listener: Port 5555"
echo "💾 Stolen data will be saved to: /app/stolen_data/"
echo ""

# Start the Python evil server
exec python /app/evil_server.py