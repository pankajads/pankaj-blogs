#!/usr/bin/env bash
# Run from cron/launchd on your own machine. Pulls main and imports any merged post
# (dated within the last 14 days) that has no Medium draft yet, then emails you to review it.
# SMTP settings are read from $PUBLISHER_HOME/smtp.env if present (chmod 600).
# Usage: scripts/publish-local.sh [--dry-run] [--headed]
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q origin main && git checkout -q main && git merge -q --ff-only origin/main
PH="${PUBLISHER_HOME:-$HOME/.writing-publisher}"; mkdir -p "$PH"
if [ -f "$PH/smtp.env" ]; then set -a; . "$PH/smtp.env"; set +a; fi
exec python3 -m publisher draft-pending "$@" >>"$PH/publish.log" 2>&1
