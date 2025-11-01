# Hedera Marketplace - Multi-Agent System with Meta-Tooling

A sophisticated multi-agent marketplace built on Hedera using Strands SDK, featuring **dynamic tool creation** (meta-tooling) for seamless integration with discovered agents.

## Key Innovation: Meta-Tooling

The **Executor agent** dynamically creates Python tools at runtime to integrate with marketplace agents discovered via ERC-8004. This enables:

- 🔧 **Runtime Tool Generation**: Create custom integration tools on-the-fly
- 🔄 **Dynamic Discovery**: Find and integrate with any marketplace agent
- 🚀 **Automatic Integration**: No manual coding for each new agent
- 📦 **Protocol Support**: ERC-8004,  x402 payments

## Architecture

### 4-Agent System

```
┌─────────────────┐
│  Orchestrator   │  Task analysis, TODO creation
└────────┬────────┘
         │
    ┌────┴─────┬─────────┬─────────┐
    │          │         │         │
┌───▼──────┐ ┌─▼────────┐ ┌──────▼──┐
│Negotiator│ │ Executor │ │Verifier │
└──────────┘ └──────────┘ └─────────┘
ERC-8004     Meta-tooling  Quality
x402 Payment Dynamic Tools Checks
```

### Agent Responsibilities

1. **Orchestrator** (`agents/orchestrator/`)
   - Analyzes user requests
   - Creates structured TODO lists
   - Coordinates agent workflows

2. **Negotiator** (`agents/negotiator/`)
   - Discovers agents via ERC-8004
   - Evaluates pricing and reputation
   - Creates x402 payment requests
   - Authorizes payments (escrow)

3. **Executor** (`agents/executor/`) ⭐ **META-TOOLING**
   - **Dynamically creates tools** for discovered agents
   - Loads and executes runtime-generated tools
   - Handles execution errors

4. **Verifier** (`agents/verifier/`)
   - Verifies task completion
   - Validates output schemas
   - Releases authorized payments
   - Rejects and refunds failed tasks

## Meta-Tooling Example

### How It Works

```python
# 1. Negotiator discovers an agent
agents = await find_agents("data-analysis")
# Returns: Agent metadata with API spec

# 2. Executor receives metadata
agent_metadata = {
    "agent_id": "data-analyzer-001",
    "endpoint": "https://api.example.com/analyze",
    "capabilities": ["data-analysis"]
}

tool_spec = {
    "endpoint": "https://api.example.com/analyze",
    "method": "POST",
    "parameters": [
        {"name": "data", "type": "str"},
        {"name": "analysis_type", "type": "str"}
    ],
    "auth_type": "bearer"
}

# 3. Executor creates dynamic tool
result = await create_dynamic_tool(
    task_id="task-123",
    tool_name="analyze_sales_data",
    agent_metadata=agent_metadata,
    tool_spec=tool_spec
)
# Generates: agents/executor/dynamic_tools/analyze_sales_data.py

# 4. Executor loads and executes the tool
result = await load_and_execute_tool(
    tool_name="analyze_sales_data",
    parameters={
        "data": "date,sales\\n2024-01-01,1000",
        "analysis_type": "trends",
        "api_key": "sk-..."
    }
)
# Tool is loaded dynamically and executed
```

### Generated Tool Example

The Executor creates tools like this automatically:

