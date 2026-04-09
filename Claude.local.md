# Local Deployment and Operations Guide

Use this guide to set up and manage the security lab on your local workstation.

## Environment Setup
1. Prerequisites: Ensure Docker and Docker Compose are installed.
2. Initialization:
    * Linux/macOS: Run ./setup.sh.
    * Windows: Run ./setup.bat.
3. Manual Start: docker-compose up --build.

## Backup and Restore
The project includes specialized utilities to manage database state between training sessions:

* Backup: ./yieldbank_backup_restore.sh backup creates a timestamped SQL dump.
* Restore: ./yieldbank_backup_restore.sh restore <filename.sql> overwrites the current database with a saved state.
* Hard Reset: docker-compose down -v wipes all volumes and resets the lab to its original state.

## Monitoring the Attack
To track exploit success, use these terminal commands:
* Application Logs: docker logs -f banking-app.
* Exfiltration Monitoring: docker logs -f evilcorp-server.
* Stolen Data Access: docker exec -it evilcorp-server ls /app/stolen_data/.