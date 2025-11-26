<#
===============================================================================
 YieldBank – PostgreSQL Backup & Restore Script (Windows PowerShell)
===============================================================================
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("backup", "restore")]
    [string]$Action,

    [string]$BackupFile
)

$container = "banking-postgres"
$backupDir = "backups"
$timestamp = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")

if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

switch ($Action) {

    # ----------------------------------------------------------
    # BACKUP MODE
    # ----------------------------------------------------------
    "backup" {
        Write-Host "Creating PostgreSQL backup from container: $container"
        $fileName = "yieldbank_pg_backup_$timestamp.sql"
        $filePath = Join-Path $backupDir $fileName

        docker exec $container pg_dump -U bankuser -d banking > $filePath

        if ((Test-Path $filePath) -and ((Get-Item $filePath).Length -gt 0)) {
            Write-Host "Backup saved to $filePath"
        } else {
            Write-Host "Backup failed!"
        }
        break
    }

    # ----------------------------------------------------------
    # RESTORE MODE
    # ----------------------------------------------------------
    "restore" {
        if (-not $BackupFile) {
            Write-Host "Usage: .\yieldbank_backup_restore.ps1 restore <file.sql>"
            exit 1
        }

        if (!(Test-Path $BackupFile)) {
            Write-Host "Backup file not found: $BackupFile"
            exit 1
        }

        Write-Host "Checking if 'banking' database exists..."
        $dbExists = docker exec $container psql -U bankuser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='banking';" 2>$null

        if ($null -ne $dbExists -and $dbExists.Trim() -eq "1") {
            Write-Host "Database 'banking' exists — creating pre-restore backup..."
            $preBackupFile = Join-Path $backupDir "yieldbank_pre_restore_$timestamp.sql"
            docker exec $container pg_dump -U bankuser -d banking > $preBackupFile
            Write-Host "Pre-restore backup saved to $preBackupFile"
        }
        else {
            Write-Host "Database 'banking' not found — creating it now..."
            docker exec $container psql -U bankuser -d postgres -c "DROP DATABASE IF EXISTS banking;"
            docker exec $container psql -U bankuser -d postgres -c "CREATE DATABASE banking WITH OWNER = bankuser;"
            Write-Host "Database 'banking' created successfully."
        }

        Write-Host "Dropping existing schema (if any) and restoring from $BackupFile..."
        docker exec $container psql -U bankuser -d banking -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" 2>$null | Out-Null

        # PowerShell-safe restore 
        Get-Content -Raw $BackupFile | docker exec -i $container psql -U bankuser -d banking 2>$null | Out-Null

        Write-Host "Database restored successfully."
        break
    }
}
