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
