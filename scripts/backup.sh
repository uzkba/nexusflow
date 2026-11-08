#!/bin/sh
# File: scripts/backup.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/nexusflow_${TIMESTAMP}.dump"

echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Starting database backup..."

# PGPASSWORD is automatically used by pg_dump when set
export PGPASSWORD="${POSTGRES_PASSWORD}"

pg_dump -h "${POSTGRES_HOST}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -Fc \
        -f "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Backup completed successfully: ${BACKUP_FILE}"
else
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Backup failed!"
    exit 1
fi

echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Cleaning up backups older than 7 days..."
# POSIX compliant cleanup for files older than 7 days
find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +7 -exec rm -f {} \;

echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] Cleanup finished."