```python
# File: agents/executor/dynamic_tools/analyze_sales_data.py

async def analyze_sales_data(data: str, analysis_type: str, api_key: str = None) -> dict:
    """
    Call the discovered sales data analyzer agent.

    Args:
        data: CSV sales data
        analysis_type: Type of analysis (summary, trends, forecast)
        api_key: Optional API key

    Returns:
        Analysis results
    """
    import httpx

    endpoint = "https://api.example.com/analyze"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"data": data, "type": analysis_type},
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
        )
        response.raise_for_status()
        return response.json()
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- Hedera testnet account
- Anthropic API key

### Setup

```bash
# Clone repository
git clone <repository-url>
cd ProvidAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python -c "from shared.database import Base, engine; Base.metadata.create_all(engine)"
```

### Configuration

Edit `.env`:

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Hedera Testnet
HEDERA_NETWORK=testnet
HEDERA_ACCOUNT_ID=0.0.12345
HEDERA_PRIVATE_KEY=302e...

# Database
DATABASE_URL=postgresql://user:pass@localhost/hedera_marketplace
# Or: DATABASE_URL=sqlite:///./hedera_marketplace.db

# ERC-8004
ERC8004_REGISTRY_ADDRESS=0x...
ERC8004_RPC_URL=https://testnet.hashio.io/api

# API
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=<generate with: openssl rand -hex 32>
```

## Usage

### Run Agents as A2A Services (optional)

Each specialist agent can be hosted as a lightweight HTTP service using the bundled A2A shim.
This lets the orchestrator delegate work over the network instead of instantiating agents
locally. In separate terminals run:

```bash
python -m agents.negotiator.server
python -m agents.executor.server
python -m agents.verifier.server
```

Configure endpoint URLs in `.env` via `NEGOTIATOR_A2A_URL`, `EXECUTOR_A2A_URL`, and
`VERIFIER_A2A_URL`. When unset, the orchestrator falls back to in-process execution.

Emitted A2A envelopes (proposal, authorized, released, refunded) are now persisted
for dashboards. Query `GET /a2a/events` on the API to inspect the latest traffic, or
add a webhook target by setting `A2A_EVENT_WEBHOOK_URL` to a comma-separated list of
endpoints.

### Start API Server

```bash
python -m api.main
# Server runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Run Individual Agents

```bash
# Orchestrator
python -m agents.orchestrator.agent

# Negotiator
python -m agents.negotiator.agent

# Executor (with meta-tooling demo)
python -m agents.executor.agent

# Verifier
python -m agents.verifier.agent
```

### API Examples

#### Create a Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Analyze Q1 Sales Data",
    "description": "Find a data analysis agent and analyze our Q1 sales"
  }'
```

#### Discover Marketplace Agents

```bash
curl -X POST http://localhost:8000/api/agents/discover \
  -H "Content-Type: application/json" \
  -d '{"capability": "data-analysis"}'
```

#### Create Dynamic Tool

```bash
curl -X POST http://localhost:8000/api/tools \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "tool_name": "analyze_sales_data",
    "agent_metadata": {
      "agent_id": "agent-456",
      "name": "Sales Analyzer"
    },
    "tool_spec": {
      "endpoint": "https://api.example.com/analyze",
      "method": "POST",
      "parameters": [
        {"name": "data", "type": "str", "description": "CSV data"},
        {"name": "analysis_type", "type": "str", "description": "Analysis type"}
      ],
      "auth_type": "bearer",
      "description": "Analyze sales data"
    }
  }'
```

#### Execute Dynamic Tool

```bash
curl -X POST http://localhost:8000/api/tools/analyze_sales_data/execute \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "data": "date,sales\\n2024-01-01,1000",
      "analysis_type": "trends",
      "api_key": "sk-..."
    }
  }'
```

## Project Structure

```
ProvidAI/
├── agents/                    # 4-agent system
│   ├── orchestrator/         # Task coordination
│   │   ├── agent.py
│   │   ├── system_prompt.py
│   │   └── tools/
│   ├── negotiator/           # ERC-8004 & x402
│   │   ├── agent.py
│   │   ├── system_prompt.py
│   │   └── tools/
│   ├── executor/             # ⭐ META-TOOLING
│   │   ├── agent.py
│   │   ├── system_prompt.py
│   │   ├── tools/
│   │   │   └── meta_tools.py  # Dynamic tool creation
│   │   └── dynamic_tools/     # Runtime-generated tools
│   └── verifier/             # Quality & payments
│       ├── agent.py
│       ├── system_prompt.py
│       └── tools/
├── shared/                    # Shared utilities
│   ├── hedera/               # Hedera SDK client
│   ├── protocols/            # ERC-8004, x402
│   ├── database/             # SQLAlchemy models
│   └── contracts/            # Solidity contracts
│       └── ERC8004Registry.sol
├── api/                      # FastAPI backend
│   ├── main.py
│   ├── routes/
│   └── middleware.py
├── requirements.txt
├── .env.example
└── README.md
```

