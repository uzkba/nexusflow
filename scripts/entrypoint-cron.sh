#!/bin/sh
# File: scripts/entrypoint-cron.sh

echo "Setting up cron environment..."
# Dump postgres environment variables to a file to be sourced by cron
printenv | grep POSTGRES_ > /etc/cron.env

echo "Scheduling backup job for 03:30 AM every day..."
# Schedule cron: Minute 30, Hour 3. Source the env vars before running the backup script.
echo "30 3 * * * . /etc/cron.env && /scripts/backup.sh > /proc/1/fd/1 2>/proc/1/fd/2" > /etc/crontabs/root

echo "Starting crond..."
# Run crond in foreground (-f) with log level 2 (-l 2)
exec crond -f -l 2