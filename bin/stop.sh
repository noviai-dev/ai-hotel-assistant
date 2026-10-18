#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v crontab >/dev/null || { echo 'crontab is required to remove the schedule.' >&2; exit 1; }
MARKER="# ai-hotel-assistant-$(printf '%s' "$ROOT_DIR" | cksum | awk '{print $1}')"
ERROR_FILE="$(mktemp)"
trap 'rm -f -- "$ERROR_FILE"' EXIT
if CURRENT_CRON="$(LC_ALL=C crontab -l 2>"$ERROR_FILE")"; then
    printf '%s\n' "$CURRENT_CRON" | awk -v marker="$MARKER" 'index($0, marker) == 0' | crontab -
elif ! grep -qi 'no crontab for' "$ERROR_FILE"; then
    cat "$ERROR_FILE" >&2
    exit 1
fi

# Include the collection profile and any running one-off collection container.
docker compose --profile collection down --remove-orphans
echo 'Schedule removed and Compose stopped. Database and backup files are preserved.'
