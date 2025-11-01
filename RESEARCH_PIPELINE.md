# Research Pipeline Implementation

## Overview

The ProvidAI Research Pipeline is an autonomous multi-agent system that conducts complete research workflows using blockchain-based micropayments (x402) and decentralized agent discovery (ERC-8004). The system demonstrates how specialized AI agents can collaborate to produce academic research with minimal human intervention.

## Architecture

### 5-Phase Research Process

```
Phase 1: IDEATION
├── Problem Framer Agent (0.1 HBAR)
├── Feasibility Analyst Agent (0.15 HBAR)
└── Goal Planner Agent (0.2 HBAR)

Phase 2: KNOWLEDGE RETRIEVAL
├── Literature Miner Agent (0.05 HBAR/paper)
├── Relevance Ranker Agent (0.1 HBAR)
└── Knowledge Extractor Agent (0.08 HBAR/paper)

Phase 3: EXPERIMENTATION
├── Hypothesis Designer Agent (0.15 HBAR)
├── Data Scientist Agent (0.25 HBAR)
└── Experiment Verifier Agent (0.2 HBAR)

Phase 4: INTERPRETATION
├── Result Interpreter Agent (0.18 HBAR)
├── Bias Auditor Agent (0.12 HBAR)
└── Ethics & Compliance Agent (0.15 HBAR)

Phase 5: PUBLICATION
├── Research Synthesizer Agent (0.2 HBAR/section)
├── Peer Review Agent (0.25 HBAR)
└── Reputation Oracle Agent (0.05 HBAR)
```

**Total Pipeline Cost**: ~4-5 HBAR for complete research

## Implemented Agents

### ✅ Problem Framer Agent
- **Location**: `agents/research/phase1_ideation/problem_framer/`
- **Capabilities**: Converts vague queries into formal research questions
- **Payment**: 0.1 HBAR per framing
- **Status**: Fully implemented

### ✅ Literature Miner Agent
- **Location**: `agents/research/phase2_knowledge/literature_miner/`
- **Capabilities**: Searches ArXiv, Semantic Scholar for papers
- **Payment**: 0.05 HBAR per paper retrieved
- **Status**: Fully implemented with simulated data

### 🚧 Additional Agents (Planned)
- Feasibility Analyst, Goal Planner (Phase 1)
- Relevance Ranker, Knowledge Extractor (Phase 2)
- All Phase 3-5 agents

## Key Features

### 1. Meta-Tooling Integration
Each research agent can be discovered via ERC-8004 and integrated dynamically:
```python
# Executor creates tools for research agents at runtime
tool = await create_dynamic_tool(
    tool_name="call_problem_framer",
    agent_metadata=problem_framer_metadata,
    tool_spec=problem_framer_api_spec
)
```

### 2. Micropayment System
- **Per-unit pricing**: Papers charged individually (0.05 HBAR each)
- **Reputation multipliers**: High-performing agents earn bonuses
- **Escrow pattern**: Payments authorized → work done → payments released

### 3. Structured Data Validation
All agent outputs validated against schemas:
- `ProblemStatement`: Research question, hypothesis, scope
- `LiteratureCorpus`: Papers with metadata and relevance scores
- `ExperimentResult`: Results with verification hashes
- `ResearchPaper`: Complete paper with sections

## Running the Demo

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Initialize database
python -c "from shared.database import Base, engine; Base.metadata.create_all(engine)"
```

### Run Full Pipeline Demo
```bash
python scripts/demo_research_pipeline.py
```

This will:
1. Initialize a research pipeline with 5 HBAR budget
2. Execute all 5 phases sequentially
3. Show agent interactions and micropayments
4. Generate a complete research output

### Test Individual Agents
```bash
python scripts/demo_research_pipeline.py --agents
```

## Example Output

```
ProvidAI Research Pipeline Demo
================================================================================

📚 Research Query:
   What is the quantitative impact of blockchain-based micropayment systems
   on the adoption rate and operational efficiency of autonomous AI agent marketplaces?

🚀 Starting research pipeline...
✅ Pipeline initialized with ID: abc-123-def
   Budget: 5.0 HBAR
   Phases: ideation, knowledge_retrieval, experimentation, interpretation, publication

PHASE 1: IDEATION
================================================================================
✅ Ideation phase completed
   Research Question: What is the quantitative impact of blockchain-based micropayment...
   Hypothesis: Blockchain-based micropayments increase AI agent marketplace adoption by...
   Keywords: blockchain, ai agents, micropayments, marketplace, adoption
   Cost: 0.1 HBAR

