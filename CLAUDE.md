# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProvidAI is a **multi-agent marketplace system** built with Strands SDK on Hedera, featuring **meta-tooling** (dynamic tool creation) as its core innovation. The system enables agents to discover, negotiate with, and execute tasks using marketplace agents through ERC-8004 protocol and x402 payments.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with required credentials (see Configuration section)

# Initialize database
python -c "from shared.database import Base, engine; Base.metadata.create_all(engine)"
```

### Running the Application
```bash
# Start API server (main entry point - Orchestrator agent)
python -m api.main
# Server runs at http://localhost:8000, docs at http://localhost:8000/docs

# Run individual agents (for testing)
python -m agents.orchestrator.agent
python -m agents.negotiator.agent
python -m agents.executor.agent  # Includes meta-tooling demo
python -m agents.verifier.agent
```

### Testing & Code Quality
```bash
# Run tests
pytest

# Format code
black .

# Lint code
ruff check .

# Type check
mypy .
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Configuration

Required environment variables in `.env`:

- **ANTHROPIC_API_KEY**: Your Anthropic API key (required)
- **HEDERA_ACCOUNT_ID**, **HEDERA_PRIVATE_KEY**: Hedera testnet credentials
- **DATABASE_URL**: PostgreSQL or SQLite connection string
- **ERC8004_REGISTRY_ADDRESS**, **ERC8004_RPC_URL**: ERC-8004 contract details
- **Agent models**: Default is `claude-3-7-sonnet-20250219` for all agents

## Architecture

### 4-Agent System

The system follows a hierarchical workflow:

```
Orchestrator (Coordinator)
    ├── Negotiator (Discovery & Payment)
    ├── Executor (Meta-Tooling & Execution)
    └── Verifier (Quality & Payment Release)
```

**Workflow**: User request → Orchestrator → Negotiator (discover agents) → Executor (create & run dynamic tools) → Verifier (validate & release payment)

### Agent Responsibilities

1. **Orchestrator** ([agents/orchestrator/](agents/orchestrator/))
   - Entry point for user requests (via FastAPI)
   - Creates TODO lists and task structure
   - Coordinates other agents as tools
   - Tools: `negotiator_agent`, `executor_agent`, `verifier_agent`, task management

2. **Negotiator** ([agents/negotiator/](agents/negotiator/))
   - Discovers agents via ERC-8004 registry
   - Evaluates pricing and reputation
   - Creates x402 payment requests and authorizes escrow
   - Tools: `discover_agents_by_capability`, `create_payment_request`, `authorize_payment`

3. **Executor** ([agents/executor/](agents/executor/)) ⭐ **META-TOOLING CORE**
   - **Dynamically generates Python tools** from agent metadata at runtime
   - Loads generated tools via `importlib` and executes them
   - Tools saved to [agents/executor/dynamic_tools/](agents/executor/dynamic_tools/)
   - Tools: `create_dynamic_tool`, `load_and_execute_tool`, `list_dynamic_tools`

4. **Verifier** ([agents/verifier/](agents/verifier/))
   - Verifies task completion and quality
   - Can execute code for validation (`run_verification_code`, `run_unit_tests`)
   - Web search for fact-checking (`search_web`, `verify_fact`)
   - Releases payments or triggers refunds
   - Tools: `verify_task_result`, `release_payment`, `reject_and_refund`

### Key Innovation: Meta-Tooling

**Meta-tooling** is the pattern where the Executor agent generates executable Python code at runtime:

1. Negotiator discovers an agent via ERC-8004 and retrieves metadata
2. Executor receives metadata with API spec (endpoint, method, parameters, auth)
3. `create_dynamic_tool()` in [agents/executor/tools/meta_tools.py](agents/executor/tools/meta_tools.py:16) generates Python code
4. Generated code saved to `agents/executor/dynamic_tools/{tool_name}.py`
5. `load_and_execute_tool()` loads the module via `importlib.util` and calls it
6. Tool usage tracked in database (`DynamicTool` model)

**Example**: When discovering a "data-analysis" agent, Executor generates a complete `analyze_sales_data.py` file with async function, error handling, and HTTP client code.

## Code Structure Patterns

### Agent Creation Pattern
All agents follow the same structure:
```python
# agents/{agent_name}/agent.py
from strands import Agent
from anthropic import Anthropic
from .system_prompt import {AGENT}_SYSTEM_PROMPT
from .tools import tool1, tool2, tool3

def create_{agent}_agent() -> Agent:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return Agent(
        client=client,
        model=os.getenv("{AGENT}_MODEL", "claude-3-7-sonnet-20250219"),
        system_prompt={AGENT}_SYSTEM_PROMPT,
        tools=[tool1, tool2, tool3]
    )
```

### Tool Implementation
Tools are async functions in `agents/{agent}/tools/*.py`:
- Must be imported in `agents/{agent}/tools/__init__.py`
- Return dictionaries with structured data
- Use `SessionLocal()` for database operations

### Database Models
Located in [shared/database/models.py](shared/database/models.py):
- **Task**: User requests and execution state
- **Agent**: Marketplace agent registry
- **Payment**: x402 payment tracking with escrow
- **DynamicTool**: Runtime-generated tools metadata

Use SQLAlchemy sessions:
```python
from shared.database import SessionLocal
db = SessionLocal()
try:
    # database operations
    db.commit()
finally:
    db.close()
```

## Protocols

### ERC-8004: Agent Discovery
- Smart contract for decentralized agent registry
- Contract: [shared/contracts/ERC8004Registry.sol](shared/contracts/ERC8004Registry.sol)
- Python client: [shared/protocols/erc8004.py](shared/protocols/erc8004.py)
- Agents register with metadata URIs (IPFS/HTTP)
- Discovery by capability tags

### x402: Payment Protocol
- Payment request/authorization/release flow
- Python implementation: [shared/protocols/x402.py](shared/protocols/x402.py)
- Escrow pattern: authorize → verify → release/refund
- Integrated with Hedera payments

## Working with Dynamic Tools

When modifying or extending meta-tooling:

1. **Tool generation logic**: [agents/executor/tools/meta_tools.py](agents/executor/tools/meta_tools.py) `_generate_tool_code()`
2. **Generated tools directory**: [agents/executor/dynamic_tools/](agents/executor/dynamic_tools/)
3. **Database tracking**: `DynamicTool` model stores code, metadata, usage count
4. **Tool templates**: Support basic, authenticated, and streaming patterns

Security considerations:
- Tools generated from ERC-8004 metadata (should be verified/trusted)
- API keys passed as parameters, never hardcoded
- All HTTP calls have 30s timeout
- Error handling returns structured error dicts

## API Integration

Main API: [api/main.py](api/main.py)

Key endpoint:
```bash
POST /execute
{
  "description": "Task description",
  "capability_requirements": "specific-capability",
  "budget_limit": 1.0,
  "min_reputation_score": 0.7,
  "verification_mode": "standard"
}
```

Returns orchestrator execution through full workflow (negotiator → executor → verifier).

## Important Notes

- **Agent coordination**: Orchestrator calls other agents as tools (not direct function calls)
- **Main branch**: Use `main` for PRs (current branch: `feat/research-agents`)
- **Model version**: All agents default to `claude-3-7-sonnet-20250219`
- **Hedera network**: Default is testnet
- **Database**: Supports PostgreSQL (production) or SQLite (development)
