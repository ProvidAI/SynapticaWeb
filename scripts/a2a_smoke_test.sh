#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

LOG_DIR="${ROOT_DIR}/.logs"
mkdir -p "${LOG_DIR}"

declare -a CHILD_PIDS=()

cleanup() {
  local exit_code=$?
  if [[ ${#CHILD_PIDS[@]} -gt 0 ]]; then
    echo "\nStopping agent processes..."
    for pid in "${CHILD_PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
      fi
    done
  fi
  exit "$exit_code"
}

trap cleanup EXIT

require_env() {
  local name=$1
  if [[ -z "${!name:-}" ]]; then
    echo "[ERROR] Environment variable $name must be set." >&2
    exit 1
  fi
}

wait_for_endpoint() {
  local url=$1
  local name=$2
  local retries=30
  local delay=2

  echo "Waiting for $name at $url"
  for ((i=1; i<=retries; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "$name is ready"
      return 0
    fi
    sleep "$delay"
  done
  echo "[ERROR] $name did not become ready in time" >&2
  return 1
}

start_agent() {
  local name=$1
  local module=$2
  local log_file="${LOG_DIR}/${name}.log"

  echo "Starting $name (python -m ${module})"
  (
    cd "$ROOT_DIR"
    PYTHONUNBUFFERED=1 python3 -m "$module"
  ) >"$log_file" 2>&1 &
  local pid=$!
  CHILD_PIDS+=($pid)
  echo "$name PID: $pid (logs: $log_file)"
}

# ---------------------------------------------------------------------------
# 1. Check required environment
# ---------------------------------------------------------------------------
require_env OPENAI_API_KEY

# Ensure database schema exists (idempotent)
echo "Ensuring database schema..."
python3 - <<'PY'
from shared.database import Base, engine

Base.metadata.create_all(bind=engine)
print("Database tables created (if missing).")
PY

# Provide safe defaults for local dry runs
# export HEDERA_ACCOUNT_ID="${HEDERA_ACCOUNT_ID:-0.0.demo-client}"
# export TASK_ESCROW_MARKETPLACE_TREASURY="${TASK_ESCROW_MARKETPLACE_TREASURY:-0x0000000000000000000000000000000000000001}"

# ---------------------------------------------------------------------------
# 2. Launch agent servers
# ---------------------------------------------------------------------------
start_agent "negotiator" "agents.negotiator.server"
wait_for_endpoint "http://127.0.0.1:9101/.well-known/agent.json" "Negotiator"

start_agent "executor" "agents.executor.server"
wait_for_endpoint "http://127.0.0.1:9102/.well-known/agent.json" "Executor"

start_agent "verifier" "agents.verifier.server"
wait_for_endpoint "http://127.0.0.1:9103/.well-known/agent.json" "Verifier"

export NEGOTIATOR_A2A_URL="${NEGOTIATOR_A2A_URL:-http://127.0.0.1:9101}"
export EXECUTOR_A2A_URL="${EXECUTOR_A2A_URL:-http://127.0.0.1:9102}"
export VERIFIER_A2A_URL="${VERIFIER_A2A_URL:-http://127.0.0.1:9103}"

echo "\nA2A endpoints configured:" \
     "\n  NEGOTIATOR_A2A_URL=${NEGOTIATOR_A2A_URL}" \
     "\n  EXECUTOR_A2A_URL=${EXECUTOR_A2A_URL}" \
     "\n  VERIFIER_A2A_URL=${VERIFIER_A2A_URL}" \
     "\n"

# ---------------------------------------------------------------------------
# 3. Orchestrator -> Negotiator smoke test (via tool invocation)
# ---------------------------------------------------------------------------
echo "Running orchestrator -> negotiator smoke test..."

python3 - <<'PY'
import json
from agents.orchestrator.tools.agent_tools import negotiator_agent

result = negotiator_agent(
    task_id="a2a-smoke-task",
    capability_requirements="Provide a short acknowledgement message for the smoke test.",
    budget_limit=10.0,
    min_reputation_score=0.5,
)

print("Negotiator tool result:")
print(json.dumps(result, indent=2))
PY

# ---------------------------------------------------------------------------
# 4. Direct A2A ping of executor & verifier endpoints to ensure reachability
# ---------------------------------------------------------------------------
echo "\nPinging executor and verifier endpoints via A2A client..."

python3 - <<'PY'
import asyncio
import os
from shared.a2a.client import A2AAgentClient


async def ping(url: str, label: str) -> None:
    client = A2AAgentClient(url)
    card = await client.get_agent_card()
    print(f"{label} card: {card.name} ({card.version})")
    try:
        response = await client.invoke_text("Hello from A2A smoke test")
        print(f"{label} response snippet: {response[:200]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label} invocation failed: {exc}")


async def main():
    await asyncio.gather(
        ping(os.environ["EXECUTOR_A2A_URL"], "Executor"),
        ping(os.environ["VERIFIER_A2A_URL"], "Verifier"),
    )


asyncio.run(main())
PY

# ---------------------------------------------------------------------------
# 5. Payment flow test via negotiated tools
# ---------------------------------------------------------------------------
echo "\nCreating and authorizing a demo payment..."

python3 - <<'PY'
import asyncio
import json
import os
from agents.negotiator.tools.payment_tools import create_payment_request
from agents.orchestrator.tools.agent_tools import authorize_payment_request
from agents.verifier.tools.payment_tools import release_payment


async def main() -> None:
    payment = await create_payment_request(
        task_id="a2a-smoke-task",
        from_agent_id="orchestrator-agent",
        to_agent_id="worker-agent",
        to_hedera_account=os.environ.get("SMOKE_WORKER_ACCOUNT", "0.0.987654"),
        amount=0.01,
        description="Hackathon A2A smoke test",
    )
    print("Payment proposal created:\n", json.dumps(payment, indent=2))

    try:
        authorization = await asyncio.to_thread(
            authorize_payment_request,
            payment["payment_id"],
        )
        print("Authorization result:\n", json.dumps(authorization, indent=2))
    except Exception as exc:  # noqa: BLE001
        print("Authorization failed:", exc)
        return

    try:
        release = await release_payment(payment["payment_id"], verification_notes="Smoke test release")
        print("Release result:\n", json.dumps(release, indent=2))
    except Exception as exc:  # noqa: BLE001
        print("Release failed:", exc)


asyncio.run(main())
PY

# ---------------------------------------------------------------------------
# 6. Display recent A2A events stored in the database
# ---------------------------------------------------------------------------
echo "\nRecent A2A events:" 

python3 - <<'PY'
from shared.database import SessionLocal
from shared.database.models import A2AEvent

session = SessionLocal()
try:
    events = (
        session.query(A2AEvent)
        .order_by(A2AEvent.timestamp.desc(), A2AEvent.id.desc())
        .limit(5)
        .all()
    )
    if not events:
        print("No events recorded yet.")
    for event in events:
        print(f"- [{event.timestamp}] {event.message_type} {event.from_agent} -> {event.to_agent} (thread {event.thread_id})")
except Exception as exc:  # noqa: BLE001
    print(f"Failed to load events: {exc}")
finally:
    session.close()
PY

echo "\nSmoke test complete. Review logs under ${LOG_DIR} for detailed output."
