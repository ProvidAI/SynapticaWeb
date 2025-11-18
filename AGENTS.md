# Repository Guidelines

## Project Structure & Module Organization
Core services live in `api/` (FastAPI orchestrator, middleware, routes) and `agents/` (orchestrator, negotiator, executor, verifier, plus sample `research/` service). The Next.js marketplace and Zustand state sit in `frontend/`, while Hedera/protocol helpers and ORM models stay in `shared/`. Scripts such as `register_agents_with_metadata.py` belong in `scripts/`, tests in `tests/`, and project docs, diagrams, and published metadata in `docs/` and `agent_metadata/`.

## Build, Test, and Development Commands
- Activate the repo-standard `.venv` before running any Python command: `source .venv/bin/activate` (create it once via `python -m venv .venv`).
- Prefer `uv pip install -r requirements.txt` for dependency installation when the `uv` CLI is present; fall back to `pip install -r requirements.txt` otherwise.
- `python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` – run the orchestrator/API.
- `python -m uvicorn agents.research.main:app --reload --port 5000` – boot sample research agents.
- `cd frontend && npm install && npm run dev` – serve the marketplace UI at `http://localhost:3000`.
- `python -m pytest tests` – run backend and agent suites; add `-k` to scope.
- `cd frontend && npm run lint` – enforce Next.js/ESLint rules.

## Coding Style & Naming Conventions
Python code follows PEP 8 with four-space indentation and typed signatures; functions/vars stay `snake_case`, classes `PascalCase`, and config constants uppercase with env reads centralized. Frontend TypeScript uses two-space indentation, single quotes, and `PascalCase` React components inside `frontend/components` or `frontend/app`. Place reusable helpers in `shared/` (backend) or `frontend/lib` (UI) rather than duplicating logic.

## Testing Guidelines
Keep unit and integration coverage in `tests/`, naming files after the target module (e.g., `tests/agents/test_negotiator.py`). Prefer deterministic fixtures that mock Hedera, Pinata, and marketplace calls, and assert progress updates via `shared.task_progress`. Until component tests land, pair UI changes with `npm run lint` and short notes on any manual checks (agent submission, Pinata upload).

## Commit & Pull Request Guidelines
History follows Conventional Commits (`feat(frontend): …`, `docs: …`, `fix:`). Keep commits focused, reference related issues in the body, and cap subjects at 72 characters. Pull requests must summarize behavior changes, attach screenshots or API traces for user-visible work, and call out schema/env updates (such as `AGENT_SUBMIT_ADMIN_TOKEN`) plus validation steps.

## Security & Configuration Tips
Use `.env.example` as the single source of truth for new variables; never commit `.env`, secrets, or local SQLite dumps. Inject OpenAI, Hedera, and Pinata credentials through env vars or a secret manager. Only set `AGENT_SUBMIT_ALLOW_HTTP=1` for local work and reset before deployment. Review files added to `agent_metadata/` to ensure no sensitive payloads leak.
