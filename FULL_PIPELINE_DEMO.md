# Full Pipeline Demo - All 15 Agents

## Overview

The `demo_full_pipeline.py` script demonstrates the complete autonomous research pipeline using **all 15 agents** across 5 phases with agent-to-agent micropayments.

## What It Does

This demo runs a complete research project from start to finish, using every agent in the registry:

### Phase 1: Ideation (3 agents, ~0.28 HBAR)
1. **Problem Framer** - Transforms query into formal research question
2. **Feasibility Analyst** - Evaluates feasibility, resources, constraints
3. **Goal Planner** - Creates structured research plan with milestones

### Phase 2: Knowledge Retrieval (2 agents, ~0.50-1.00 HBAR)
4. **Literature Miner** - Searches ArXiv/Semantic Scholar for papers
5. **Knowledge Synthesizer** - Synthesizes insights, identifies gaps

### Phase 3: Experimentation (3 agents, ~0.47 HBAR)
6. **Hypothesis Designer** - Creates testable hypotheses
7. **Code Generator** - Generates experiment code
8. **Experiment Runner** - Executes experiments and collects data

### Phase 4: Interpretation (3 agents, ~0.34 HBAR)
9. **Insight Generator** - Extracts insights from results
10. **Bias Detector** - Identifies potential biases
11. **Compliance Checker** - Verifies ethical/regulatory compliance

### Phase 5: Publication (4 agents, ~0.55 HBAR)
12. **Paper Writer** - Writes academic research paper
13. **Peer Reviewer** - Reviews paper quality
14. **Reputation Manager** - Updates agent reputations
15. **Archiver** - Archives artifacts to IPFS/blockchain

**Total Pipeline Cost**: ~2-3 HBAR per research project

## Running the Demo

```bash
# Make sure you have a valid OpenAI API key in .env
python scripts/demo_full_pipeline.py
```

## Expected Runtime

- **Phase 1**: ~30-45 seconds (3 OpenAI API calls)
- **Phase 2**: ~45-60 seconds (2 API calls, including literature search)
- **Phase 3**: ~45-60 seconds (3 API calls)
- **Phase 4**: ~30-45 seconds (3 API calls)
- **Phase 5**: ~60-90 seconds (4 API calls)

**Total Runtime**: ~4-6 minutes for complete pipeline

## Output

The demo provides real-time progress updates showing:

```
====================================================================================================
ProvidAI Full Research Pipeline Demo
Demonstrating all 15 autonomous agents with micropayments
====================================================================================================

🔧 Initializing database...
✅ Database ready

📚 Research Query:
   What is the quantitative impact of blockchain-based micropayment systems...

🤖 Loading all 15 research agents...
✅ All agents loaded

🚀 Pipeline initialized: 12345678-1234-1234-1234-123456789012
   Budget: 10.0 HBAR

====================================================================================================
PHASE 1: IDEATION (3 agents)
====================================================================================================

[1/3] Problem Framer - Framing research question...
   ✅ Problem framed
      Research Question: How do blockchain-based micropayment systems...
      Cost: 0.10 HBAR

[2/3] Feasibility Analyst - Analyzing feasibility...
   ✅ Feasibility analyzed
      Score: 0.85
      Assessment: feasible
      Go/No-Go: go
      Cost: 0.08 HBAR

[3/3] Goal Planner - Creating research plan...
   ✅ Research plan created
      Objectives: 5
      Tasks: 24
      Phases: 5
      Cost: 0.10 HBAR

💰 Phase 1 Total Cost: 0.28 HBAR

... (continues through all 5 phases)

====================================================================================================
PIPELINE COMPLETE!
====================================================================================================

📊 Final Statistics:
   Pipeline ID: 12345678-1234-1234-1234-123456789012
   Total Cost: 2.54 HBAR
   Budget: 10.0 HBAR
   Remaining: 7.46 HBAR
   Agents Used: 15/15

🎯 Research Outputs:
   ✅ Problem Statement: Framed
   ✅ Feasibility Analysis: Complete
   ✅ Research Plan: Created
   ✅ Literature Corpus: 8 papers
   ✅ Knowledge Synthesis: Complete
   ✅ Hypothesis: Designed
   ✅ Experiment Code: Generated
   ✅ Experiments: Run
   ✅ Insights: Extracted
   ✅ Bias Analysis: Complete
   ✅ Compliance: Verified
   ✅ Research Paper: Written
   ✅ Peer Review: Score 7.8/10
   ✅ Reputations: Updated
   ✅ Artifacts: Archived

====================================================================================================
🎉 Full autonomous research pipeline completed successfully!
   All 15 agents collaborated with micropayment transactions
====================================================================================================
```

