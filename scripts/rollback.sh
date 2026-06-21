#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${CONFIG:-$ROOT_DIR/ops/deploy.config}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/rollback.sh staging [latest|archive-name]
  CONFIRM_PRODUCTION=production bash scripts/rollback.sh production [latest|archive-name]
  bash scripts/rollback.sh list staging
  bash scripts/rollback.sh list production

Notes:
  - Rollback restores the remote code snapshot made before release.
  - Rollback does not downgrade the database.
  - Runtime Creative Agent skills are preserved from the current server.
EOF
}

log() { printf '[rollback] %s\n' "$*"; }
die() { printf '[rollback][error] %s\n' "$*" >&2; exit 1; }

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

list_one() {
  local name="$1" host="$2"
  [ -n "$host" ] || die "$name host is empty"
  log "list $name ($host)"
  remote "$host" "
    set -e
    backup_root=\"\${ROLLBACK_BACKUP_DIR:-$(dirname "$REMOTE_DIR")/anti_pro_release_backups}\"
    if [ ! -d \"\$backup_root\" ]; then
      echo 'no backups'
      exit 0
    fi
    ls -1t \"\$backup_root\"/*.tar.gz 2>/dev/null | head -10 | xargs -r -n1 basename
  "
}

rollback_one() {
  local name="$1" host="$2" mode="$3" env_file="$4" requested_archive="$5"
  [ -n "$host" ] || die "$name host is empty"
  log "rollback $name ($host)"
  remote "$host" "
    set -e
    backup_root=\"\${ROLLBACK_BACKUP_DIR:-$(dirname "$REMOTE_DIR")/anti_pro_release_backups}\"
    requested='$requested_archive'
    if [ \"\$requested\" = 'latest' ]; then
      archive=\$(ls -1t \"\$backup_root\"/*.tar.gz 2>/dev/null | head -1)
    elif [ -f \"\$backup_root/\$requested\" ]; then
      archive=\"\$backup_root/\$requested\"
    elif [ -f \"\$requested\" ]; then
      archive=\"\$requested\"
    else
      archive=\"\$backup_root/\$requested.tar.gz\"
    fi
    test -f \"\$archive\" || { echo \"missing rollback archive: \$requested\" >&2; exit 1; }

    work_dir=\"$(dirname "$REMOTE_DIR")/.anti_pro_rollback_\$(date +%Y%m%d-%H%M%S)_\$\$\"
    protected_dir=\"\$work_dir/protected\"
    extract_dir=\"\$work_dir/extract\"
    mkdir -p \"\$protected_dir\" \"\$extract_dir\"

    if [ -d '$REMOTE_DIR/cursor_sh/hermes_skills' ]; then
      mkdir -p \"\$protected_dir/cursor_sh\"
      cp -a '$REMOTE_DIR/cursor_sh/hermes_skills' \"\$protected_dir/cursor_sh/\"
    fi

    tar -C \"\$extract_dir\" -xzf \"\$archive\"
    restored=\"\$extract_dir/$(basename "$REMOTE_DIR")\"
    test -d \"\$restored\" || { echo \"invalid rollback archive: \$archive\" >&2; exit 1; }

    previous=\"$(dirname "$REMOTE_DIR")/$(basename "$REMOTE_DIR").rollback-before-\$(date +%Y%m%d-%H%M%S)\"
    if [ -d '$REMOTE_DIR' ]; then
      mv '$REMOTE_DIR' \"\$previous\"
    fi
    mv \"\$restored\" '$REMOTE_DIR'

    if [ -d \"\$protected_dir/cursor_sh/hermes_skills\" ]; then
      rm -rf '$REMOTE_DIR/cursor_sh/hermes_skills'
      mkdir -p '$REMOTE_DIR/cursor_sh'
      cp -a \"\$protected_dir/cursor_sh/hermes_skills\" '$REMOTE_DIR/cursor_sh/'
    fi

    cd '$REMOTE_DIR'
    test -f '$env_file' || { echo 'missing env file after rollback: $env_file' >&2; exit 1; }
    export BACKEND_ENV_FILE='$env_file'
    export DEPLOYMENT_MODE='$mode'
    docker compose up -d --remove-orphans
    curl -fsS http://127.0.0.1:8080/api/health
    echo
    echo \"rollback_archive=\$archive\"
    echo \"previous_saved_as=\$previous\"
    rm -rf \"\$work_dir\"
  "
}

list_env() {
  case "$1" in
    staging)
      list_one "staging external" "$STAGING_EXTERNAL_HOST"
      list_one "staging internal" "$STAGING_INTERNAL_HOST"
      ;;
    production)
      list_one "production external" "$PRODUCTION_EXTERNAL_HOST"
      list_one "production internal" "$PRODUCTION_INTERNAL_HOST"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

rollback_env() {
  local env_name="$1" archive="${2:-latest}"
  case "$env_name" in
    staging)
      rollback_one "staging external" "$STAGING_EXTERNAL_HOST" external "$STAGING_EXTERNAL_ENV" "$archive"
      rollback_one "staging internal" "$STAGING_INTERNAL_HOST" internal "$STAGING_INTERNAL_ENV" "$archive"
      ;;
    production)
      [ "${CONFIRM_PRODUCTION:-}" = "production" ] || die "Add CONFIRM_PRODUCTION=production to rollback production"
      rollback_one "production external" "$PRODUCTION_EXTERNAL_HOST" external "$PRODUCTION_EXTERNAL_ENV" "$archive"
      rollback_one "production internal" "$PRODUCTION_INTERNAL_HOST" internal "$PRODUCTION_INTERNAL_ENV" "$archive"
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
    list)
      list_env "${2:-}"
      ;;
    staging|production)
      rollback_env "$1" "${2:-latest}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