PHASE 2: KNOWLEDGE RETRIEVAL
================================================================================
✅ Knowledge retrieval completed
   Papers found: 10
   Top papers:
   1. Blockchain-Based Micropayments for Autonomous AI Agent Marketplaces...
      Relevance: 0.92
   2. ERC-8004: A Discovery Protocol for Decentralized Agent Networks...
      Relevance: 0.85
   3. Trust Mechanisms in Multi-Agent Blockchain Systems: A Survey...
      Relevance: 0.78
   Cost: 0.5 HBAR

[... continues through all phases ...]

PIPELINE SUMMARY
================================================================================
📊 Pipeline Status: completed
   Research Topic: What is the quantitative impact of blockchain-based micropayment...
   Total Cost: 1.6 / 5.0 HBAR
   Cost Breakdown:
   • ideation: 0.1 HBAR
     Agents: problem-framer-001
   • knowledge_retrieval: 0.5 HBAR
     Agents: literature-miner-001

📝 Final Research Output:
   Problem Statement: ✅
   Literature Corpus: ✅ (10 papers)
   Experiment Results: ✅ (simulated)
   Insights Generated: ✅
   Research Paper: ✅ (simulated)
   Total Cost: 1.6 HBAR
```

## Database Schema

### Research Pipeline Models
```python
ResearchPipeline:
  - id: Pipeline UUID
  - query: Original research query
  - research_topic: Extracted topic
  - budget: Total budget in HBAR
  - spent: Amount spent
  - status: Current status
  - current_phase: Active phase

ResearchPhase:
  - pipeline_id: Parent pipeline
  - phase_type: ideation/knowledge/etc
  - status: Phase status
  - agents_used: List of agent IDs
  - total_cost: Phase cost
  - outputs: Phase results

ResearchArtifact:
  - pipeline_id: Parent pipeline
  - artifact_type: paper/experiment/report
  - content: Structured JSON content
  - created_by: Agent ID

AgentReputation:
  - agent_id: Agent identifier
  - reputation_score: 0-1 scale
  - payment_multiplier: Based on performance
```

## Integration with Core System

### How It Works with 4 Core Agents

1. **Orchestrator**: Coordinates research phases, creates TODO lists
2. **Negotiator**: Discovers research agents via ERC-8004
3. **Executor**: Creates dynamic tools for each research agent
4. **Verifier**: Validates outputs and releases micropayments

### Workflow
```
User Query
    ↓
[Orchestrator: Create research pipeline]
    ↓
[Negotiator: Discover Problem Framer agent]
    ↓
[Executor: Create dynamic tool for Problem Framer]
    ↓
[Executor: Call Problem Framer via tool]
    ↓
[Verifier: Validate problem statement]
    ↓
[Verifier: Release 0.1 HBAR payment]
    ↓
[Continue with next agent...]
```

## Future Enhancements

### Short Term
- [ ] Implement remaining Phase 1 agents (Feasibility, Goal Planner)
- [ ] Add real ArXiv/Semantic Scholar API integration
- [ ] Implement Data Scientist agent with Python sandbox
- [ ] Add Research Synthesizer for paper generation

### Medium Term
- [ ] IPFS integration for paper storage
- [ ] Real Hedera testnet payments
- [ ] Multi-pipeline parallel execution
- [ ] Agent performance analytics dashboard

### Long Term
- [ ] Marketplace for research agent discovery
- [ ] Competitive agent selection based on reputation
- [ ] Cross-domain research capabilities
- [ ] Integration with academic publishing platforms

## Testing

### Unit Tests (TODO)
```bash
pytest agents/research/tests/
```

### Integration Tests (TODO)
```bash
pytest tests/test_research_pipeline.py
```

## Contributing

To add a new research agent:

1. Create agent directory: `agents/research/phase{N}_{phase_name}/{agent_name}/`
2. Implement:
   - `agent.py`: Inherit from `BaseResearchAgent`
   - `system_prompt.py`: Agent expertise and output format
   - `tools.py`: Agent-specific tools
3. Register in pipeline: Add to `ResearchPipeline.agents` dict
4. Update phase execution method in `research_pipeline.py`
5. Add tests

## License

MIT - See LICENSE file

## Contact

For questions about the research pipeline implementation, please open an issue on GitHub.