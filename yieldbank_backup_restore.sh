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
    echo "Creating PostgreSQL backups from container: $container"
    sql_path="${backup_dir}/yieldbank_pg_backup_${timestamp}.sql"
    dump_path="${backup_dir}/yieldbank_pg_backup_${timestamp}.dump"

    # Plain SQL (restore with psql)
    docker exec "$container" pg_dump -U bankuser -d banking > "$sql_path" 2>/dev/null || {
      echo "Plain SQL backup failed: could not connect or export from container."
      exit 1
    }

    if [ -s "$sql_path" ]; then
      echo "Plain SQL backup saved to $sql_path"
    else
      echo "Plain SQL backup failed: empty file created."
      rm -f "$sql_path"
      exit 1
    fi

    # Custom format (restore with pg_restore / pgAdmin)
    docker exec "$container" pg_dump -U bankuser -d banking -Fc > "$dump_path" 2>/dev/null || {
      echo "Custom-format backup failed."
      exit 1
    }

    if [ -s "$dump_path" ]; then
      echo "Custom-format backup saved to $dump_path"
    else
      echo "Custom-format backup failed: empty file created."
      rm -f "$dump_path"
      exit 1
    fi
    ;;

  # ----------------------------------------------------------
  # RESTORE MODE
  # ----------------------------------------------------------
  restore)
    if [ -z "$backup_file" ]; then
      echo "Usage: ./yieldbank_backup_restore.sh restore <file.sql|file.dump>"
      exit 1
    fi

    if [ ! -f "$backup_file" ]; then
      echo "Backup file not found: $backup_file"
      exit 1
    fi

    echo "Checking if 'banking' database exists..."
    db_exists=$(docker exec "$container" psql -U bankuser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='banking';" 2>/dev/null | tr -d '[:space:]')

    if [ "$db_exists" == "1" ]; then
      echo "Database 'banking' exists — creating pre-restore backups..."
      pre_sql="${backup_dir}/yieldbank_pre_restore_${timestamp}.sql"
      pre_dump="${backup_dir}/yieldbank_pre_restore_${timestamp}.dump"
      docker exec "$container" pg_dump -U bankuser -d banking     > "$pre_sql"  2>/dev/null || true
      docker exec "$container" pg_dump -U bankuser -d banking -Fc > "$pre_dump" 2>/dev/null || true
      echo "Pre-restore backups saved to $pre_sql and $pre_dump"
    else
      echo "Database 'banking' not found — creating it now..."
      docker exec "$container" psql -U bankuser -d postgres -c "DROP DATABASE IF EXISTS banking;" >/dev/null 2>&1 || true
      docker exec "$container" psql -U bankuser -d postgres -c "CREATE DATABASE banking WITH OWNER = bankuser;" >/dev/null 2>&1
      echo "Database 'banking' created successfully."
    fi

    echo "Dropping existing schema (if any) and restoring from $backup_file..."
    docker exec "$container" psql -U bankuser -d banking -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true

    # Detect format: custom-format dumps start with magic bytes "PGDMP"
    magic=$(head -c 5 "$backup_file" 2>/dev/null || true)

    if [ "$magic" = "PGDMP" ]; then
      echo "Detected custom-format dump — restoring with pg_restore..."
      cat "$backup_file" | docker exec -i "$container" pg_restore -U bankuser -d banking --no-owner --no-privileges >/dev/null 2>&1 || {
        echo "Restore failed — check if backup file is valid."
        exit 1
      }
    else
      echo "Detected plain SQL dump — restoring with psql..."
      cat "$backup_file" | docker exec -i "$container" psql -U bankuser -d banking >/dev/null 2>&1 || {
        echo "Restore failed — check if backup file is valid."
        exit 1
      }
    fi

    echo "Database restored successfully."
    ;;

  *)
    echo "Usage: ./yieldbank_backup_restore.sh [backup|restore <file.sql|file.dump>]"
    exit 1
    ;;
esac
