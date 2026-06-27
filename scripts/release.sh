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

backup_remote() {
  local name="$1" host="$2"
  [ -n "$host" ] || die "$name host is empty"
  log "backup $name ($host)"
  remote "$host" "
    set -e
    if [ ! -d '$REMOTE_DIR' ]; then
      echo 'skip backup: remote dir does not exist yet'
      exit 0
    fi
    backup_root=\"\${ROLLBACK_BACKUP_DIR:-$(dirname "$REMOTE_DIR")/anti_pro_release_backups}\"
    mkdir -p \"\$backup_root\"
    safe_name=\$(printf '%s' '$name' | tr ' /' '__')
    archive=\"\$backup_root/\$(date +%Y%m%d-%H%M%S)-\$safe_name.tar.gz\"
    tar -C '$(dirname "$REMOTE_DIR")' \
      --exclude='$(basename "$REMOTE_DIR")/cursor_sh/hermes_skills' \
      --exclude='$(basename "$REMOTE_DIR")/ops/deploy.config' \
      -czf \"\$archive\" '$(basename "$REMOTE_DIR")'
    echo \"backup=\$archive\"
    ls -1t \"\$backup_root\"/*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
  "
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
    --exclude '.agents/' \
    --exclude 'skills-lock.json' \
    --exclude 'node_modules' \
    --exclude 'dist' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'cursor_sh/backend/.env*' \
    --exclude 'cursor_sh/hermes_skills/' \
    --exclude 'ops/deploy.config' \
    -e "$ssh_cmd" \
    "$ROOT_DIR/" "${SSH_USER}@${host}:${REMOTE_DIR}/"
}

deploy_one() {
  local name="$1" host="$2" mode="$3" env_file="$4" migrate="$5" frontend_port_bind="$6" health_url="$7"
  [ -n "$host" ] || die "$name host is empty"

  log "deploy $name ($host)"
  backup_remote "$name" "$host"
  sync_code "$host"

  remote "$host" "
    set -e
    cd '$REMOTE_DIR'
    test -f '$env_file' || { echo 'missing env file: $env_file' >&2; exit 1; }
    export BACKEND_ENV_FILE='$env_file'
    export DEPLOYMENT_MODE='$mode'
    export FRONTEND_PORT_BIND='$frontend_port_bind'
    docker compose build
    if [ '$migrate' = 'yes' ]; then
      docker compose run --rm backend alembic upgrade head
    fi
    docker compose up -d --remove-orphans
    for i in \$(seq 1 30); do
      if curl -fsS '$health_url'; then
        echo
        exit 0
      fi
      sleep 2
    done
    docker compose ps
    docker compose logs --tail=120 backend
    exit 1
  "
}

deploy_staging() {
  deploy_one "staging external" "$STAGING_EXTERNAL_HOST" external "$STAGING_EXTERNAL_ENV" yes "${STAGING_EXTERNAL_FRONTEND_PORT_BIND:-80:8080}" "${STAGING_EXTERNAL_HEALTH_URL:-http://127.0.0.1/api/health}"
  deploy_one "staging internal" "$STAGING_INTERNAL_HOST" internal "$STAGING_INTERNAL_ENV" no "${STAGING_INTERNAL_FRONTEND_PORT_BIND:-127.0.0.1:8080:8080}" "${STAGING_INTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
}

deploy_production() {
  [ "${CONFIRM_PRODUCTION:-}" = "production" ] || die "Add CONFIRM_PRODUCTION=production to deploy production"
  deploy_one "production external" "$PRODUCTION_EXTERNAL_HOST" external "$PRODUCTION_EXTERNAL_ENV" yes "${PRODUCTION_EXTERNAL_FRONTEND_PORT_BIND:-127.0.0.1:8080:8080}" "${PRODUCTION_EXTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
  deploy_one "production internal" "$PRODUCTION_INTERNAL_HOST" internal "$PRODUCTION_INTERNAL_ENV" no "${PRODUCTION_INTERNAL_FRONTEND_PORT_BIND:-127.0.0.1:8080:8080}" "${PRODUCTION_INTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
}

health_one() {
  local name="$1" host="$2" health_url="$3"
  [ -n "$host" ] || die "$name host is empty"
  log "health $name ($host)"
  remote "$host" "curl -fsS '$health_url' && echo"
}

health_env() {
  case "$1" in
    staging)
      health_one "staging external" "$STAGING_EXTERNAL_HOST" "${STAGING_EXTERNAL_HEALTH_URL:-http://127.0.0.1/api/health}"
      health_one "staging internal" "$STAGING_INTERNAL_HOST" "${STAGING_INTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
      ;;
    production)
      health_one "production external" "$PRODUCTION_EXTERNAL_HOST" "${PRODUCTION_EXTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
      health_one "production internal" "$PRODUCTION_INTERNAL_HOST" "${PRODUCTION_INTERNAL_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
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