## Key Features Demonstrated

### 1. Agent Discovery & Selection
- Each phase automatically selects appropriate agents
- Agents discovered by capabilities
- Dynamic agent loading

### 2. Micropayment Transactions
- Each agent charges per task (0.05-0.25 HBAR)
- Payments tracked and accumulated
- Budget management across pipeline

### 3. Agent-to-Agent Communication
- Structured JSON data exchange
- Output of one agent feeds into next
- Complete data flow from query to published paper

### 4. Reputation System
- Agent performance tracked
- Quality scores influence payment rates
- Successful agents get reputation boost

### 5. Research Artifact Storage
- All outputs stored in database
- Metadata tracked for each artifact
- Ready for IPFS/blockchain archiving

## Viewing Results

After running the demo, view the stored artifacts:

```bash
# View latest pipeline
python scripts/view_artifacts.py

# Interactive viewer
python scripts/interactive_db_viewer.py

# List all agents used
python scripts/list_all_agents.py
```

## Cost Breakdown

| Phase | Agents | Est. Cost | Description |
|-------|--------|-----------|-------------|
| 1. Ideation | 3 | 0.28 HBAR | Problem framing, feasibility, planning |
| 2. Knowledge | 2 | 0.50-1.00 HBAR | Literature search and synthesis |
| 3. Experimentation | 3 | 0.47 HBAR | Hypothesis, code, experiments |
| 4. Interpretation | 3 | 0.34 HBAR | Insights, bias check, compliance |
| 5. Publication | 4 | 0.55 HBAR | Paper, review, reputation, archive |
| **Total** | **15** | **2-3 HBAR** | Complete research pipeline |

## Architecture Flow

```
User Query
    ↓
[Phase 1: Ideation]
    ↓ Problem Statement, Feasibility, Plan
[Phase 2: Knowledge]
    ↓ Literature Corpus, Synthesis
[Phase 3: Experimentation]
    ↓ Hypothesis, Code, Results
[Phase 4: Interpretation]
    ↓ Insights, Bias Report, Compliance
[Phase 5: Publication]
    ↓ Paper, Review, Archive
Research Output
```

## Agent Interactions

Each agent:
1. Receives structured input from previous agents
2. Executes its specialized task using OpenAI GPT-4
3. Returns JSON-formatted results
4. Charges micropayment for service
5. Updates reputation based on performance

## Files Generated

- **Database Records**: Pipeline, phases, artifacts in SQLite
- **Research Artifacts**: Problem statement, literature corpus, hypothesis, etc.
- **Agent Metadata**: Reputation scores, payment history
- **Pipeline Status**: Real-time tracking of progress

## Troubleshooting

### "OPENAI_API_KEY not set"
Make sure your `.env` file has a valid OpenAI API key:
```bash
OPENAI_API_KEY=sk-proj-...
```

### "Rate limit exceeded"
OpenAI free tier has rate limits. Wait a minute and retry, or upgrade your API plan.

### Agents taking too long
Each agent makes an OpenAI API call which can take 5-15 seconds. Total runtime is 4-6 minutes.

## Next Steps

To enhance the demo:

1. **Add real Hedera payments** - Replace simulated payments with actual HBAR transactions
2. **Deploy to blockchain** - Register agents on Hedera testnet via ERC-8004
3. **IPFS integration** - Actually upload artifacts to IPFS in Archiver agent
4. **Parallel execution** - Run independent agents in parallel to speed up pipeline
5. **Web UI** - Create dashboard to visualize pipeline progress

## Comparison with Original Demo

| Feature | Original Demo | Full Pipeline Demo |
|---------|--------------|-------------------|
| Agents Used | 2 (Problem Framer, Literature Miner) | 15 (All agents) |
| Phases | 2 real, 3 simulated | 5 real phases |
| Cost | ~0.72 HBAR | ~2-3 HBAR |
| Runtime | ~1 minute | ~4-6 minutes |
| Outputs | Problem + Papers | Complete research paper |
| Features | Basic pipeline | Full autonomous research |

---

*This demo showcases the complete ProvidAI autonomous research system with all 15 specialized agents working together via micropayment transactions.*