## Protocols

### ERC-8004: Agent Discovery

Decentralized agent registry on Hedera:

- Smart contract at `shared/contracts/ERC8004Registry.sol`
- Agents register with metadata URIs (IPFS/HTTP)
- Capability-based discovery
- Python integration via Web3.py

### x402: Payments

Payment protocol for agent-to-agent transactions:

- Payment request creation
- Authorization (escrow pattern)
- Release on verification
- Refunds for failures

## Meta-Tooling Deep Dive

### Why Meta-Tooling?

Traditional approach:
```python
# Manual integration for each agent
def call_agent_a(): ...
def call_agent_b(): ...
def call_agent_c(): ...
# Requires coding for each new agent
```

Meta-tooling approach:
```python
# Automatic integration
tool_spec = discover_agent_api_spec()
create_dynamic_tool(tool_spec)  # Generated automatically
load_and_execute_tool()         # Use immediately
```

### Tool Creation Flow

1. **Discovery**: Negotiator finds agent via ERC-8004
2. **Spec Extraction**: Parse agent metadata for API details
3. **Code Generation**: `_generate_tool_code()` creates Python function
4. **Persistence**: Save to `dynamic_tools/` + database
5. **Loading**: `importlib.util` loads module dynamically
6. **Execution**: Call like any Strands SDK tool

### Tool Templates

See `agents/executor/tools/execution_tools.py` for templates:

- **Basic**: Simple POST request
- **Authenticated**: Bearer token/API key
- **Streaming**: Async streaming responses

### Security

- Tools generated from verified ERC-8004 metadata
- API keys passed as parameters (not hardcoded)
- Error handling and timeouts
- Usage tracking in database

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format
black .

# Lint
ruff check .

# Type check
mypy .
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Deployment

### Deploy ERC-8004 Contract

```bash
# Using Foundry
forge create --rpc-url https://testnet.hashio.io/api \
  --private-key $HEDERA_PRIVATE_KEY \
  shared/contracts/ERC8004Registry.sol:ERC8004Registry
```

### Deploy API

```bash
# Using Docker
docker build -t hedera-marketplace .
docker run -p 8000:8000 --env-file .env hedera-marketplace

# Or with gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Examples

### Full Workflow Example

```python
from agents.orchestrator import create_orchestrator_agent
from agents.negotiator import create_negotiator_agent
from agents.executor import create_executor_agent
from agents.verifier import create_verifier_agent

# 1. User request to Orchestrator
orchestrator = create_orchestrator_agent()
task = await orchestrator.run(
    "Analyze our Q1 sales data and generate insights"
)

# 2. Orchestrator delegates to Negotiator
negotiator = create_negotiator_agent()
agents = await negotiator.run(
    "Find a data analysis agent and set up payment of 0.5 HBAR"
)

# 3. Negotiator hands off to Executor
executor = create_executor_agent()
result = await executor.run(f"""
    Create a tool for agent {agents[0]['agent_id']} and analyze this data:
    {sales_data}
""")
# Executor creates dynamic tool and executes it

# 4. Verifier checks quality and releases payment
verifier = create_verifier_agent()
await verifier.run(f"""
    Verify task {task_id} and release payment {payment_id}
""")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run code quality checks
5. Submit pull request

## License

MIT

## Resources

- [Strands SDK Documentation](https://github.com/anthropics/strands)
- [Hedera Documentation](https://docs.hedera.com/)
- [ERC-8004 Specification](https://eips.ethereum.org/EIPS/eip-8004)

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/ProvidAI/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/ProvidAI/discussions)

---

Built with ❤️ using [Anthropic Claude](https://anthropic.com) and [Hedera](https://hedera.com)
