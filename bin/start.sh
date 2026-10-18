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

mkdir -p logs
"$DOCKER" compose up -d
{
    printf '%s\n' "$CURRENT_CRON" | awk -v marker="$MARKER" 'index($0, marker) == 0'
    printf '0 5 * * * %s %s\n' "$JOB" "$MARKER"
} | crontab -

echo 'Compose started; competitors scheduled daily at 05:00 (host timezone).'
echo "Logs: $ROOT_DIR/logs/competitors.log"
