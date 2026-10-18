#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v crontab >/dev/null || { echo 'crontab is required; install and enable cron first.' >&2; exit 1; }
DOCKER="$(command -v docker)"
"$DOCKER" compose version >/dev/null

# Identify this checkout without affecting other projects or user cron entries.
MARKER="# ai-hotel-assistant-$(printf '%s' "$ROOT_DIR" | cksum | awk '{print $1}')"
ERROR_FILE="$(mktemp)"
trap 'rm -f -- "$ERROR_FILE"' EXIT
if ! CURRENT_CRON="$(LC_ALL=C crontab -l 2>"$ERROR_FILE")"; then
    if ! grep -qi 'no crontab for' "$ERROR_FILE"; then
        cat "$ERROR_FILE" >&2
        exit 1
    fi
    CURRENT_CRON=''
fi

# Cron runs commands through /bin/sh, so use POSIX single-quote escaping.
quote() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
JOB="cd $(quote "$ROOT_DIR") && PATH=$(quote "$PATH") $(quote "$DOCKER") compose run --build --rm competitors >> $(quote "$ROOT_DIR/logs/competitors.log") 2>&1"
# Cron treats percent signs specially, even inside shell quotes.
JOB="${JOB//%/\\%}"
MARKETING_JOB="cd $(quote "$ROOT_DIR") && PATH=$(quote "$PATH") $(quote "$DOCKER") compose run --build --rm -T marketing run >> $(quote "$ROOT_DIR/logs/marketing.log") 2>&1"
MARKETING_JOB="${MARKETING_JOB//%/\\%}"

mkdir -p logs
"$DOCKER" compose up -d
# Use cron as the only scheduler, including when migrating from the worker service.
"$DOCKER" compose --profile marketing stop marketing
# Apply additive report/email migrations to existing databases before scheduling.
"$DOCKER" compose run --build --rm -T marketing init-db
{
    printf '%s\n' "$CURRENT_CRON" | awk -v marker="$MARKER" 'index($0, marker) == 0'
    printf '0 5 * * * %s %s\n' "$JOB" "$MARKER"
    printf '0 9 * * * %s %s\n' "$MARKETING_JOB" "$MARKER"
} | crontab -

echo 'Compose started; competitors at 05:00, marketing analysis and email at 09:00 daily (host timezone).'
echo "Logs: $ROOT_DIR/logs/competitors.log"
echo "Logs: $ROOT_DIR/logs/marketing.log"
echo 'Email requires MARKETING_EMAIL_ENABLED=true and SMTP settings in .env. For Japan time, set the host timezone to Asia/Tokyo.'
