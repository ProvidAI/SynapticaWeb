#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f .env ]]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT

start_server() {
  local name=$1
  shift
  echo "Starting ${name}..."
  "$@" &
  local pid=$!
  PIDS+=("${pid}")
  echo "  ${name} PID: ${pid}"
}

start_server "Negotiator A2A server" python3 -m agents.negotiator.server
start_server "Executor A2A server" python3 -m agents.executor.server
start_server "Verifier A2A server" python3 -m agents.verifier.server

echo "All A2A servers are running. Press Ctrl+C to stop."
wait
