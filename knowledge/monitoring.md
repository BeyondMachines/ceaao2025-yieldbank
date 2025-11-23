# Complete Monitoring Commands for Banking Security Training

## 1. Container Logs Monitoring

### Banking App Logs
```bash
# View recent logs
docker logs banking-app

# Follow logs in real-time
docker logs -f banking-app

# View last 50 lines and follow
docker logs --tail 50 -f banking-app

# View logs with timestamps
docker logs -t banking-app

# View logs from last 10 minutes
docker logs --since 10m banking-app
```

### EvilCorp Server Logs
```bash
# View recent logs
docker logs evilcorp-server

# Follow logs in real-time (IMPORTANT for tracking attacks)
docker logs -f evilcorp-server

# View with timestamps
docker logs -t evilcorp-server

# View last 100 lines and follow
docker logs --tail 100 -f evilcorp-server
```

### Both Containers Simultaneously
```bash
# Follow both logs at the same time (in separate terminals)
# Terminal 1:
docker logs -f banking-app

# Terminal 2:
docker logs -f evilcorp-server

# Or use docker-compose to see all logs:
docker-compose -f docker-compose.postgres.yml logs -f
```

## 2. Interactive Command Line Access

### Banking App Shell Access
```bash
# Get bash shell in banking app
docker exec -it banking-app bash

# Alternative if bash not available
docker exec -it banking-app sh

# Run single command
docker exec banking-app whoami

# Run command with output
docker exec banking-app ls -la /tmp/
```

### EvilCorp Server Shell Access
```bash
# Get shell in evilcorp server
docker exec -it evilcorp-server sh

# Check stolen data directory
docker exec evilcorp-server ls -la /app/stolen_data/

# View stolen files
docker exec evilcorp-server find /app/stolen_data/ -type f -exec ls -la {} \;
```

## 3. Netcat Connection Tracking

### Real-time Connection Monitoring
```bash
# Monitor EvilCorp logs for netcat connections
docker logs -f evilcorp-server | grep -E "(NC|netcat|5555)"

# Monitor all network activity on EvilCorp
docker exec -it evilcorp-server netstat -tuln

# Check active connections to port 5555
docker exec evilcorp-server netstat -an | grep 5555

# Monitor processes on EvilCorp
docker exec evilcorp-server ps aux
```

### Track Stolen Data Files
```bash
# Watch stolen data directory for new files
docker exec -it evilcorp-server watch -n 1 'ls -lat /app/stolen_data/'

# Monitor file changes in real-time
docker exec -it evilcorp-server sh -c "while true; do find /app/stolen_data/ -type f -newer /tmp/lastcheck 2>/dev/null; touch /tmp/lastcheck; sleep 2; done"

# Count stolen files
docker exec evilcorp-server sh -c "echo 'Stolen files count:'; ls -1 /app/stolen_data/*.txt 2>/dev/null | wc -l"
```

## 4. Complete Monitoring Setup (Multi-Terminal)

### Terminal 1: Banking App Logs
```bash
echo "=== BANKING APP LOGS ==="
docker logs -f banking-app
```

### Terminal 2: EvilCorp Server Logs
```bash
echo "=== EVILCORP SERVER LOGS ==="
docker logs -f evilcorp-server
```

### Terminal 3: Stolen Data Monitoring
```bash
echo "=== STOLEN DATA MONITORING ==="
docker exec -it evilcorp-server sh -c "
echo 'Monitoring stolen data directory...'
while true; do
    echo '--- $(date) ---'
    ls -lat /app/stolen_data/ | head -10
    echo 'Total files: $(ls -1 /app/stolen_data/*.txt 2>/dev/null | wc -l)'
    echo 'HTTP requests: $(grep -c \"HTTP\" /app/stolen_data/http_access.log 2>/dev/null || echo 0)'
    echo ''
    sleep 5
done
"
```

### Terminal 4: Interactive Testing
```bash
echo "=== INTERACTIVE TESTING TERMINAL ==="
docker exec -it banking-app bash
```

## 5. Network Connection Tracking

### Monitor All Network Connections
```bash
# Check connections between containers
docker exec banking-app netstat -an | grep evilcorp

# Monitor EvilCorp network connections
docker exec evilcorp-server netstat -tuln

# Check which ports are listening on EvilCorp
docker exec evilcorp-server ss -tlnp
```

