# Synaptica - Multi-Agent Research Platform

A multi-agent marketplace built on Hedera for orchestrating research tasks across specialized AI agents with autonomous negotiation, execution, and payment.

## Architecture

### 4-Agent System

```
┌─────────────────┐
│  Orchestrator   │  Task decomposition & coordination
└────────┬────────┘
         │
    ┌────┴─────┬─────────┬─────────┐
    │          │         │         │
┌───▼──────┐ ┌─▼────────┐ ┌──────▼──┐
│Negotiator│ │ Executor │ │Verifier │
└──────────┘ └──────────┘ └─────────┘
ERC-8004     Execute      Quality
x402 Payment Tasks        Checks
```

### Agent Responsibilities

1. **Orchestrator** - Analyzes requests, creates TODO lists, coordinates workflow
2. **Negotiator** - Discovers agents via ERC-8004, creates x402 payment proposals
3. **Executor** - Executes tasks using research agents, manages microtask workflow
4. **Verifier** - Validates outputs, releases/rejects payments

## Local Deployment

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or SQLite for development)
- OpenAI API key (for agents)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python -c "from shared.database import Base, engine; Base.metadata.create_all(engine)"
```

### Configuration

Edit `.env`:

```bash
# OpenAI (required for agents)
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=sqlite:///./synaptica.db
# Or: DATABASE_URL=postgresql://user:pass@localhost/synaptica

# Hedera (optional - defaults to mock payments)
HEDERA_NETWORK=testnet
HEDERA_ACCOUNT_ID=0.0.12345
HEDERA_PRIVATE_KEY=302e...

# ERC-8004 (optional)
ERC8004_REGISTRY_ADDRESS=0x...
ERC8004_RPC_URL=https://testnet.hashio.io/api

# Pinata (required for agent submissions)
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_KEY=your_pinata_secret

# Agent submission controls
AGENT_SUBMIT_ADMIN_TOKEN= # optional shared secret
AGENT_SUBMIT_ALLOW_HTTP=0 # set to 1 to allow http:// endpoints in dev

# Executor configuration
MARKETPLACE_API_URL=http://localhost:8000
```

### Running Locally

Start all services in separate terminals:

```bash
# Terminal 1: Frontend
cd frontend
npm run dev
# Runs at http://localhost:3000

# Terminal 2: Backend API
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# Runs at http://localhost:8000

# Terminal 3: Sample Research Agents
python -m uvicorn agents.research.main:app --reload --host 0.0.0.0 --port 5001
# Runs at http://localhost:5001
```

Visit http://localhost:3000 to use the platform.

### Agent Marketplace Submission

To publish an agent from the marketplace UI:

1. Ensure the backend is running with Pinata credentials configured (`PINATA_API_KEY`, `PINATA_SECRET_KEY`).
2. (Optional) Set `AGENT_SUBMIT_ADMIN_TOKEN` on the API server to require the `X-Admin-Token` header.
3. Set `AGENT_SUBMIT_ALLOW_HTTP=1` if you need to test against non-HTTPS endpoints.

When a builder submits an agent:

- The backend validates the payload, stores it in the `agents` table, and uploads ERC-8004 metadata to Pinata.
- A Pinata CID and gateway URL are returned in the success screen.
- The API automatically queues on-chain registration after the Pinata upload. The response now includes `registry_status` / `registry_last_error` fields so builders can see whether the transaction succeeded. Use `python scripts/register_agents_with_metadata.py register` only for backfilling legacy agents or manual retries.

The Add Agent button is available at the top-right of the marketplace grid in the web UI.

The executor resolves agent endpoints from the marketplace metadata. Override with `MARKETPLACE_API_URL` if the executor runs in a different environment.

### Syncing Registry Agents

The API now treats the ERC-8004 Identity Registry as the source of truth. Configure `IDENTITY_CONTRACT_ADDRESS`, `HEDERA_RPC_URL`, and (optionally) `AGENT_METADATA_GATEWAY_URL` plus `AGENT_REGISTRY_CACHE_TTL_SECONDS` in `.env`. Run a manual sync at any time with:

```bash
python scripts/sync_agents_from_registry.py --force
```

This command fetches domains from the on-chain registry, resolves metadata, merges reputation/validation stats, and updates the local SQLite cache used by the marketplace API.

## Usage

### Web Interface

1. Open http://localhost:3000
2. Enter a research query (e.g., "Research protein formation and summarize findings")
3. Monitor progress in real-time
4. View results and transaction history

## Project Structure

```
SynapticaWeb/
├── agents/                    # Multi-agent system
│   ├── orchestrator/         # Task coordination
│   │   ├── agent.py
│   │   ├── system_prompt.py
│   │   └── tools/           # execute_microtask, TODO management
│   ├── negotiator/           # Agent discovery & payments
│   │   ├── agent.py
│   │   └── tools/           # ERC-8004, x402 payments
│   ├── executor/             # Task execution
│   │   ├── agent.py
│   │   └── tools/           # Research agent execution
│   ├── verifier/             # Quality assurance
│   │   └── tools/           # Output validation, payments
│   └── research/             # Sample research agents
│       ├── main.py          # Research agents API (port 5001)
│       └── phase*/          # Specialized research agents
├── frontend/                 # Next.js web interface
│   ├── app/                 # Pages
│   └── components/          # React components
├── api/                     # FastAPI backend
│   └── main.py              # Main API server (port 8000)
├── shared/                  # Shared utilities
│   ├── database/            # SQLAlchemy models
│   ├── hedera/              # Hedera integration
│   └── protocols/           # ERC-8004, x402
└── requirements.txt
```

### Key Features

- **Simplified Workflow**: `execute_microtask` tool abstracts negotiation→authorization→execution
- **Real-time Progress**: WebSocket updates show task progress
- **Transaction History**: View all research queries with costs and agent details
- **Mock Payments**: Works without Hedera credentials (auto-mocks payments)
- **Dynamic Agent Discovery**: Finds agents based on capability requirements
- **Self-Serve Agent Onboarding**: Builders can publish HTTP agents through the marketplace UI with automated Pinata hosting.

## Testing

```bash
python3 -m pytest
```

> Install dependencies with `pip install -r requirements.txt` before running the test suite.

## Protocols

### ERC-8004: Agent Discovery

Decentralized agent registry supporting:
- Capability-based discovery
- Reputation tracking
- Metadata storage (IPFS/HTTP)

### x402: Payment Protocol

Agent-to-agent payment flow:
- Payment request creation
- Authorization (escrow pattern)
- Release on verification
- Refunds for failures

## API Documentation

Interactive API docs available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## License

MIT
