#!/bin/bash
# auto_tasks.sh - Automated backup and transaction generation

# Configuration
CONTAINER_NAME="banking-app"  # Change this to your container name
BACKUP_COMMAND="./yieldbank_backup_restore.sh backup"  # Replace with your actual backup command
TRANSACTIONS_PER_RUN=10  # Number of transactions to generate every 15 minutes

# Counters
minute_counter=0

echo "🚀 Starting automated tasks..."
echo "   Backup: Every 60 minutes"
echo "   Transactions: Every 15 minutes"
echo "   Container: $CONTAINER_NAME"
echo ""

while true; do
    current_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Every 15 minutes - Generate transactions
    if [ $((minute_counter % 15)) -eq 0 ]; then
        echo "[$current_time] 📊 Generating transactions..."
        docker exec $CONTAINER_NAME python python/add_transactions.py $TRANSACTIONS_PER_RUN
        echo ""
    fi
    
    # Every 60 minutes - Run backup
    if [ $((minute_counter % 60)) -eq 0 ]; then
        echo "[$current_time] 💾 Running backup..."
        $BACKUP_COMMAND
        echo ""
    fi
    
    # Increment counter and sleep
    minute_counter=$((minute_counter + 15))
    
    # Reset counter after 1 day to prevent overflow
    if [ $minute_counter -ge 1440 ]; then
        minute_counter=0
    fi
    
    # Sleep for 15 minutes (900 seconds)
    sleep 900
done