### Test Connectivity
```bash
# Test HTTP connection from banking-app to evilcorp
docker exec banking-app curl -I http://evilcorp-server:8888

# Test netcat connection
docker exec banking-app sh -c "echo 'connectivity test' | nc -w 1 evilcorp 5555"

# Test reverse DNS
docker exec banking-app nslookup evilcorp
```

## 6. Real-time Attack Monitoring Script

### Create monitoring script `monitor_attacks.sh`:
```bash
#!/bin/bash

echo "🔍 Banking Security Training - Attack Monitoring Dashboard"
echo "=========================================================="

# Function to check stolen data
check_stolen_data() {
    echo "📊 Stolen Data Summary:"
    docker exec evilcorp-server sh -c "
        echo '  HTTP captures: \$(ls -1 /app/stolen_data/http_*.txt 2>/dev/null | wc -l)'
        echo '  Netcat captures: \$(ls -1 /app/stolen_data/netcat_*.txt 2>/dev/null | wc -l)'
        echo '  Total files: \$(ls -1 /app/stolen_data/*.txt 2>/dev/null | wc -l)'
        echo '  Latest file: \$(ls -t /app/stolen_data/*.txt 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo \"None\")'
    "
}

# Function to show recent activity
show_recent_activity() {
    echo "🕐 Recent Activity (last 5 minutes):"
    docker exec evilcorp-server find /app/stolen_data/ -name "*.txt" -mmin -5 -exec echo "  📄 {}" \; 2>/dev/null | head -5
}

# Function to show active connections
show_connections() {
    echo "🌐 Active Connections:"
    docker exec evilcorp-server netstat -an | grep -E "(5555|8888)" | sed 's/^/  /'
}

# Main monitoring loop
while true; do
    clear
    echo "🔍 Banking Security Training - Attack Monitoring Dashboard"
    echo "=========================================================="
    echo "📅 $(date)"
    echo ""
    
    check_stolen_data
    echo ""
    
    show_recent_activity
    echo ""
    
    show_connections
    echo ""
    
    echo "🔄 Refreshing in 10 seconds... (Ctrl+C to stop)"
    sleep 10
done
```

### Run the monitoring script:
```bash
chmod +x monitor_attacks.sh
./monitor_attacks.sh
```

## 7. Specific Attack Evidence Commands

### After Running Exploits, Check Evidence:
```bash
# Check for exploit evidence files
docker exec banking-app ls -la /tmp/*hacked*.txt /tmp/*pwned*.txt 2>/dev/null

# View stolen data files
docker exec evilcorp-server cat /app/stolen_data/*.txt

# Check HTTP access logs
docker exec evilcorp-server tail -20 /app/stolen_data/http_access.log

# Count successful attacks
docker exec evilcorp-server sh -c "
echo 'Attack Summary:'
echo 'HTTP POST requests: \$(grep -c POST /app/stolen_data/http_access.log 2>/dev/null || echo 0)'
echo 'Netcat connections: \$(ls -1 /app/stolen_data/netcat_*.txt 2>/dev/null | wc -l)'
echo 'Total data files: \$(ls -1 /app/stolen_data/*.txt 2>/dev/null | wc -l)'
"
```

## 8. Copy Evidence to Host

### Extract All Evidence:
```bash
# Create evidence directory
mkdir -p ./security_training_evidence

# Copy stolen data from EvilCorp
docker cp evilcorp-server:/app/stolen_data ./security_training_evidence/evilcorp_stolen_data

# Copy exploit evidence from banking app
docker cp banking-app:/tmp ./security_training_evidence/banking_app_tmp

# Copy application logs
docker cp banking-app:/app/logs ./security_training_evidence/banking_app_logs 2>/dev/null || echo "No app logs found"

echo "📁 Evidence copied to ./security_training_evidence/"
ls -la ./security_training_evidence/
```

## 9. Quick Status Check

### One-liner status commands:
```bash
# Quick health check
echo "Banking App: $(docker exec banking-app echo 'OK' 2>/dev/null || echo 'DOWN')"
echo "evilcorp-server: $(docker exec evilcorp-server echo 'OK' 2>/dev/null || echo 'DOWN')"

# Quick attack summary
docker exec evilcorp-server sh -c "echo 'Attacks detected: $(ls -1 /app/stolen_data/*.txt 2>/dev/null | wc -l)'"

# Quick exploit check
docker exec banking-app sh -c "echo 'Exploit evidence: $(ls -1 /tmp/*hacked*.txt /tmp/*pwned*.txt 2>/dev/null | wc -l)'"
```

Use these commands to effectively monitor your security training environment and track all the deserialization attacks in real-time!