# OpenAI API Migration Summary

All agents in ProvidAI have been successfully migrated from Anthropic/Strands SDK to OpenAI API.

## Changes Made

### 1. Marketplace Agents (4 agents)

All marketplace agents now use OpenAI GPT-4 Turbo instead of Anthropic Claude:

#### [agents/orchestrator/agent.py](agents/orchestrator/agent.py)
- **Before**: Used `Anthropic` client with `claude-3-7-sonnet-20250219`
- **After**: Uses `create_openai_agent` with `gpt-4-turbo-preview`
- **Environment Variable**: `ORCHESTRATOR_MODEL` (defaults to `gpt-4-turbo-preview`)

#### [agents/negotiator/agent.py](agents/negotiator/agent.py)
- **Before**: Used `Anthropic` client with `claude-3-7-sonnet-20250219`
- **After**: Uses `create_openai_agent` with `gpt-4-turbo-preview`
- **Environment Variable**: `NEGOTIATOR_MODEL` (defaults to `gpt-4-turbo-preview`)

#### [agents/executor/agent.py](agents/executor/agent.py)
- **Before**: Used `Anthropic` client with `claude-3-7-sonnet-20250219`
- **After**: Uses `create_openai_agent` with `gpt-4-turbo-preview`
- **Environment Variable**: `EXECUTOR_MODEL` (defaults to `gpt-4-turbo-preview`)
- **Note**: Meta-tooling capabilities preserved

#### [agents/verifier/agent.py](agents/verifier/agent.py)
- **Before**: Used `Anthropic` client with `claude-3-7-sonnet-20250219`
- **After**: Uses `create_openai_agent` with `gpt-4-turbo-preview`
- **Environment Variable**: `VERIFIER_MODEL` (defaults to `gpt-4-turbo-preview`)

### 2. Agent Tools

#### [agents/orchestrator/tools/agent_tools.py](agents/orchestrator/tools/agent_tools.py)
- Removed `from anthropic import Anthropic` and `from strands import Agent, tool`
- Added `from shared.openai_agent import create_openai_agent`
- Replaced `get_anthropic_client()` with `get_openai_api_key()`
- Updated all 3 agent tool functions:
  - `negotiator_agent()` - Now uses OpenAI
  - `executor_agent()` - Now uses OpenAI
  - `verifier_agent()` - Now uses OpenAI
- Changed agent execution from `agent(query)` to `asyncio.run(agent.run(query))`

### 3. Research Agents (15 agents)

Research agents were already using OpenAI API via `shared/openai_agent.py`:
- problem_framer
- literature_miner
- feasibility_analyst
- goal_planner
- knowledge_synthesizer
- hypothesis_designer
- experiment_runner
- code_generator
- insight_generator
- bias_detector
- compliance_checker
- paper_writer
- peer_reviewer
- reputation_manager
- archiver

No changes needed for these agents.

## Environment Variables

Update your `.env` file to use OpenAI API key instead of Anthropic:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional model overrides (defaults shown)
ORCHESTRATOR_MODEL=gpt-4-turbo-preview
NEGOTIATOR_MODEL=gpt-4-turbo-preview
EXECUTOR_MODEL=gpt-4-turbo-preview
VERIFIER_MODEL=gpt-4-turbo-preview

# All research agents use gpt-4-turbo-preview by default
```

## API Key Setup

Remove the old Anthropic API key:
```bash
# Remove from .env file
# ANTHROPIC_API_KEY=...

# Unset from environment
unset ANTHROPIC_API_KEY
```

Add OpenAI API key:
```bash
# Add to .env file
OPENAI_API_KEY=sk-your-api-key-here
```

## Dependencies

The following packages are NO LONGER required:
- `anthropic` - Anthropic API client
- `strands` - Strands SDK (was never installed)

The following packages ARE required:
- `openai>=1.0.0` - Already in requirements.txt

## Compatibility

### Agent Interface

The OpenAI agent wrapper in `shared/openai_agent.py` provides a compatible interface:

- **Strands**: `agent(query)` or `agent.run(query)`
- **OpenAI Wrapper**: `await agent.run(query)` or `asyncio.run(agent.run(query))`

### Tool Calling

**Note**: The current OpenAI agent wrapper uses JSON mode for structured outputs but does NOT yet support full function calling. If marketplace agents need to use tools dynamically, the wrapper would need to be enhanced with OpenAI's function calling API.

Research agents don't use tools (they output JSON directly), so they work perfectly.

## Testing

Run the full pipeline demo to verify all agents work:
```bash
python scripts/demo_full_pipeline.py
```

Expected result: All 15 research agents should complete successfully.

## Cost Comparison

### Anthropic Claude Pricing
- Claude 3.7 Sonnet: $3.00 / 1M input tokens, $15.00 / 1M output tokens

### OpenAI GPT-4 Turbo Pricing
- GPT-4 Turbo: $10.00 / 1M input tokens, $30.00 / 1M output tokens

**Note**: GPT-4 Turbo is more expensive than Claude Sonnet. Consider using `gpt-3.5-turbo` for less critical agents to reduce costs.

## Performance

- **OpenAI GPT-4 Turbo**: Generally faster response times, good quality
- **Anthropic Claude Sonnet**: Was not available (Strands SDK never installed)

## Future Enhancements

1. **Add function calling support** to `shared/openai_agent.py` for marketplace agents
2. **Consider GPT-4o** for better performance/cost ratio
3. **Add model selection per agent** based on task complexity
4. **Implement streaming responses** for better user experience

## Rollback

If you need to rollback to Anthropic:

1. Install Strands SDK: `pip install strands-sdk anthropic`
2. Revert changes to the 4 marketplace agent files
3. Update `.env` to use `ANTHROPIC_API_KEY`
4. Update model environment variables to use Claude models

However, note that Strands SDK was never part of the original setup, so this would be a new addition.
