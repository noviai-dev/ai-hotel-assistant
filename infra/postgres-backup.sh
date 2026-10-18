#!/bin/sh
set -eu
umask 077

BACKUP_INTERVAL_SECONDS=${BACKUP_INTERVAL_SECONDS:-86400}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
for value in "$BACKUP_INTERVAL_SECONDS" "$BACKUP_RETENTION_DAYS"; do
    case "$value" in
        ''|*[!0-9]*|0*) echo 'Backup interval and retention must be positive integers without leading zeros.' >&2; exit 1 ;;
    esac
done
case "${1:-loop}" in
    loop|once) ;;
    *) echo 'Usage: postgres-backup.sh [loop|once]' >&2; exit 1 ;;
esac

mkdir -p /backups
temporary=''
trap 'if [ -n "$temporary" ]; then rm -f "$temporary"; fi' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

backup() {
    temporary=$(mktemp "/backups/.postgres-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX") || return 1
    if pg_dump --format=custom --no-password --file="$temporary"; then
        if ! pg_restore --list "$temporary" >/dev/null; then
            echo 'Backup archive validation failed.' >&2
            rm -f "$temporary"
            temporary=''
            return 1
        fi
        filename=${temporary##*/}
        archive="/backups/${filename#.}.dump"
        if ! mv "$temporary" "$archive"; then
            echo 'Cannot finalize backup archive.' >&2
            rm -f "$temporary"
            temporary=''
            return 1
        fi
        temporary=''
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Backup complete: $archive"
        # Remove expired archives only after a new backup succeeds.
        find /backups -type f -name 'postgres-*.dump' -mmin "+$((BACKUP_RETENTION_DAYS * 1440))" -exec rm -f '{}' ';'
    else
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Backup failed; existing archives retained." >&2
        rm -f "$temporary"
        temporary=''
        return 1
    fi
}

if [ "${1:-loop}" = once ]; then
    backup
    exit $?
fi

while :; do
    if backup; then
        delay=$BACKUP_INTERVAL_SECONDS
    else
        delay=60
    fi
    sleep "$delay" &
    wait $!
done
