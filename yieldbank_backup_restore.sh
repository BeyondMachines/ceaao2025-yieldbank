#!/usr/bin/env bash
# =============================================================================
#  YieldBank – PostgreSQL Backup & Restore Script (Linux/macOS)
# =============================================================================

set -e  
container="banking-postgres"
backup_dir="backups"
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "$backup_dir"

action=$1
backup_file=$2

case "$action" in
  # ----------------------------------------------------------
  # BACKUP MODE
  # ----------------------------------------------------------
  backup)
    echo "Creating PostgreSQL backup from container: $container"
    file_name="yieldbank_pg_backup_${timestamp}.sql"
    file_path="${backup_dir}/${file_name}"

    docker exec "$container" pg_dump -U bankuser -d banking > "$file_path" 2>/dev/null || {
      echo "Backup failed: could not connect or export from container."
      exit 1
    }

    if [ -s "$file_path" ]; then
      echo "Backup saved to $file_path"
    else
      echo "Backup failed: empty file created."
      rm -f "$file_path"
      exit 1
    fi
    ;;

  # ----------------------------------------------------------
  # RESTORE MODE
  # ----------------------------------------------------------
  restore)
    if [ -z "$backup_file" ]; then
      echo "Usage: ./yieldbank_backup_restore.sh restore <file.sql>"
      exit 1
    fi

    if [ ! -f "$backup_file" ]; then
      echo "Backup file not found: $backup_file"
      exit 1
    fi

    echo "Checking if 'banking' database exists..."
    db_exists=$(docker exec "$container" psql -U bankuser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='banking';" 2>/dev/null | tr -d '[:space:]')

    if [ "$db_exists" == "1" ]; then
      echo "Database 'banking' exists — creating pre-restore backup..."
      pre_backup_file="${backup_dir}/yieldbank_pre_restore_${timestamp}.sql"
      docker exec "$container" pg_dump -U bankuser -d banking > "$pre_backup_file" 2>/dev/null || true
      echo "Pre-restore backup saved to $pre_backup_file"
    else
      echo "Database 'banking' not found — creating it now..."
      docker exec "$container" psql -U bankuser -d postgres -c "DROP DATABASE IF EXISTS banking;" >/dev/null 2>&1 || true
      docker exec "$container" psql -U bankuser -d postgres -c "CREATE DATABASE banking WITH OWNER = bankuser;" >/dev/null 2>&1
      echo "Database 'banking' created successfully."
    fi

    echo "Dropping existing schema (if any) and restoring from $backup_file..."
    docker exec "$container" psql -U bankuser -d banking -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true

    cat "$backup_file" | docker exec -i "$container" psql -U bankuser -d banking >/dev/null 2>&1 || {
      echo "Restore failed — check if backup file is valid."
      exit 1
    }

    echo "Database restored successfully."
    ;;

  *)
    echo "Usage: ./yieldbank_backup_restore.sh [backup|restore <file.sql>]"
    exit 1
    ;;
esac
