#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[entrypoint] $*"
}

bool_is_true() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if bool_is_true "${AUTO_LOAD_DATA:-1}"; then
  if [[ "${DATA_BACKEND:-database}" == "database" ]]; then
    log "Ensuring SQLite database is hydrated"
    args=()
    if bool_is_true "${RESET_DB_ON_START:-0}"; then
      log "RESET_DB_ON_START enabled"
      args+=("--reset-db")
    elif bool_is_true "${SKIP_DB_IF_EXISTS:-1}"; then
      args+=("--skip-if-exists")
    fi
    python scripts/load_parquet_to_db.py "${args[@]}"
  elif bool_is_true "${USE_LOCAL_DATA:-0}"; then
    log "Bootstrapping local parquet data"
    python scripts/bootstrap_local_data.py
  else
    log "AUTO_LOAD_DATA enabled but no matching data backend workflow"
  fi
else
  log "AUTO_LOAD_DATA disabled; skipping data bootstrap"
fi

UVICORN_APP=${UVICORN_APP:-app.main:app}
UVICORN_HOST=${API_HOST:-0.0.0.0}
UVICORN_PORT=${API_PORT:-8000}

cmd=("uvicorn" "$UVICORN_APP" "--host" "$UVICORN_HOST" "--port" "$UVICORN_PORT")

if [[ -n "${UVICORN_WORKERS:-}" ]]; then
  cmd+=("--workers" "${UVICORN_WORKERS}")
fi

if bool_is_true "${UVICORN_RELOAD:-0}"; then
  cmd+=("--reload")
fi

log "Starting API with command: ${cmd[*]}"
exec "${cmd[@]}"
