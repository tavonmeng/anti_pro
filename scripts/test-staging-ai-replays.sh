#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${CONFIG:-$ROOT_DIR/ops/deploy.config}"

[ -f "$CONFIG" ] || {
  printf 'missing deploy config: %s\n' "$CONFIG" >&2
  exit 1
}

# shellcheck disable=SC1090
source "$CONFIG"
: "${SSH_USER:=root}"
: "${SSH_PORT:=22}"
: "${SSH_KEY:=}"
: "${STAGING_EXTERNAL_HOST:?STAGING_EXTERNAL_HOST is required}"

ssh_options=(
  -p "$SSH_PORT"
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o StrictHostKeyChecking=accept-new
)
[ -n "$SSH_KEY" ] && ssh_options+=(-i "$SSH_KEY")

ssh "${ssh_options[@]}" "${SSH_USER}@${STAGING_EXTERNAL_HOST}" \
  "docker exec anti-pro-backend python -m scripts.replay_ai_conversations"
