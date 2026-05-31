#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${CONFIG:-$ROOT_DIR/ops/deploy.config}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/release.sh staging
  CONFIRM_PRODUCTION=production bash scripts/release.sh production
  bash scripts/release.sh health staging
  bash scripts/release.sh health production

First:
  cp ops/deploy.config.example ops/deploy.config
  edit ops/deploy.config
EOF
}

log() { printf '[release] %s\n' "$*"; }
die() { printf '[release][error] %s\n' "$*" >&2; exit 1; }

load_config() {
  [ -f "$CONFIG" ] || die "Missing config: $CONFIG"
  # shellcheck disable=SC1090
  source "$CONFIG"
  : "${SSH_USER:=root}"
  : "${SSH_PORT:=22}"
  : "${SSH_KEY:=}"
  : "${REMOTE_DIR:=/root/service/anti_pro}"
}

ssh_args() {
  local args=(-p "$SSH_PORT" -o ConnectTimeout=10 -o ServerAliveInterval=15 -o StrictHostKeyChecking=accept-new)
  [ -n "${SSH_KEY:-}" ] && args+=(-i "$SSH_KEY")
  printf '%q ' "${args[@]}"
}

remote() {
  local host="$1" command="$2"
  # shellcheck disable=SC2046
  ssh $(ssh_args) "${SSH_USER}@${host}" "$command"
}

sync_code() {
  local host="$1"
  log "sync -> $host"
  remote "$host" "mkdir -p '$REMOTE_DIR'"

  local ssh_cmd="ssh -p $SSH_PORT -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
  [ -n "${SSH_KEY:-}" ] && ssh_cmd="$ssh_cmd -i $SSH_KEY"

  rsync -az --delete \
    --exclude '.git' \
    --exclude '.DS_Store' \
    --exclude 'node_modules' \
    --exclude 'dist' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'cursor_sh/backend/.env*' \
    --exclude 'ops/deploy.config' \
    -e "$ssh_cmd" \
    "$ROOT_DIR/" "${SSH_USER}@${host}:${REMOTE_DIR}/"
}

deploy_one() {
  local name="$1" host="$2" mode="$3" env_file="$4" migrate="$5"
  [ -n "$host" ] || die "$name host is empty"

  log "deploy $name ($host)"
  sync_code "$host"

  remote "$host" "
    set -e
    cd '$REMOTE_DIR'
    test -f '$env_file' || { echo 'missing env file: $env_file' >&2; exit 1; }
    export BACKEND_ENV_FILE='$env_file'
    export DEPLOYMENT_MODE='$mode'
    docker compose build
    if [ '$migrate' = 'yes' ]; then
      docker compose run --rm backend alembic upgrade head
    fi
    docker compose up -d --remove-orphans
    curl -fsS http://127.0.0.1:8080/api/health
    echo
  "
}

deploy_staging() {
  deploy_one "staging external" "$STAGING_EXTERNAL_HOST" external "$STAGING_EXTERNAL_ENV" yes
  deploy_one "staging internal" "$STAGING_INTERNAL_HOST" internal "$STAGING_INTERNAL_ENV" no
}

deploy_production() {
  [ "${CONFIRM_PRODUCTION:-}" = "production" ] || die "Add CONFIRM_PRODUCTION=production to deploy production"
  deploy_one "production external" "$PRODUCTION_EXTERNAL_HOST" external "$PRODUCTION_EXTERNAL_ENV" yes
  deploy_one "production internal" "$PRODUCTION_INTERNAL_HOST" internal "$PRODUCTION_INTERNAL_ENV" no
}

health_one() {
  local name="$1" host="$2"
  [ -n "$host" ] || die "$name host is empty"
  log "health $name ($host)"
  remote "$host" "curl -fsS http://127.0.0.1:8080/api/health && echo"
}

health_env() {
  case "$1" in
    staging)
      health_one "staging external" "$STAGING_EXTERNAL_HOST"
      health_one "staging internal" "$STAGING_INTERNAL_HOST"
      ;;
    production)
      health_one "production external" "$PRODUCTION_EXTERNAL_HOST"
      health_one "production internal" "$PRODUCTION_INTERNAL_HOST"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main() {
  if [ -z "${1:-}" ]; then
    usage
    exit 1
  fi

  load_config
  case "${1:-}" in
    staging)
      deploy_staging
      ;;
    production)
      deploy_production
      ;;
    health)
      health_env "${2:-}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
