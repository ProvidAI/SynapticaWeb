# ProvidAI Agent Registry

## Overview

ProvidAI now has **15 autonomous research agents** registered in the local database, implementing the complete 5-phase research pipeline from the agent-plan.pdf.

## Registry Summary

- **Total Agents**: 15
- **Status**: All active
- **Total Pricing Range**: 0.05 - 0.25 HBAR per task
- **Registry Type**: Local SQLite database (blockchain registration pending)

## Agents by Phase

### Phase 1: Ideation (3 agents)

1. **Research Problem Framer** (`problem-framer-001`)
   - Pricing: 0.10 HBAR per framing
   - Transforms vague queries into formal research questions
   - Status: ✅ Fully implemented & tested

2. **Research Feasibility Analyst** (`feasibility-analyst-001`)
   - Pricing: 0.08 HBAR per analysis
   - Evaluates research feasibility (data, resources, complexity, constraints)
   - Status: ✅ Implemented

3. **Research Goal Planner** (`goal-planner-001`)
   - Pricing: 0.10 HBAR per plan
   - Creates structured research plans with objectives, milestones, tasks
   - Status: ✅ Implemented

### Phase 2: Knowledge Retrieval (2 agents)

4. **Academic Literature Miner** (`literature-miner-001`)
   - Pricing: 0.05 HBAR per paper
   - Searches ArXiv, Semantic Scholar for relevant papers
   - Status: ✅ Fully implemented & tested

5. **Knowledge Synthesizer** (`knowledge-synthesizer-001`)
   - Pricing: 0.15 HBAR per synthesis
   - Synthesizes knowledge from multiple papers, identifies patterns and gaps
   - Status: ✅ Implemented

### Phase 3: Experimentation (3 agents)

6. **Hypothesis Designer** (`hypothesis-designer-001`)
   - Pricing: 0.12 HBAR per design
   - Creates testable hypotheses and experiment protocols
   - Status: ✅ Implemented

7. **Experiment Runner** (`experiment-runner-001`)
   - Pricing: 0.20 HBAR per experiment
   - Executes experiments, simulations, and data collection
   - Status: ✅ Implemented

8. **Code Generator** (`code-generator-001`)
   - Pricing: 0.15 HBAR per generation
   - Generates experimental code, analysis scripts, visualizations
   - Status: ✅ Implemented

### Phase 4: Interpretation (3 agents)

9. **Insight Generator** (`insight-generator-001`)
   - Pricing: 0.14 HBAR per task
   - Extracts insights, identifies patterns, draws conclusions
   - Status: ✅ Implemented

10. **Bias Detector** (`bias-detector-001`)
    - Pricing: 0.11 HBAR per detection
    - Detects biases in methodology, data, and interpretations
    - Status: ✅ Implemented

11. **Compliance Checker** (`compliance-checker-001`)
    - Pricing: 0.09 HBAR per check
    - Verifies ethical, regulatory, and standards compliance
    - Status: ✅ Implemented

### Phase 5: Publication (4 agents)

12. **Research Paper Writer** (`paper-writer-001`)
    - Pricing: 0.25 HBAR per paper
    - Writes academic papers in proper format with citations
    - Status: ✅ Implemented

13. **Peer Reviewer** (`peer-reviewer-001`)
    - Pricing: 0.18 HBAR per review
    - Provides peer review feedback on quality, rigor, contribution
    - Status: ✅ Implemented

14. **Reputation Manager** (`reputation-manager-001`)
    - Pricing: 0.05 HBAR per update
    - Updates agent reputations based on performance
    - Status: ✅ Implemented

15. **Research Archiver** (`archiver-001`)
    - Pricing: 0.07 HBAR per archive
    - Archives research to IPFS and blockchain for permanence
    - Status: ✅ Implemented

## Usage

### View All Agents
```bash
python scripts/list_all_agents.py
```

### Register New Agents
```bash
python scripts/register_all_agents.py
```

### Run Research Pipeline
```bash
python scripts/demo_research_pipeline.py
```

### View Database Artifacts
```bash
python scripts/view_artifacts.py
python scripts/interactive_db_viewer.py
```

## Agent Capabilities

Each agent is registered with:
- ✅ Unique agent ID
- ✅ Descriptive name
- ✅ Capabilities list (for ERC-8004 discovery)
- ✅ Pricing model (pay-per-use in HBAR)
- ✅ Status tracking
- ✅ Reputation scores
- ✅ Metadata (model, creation date, etc.)

## Current State

### ✅ Local Registry
- All 15 agents registered in SQLite database
- Capability-based discovery implemented
- Reputation tracking active
- Payment simulation working

### ⚠️ Blockchain Registry (Pending)
- ERC-8004 contract not yet deployed on Hedera testnet
- Agents not yet on-chain
- Payments simulated (not actual HBAR transactions)
- IPFS integration pending

## Next Steps

1. **Deploy ERC-8004 Registry Contract** on Hedera testnet
2. **Register agents on-chain** with metadata URIs
3. **Implement real x402 micropayments** using Hedera SDK
4. **Upload agent metadata to IPFS** for decentralized storage
5. **Enable on-chain discovery** via smart contract queries
6. **Integrate with research pipeline** for automatic agent selection

## Cost Estimates

Estimated costs for a complete research pipeline:
- **Phase 1 (Ideation)**: ~0.28 HBAR (3 agents)
- **Phase 2 (Knowledge)**: ~0.50-1.00 HBAR (depending on # papers)
- **Phase 3 (Experimentation)**: ~0.47 HBAR (3 agents)
- **Phase 4 (Interpretation)**: ~0.34 HBAR (3 agents)
- **Phase 5 (Publication)**: ~0.55 HBAR (4 agents)

**Total Pipeline Cost**: ~2-3 HBAR per research project

## Architecture

```
User Query
    ↓
Research Pipeline Orchestrator
    ↓
┌─────────────────────────────────────┐
│  Local Agent Registry (SQLite)      │
│  - Agent discovery                  │
│  - Reputation tracking              │
│  - Payment simulation               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  15 Autonomous Research Agents      │
│  - Phase-specific tasks             │
│  - JSON-based communication         │
│  - OpenAI GPT-4 powered             │
└─────────────────────────────────────┘
    ↓
Research Artifacts → Database → IPFS (pending)
```

## Files

- Agent implementations: `agents/research/phase[1-5]_*/*/agent.py`
- Registry scripts: `scripts/list_all_agents.py`, `scripts/register_all_agents.py`
- Database models: `shared/database/models.py`
- ERC-8004 protocol: `shared/protocols/erc8004.py`

---

*Generated on November 1, 2025*
*ProvidAI - Autonomous Research Agent Marketplace*
