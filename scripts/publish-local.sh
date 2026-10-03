#!/usr/bin/env bash
# Run from cron/launchd on your own machine. Pulls main and publishes any merged post
# (dated within the last 14 days) that is not yet on Medium / its approved subreddit.
# Usage: scripts/publish-local.sh [--dry-run] [--headed]
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q origin main && git checkout -q main && git merge -q --ff-only origin/main
mkdir -p "${PUBLISHER_HOME:-$HOME/.writing-publisher}"
exec python3 -m publisher publish-pending "$@" >>"${PUBLISHER_HOME:-$HOME/.writing-publisher}/publish.log" 2>&1
