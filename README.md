# YieldBank
Vulnerable YieldBank repo for the Masterclass

###  Prerequisites
- Docker Desktop installed and running  


Make sure to copy `.env.postgres` to `.env` before running.
The stack starts with `setup.bat` (Windows) or `setup.sh` (Mac, Linux)


To add more transactions
docker exec -it banking-app python python/add_transactions.py

To make a backup
yieldbank_backup_restore.sh backup

To restore
yieldbank_backup_restore.sh restore backups/filename