#!/usr/bin/env python
"""
Fix JSON parsing in all agent files.
"""

import os
import re

# Old pattern to find
OLD_PATTERN = r'''            if isinstance\(agent_output, str\):
                # Extract JSON from response
                json_start = agent_output\.find\('\{'\)
                json_end = agent_output\.rfind\('\}'\) \+ 1
                if json_start != -1 and json_end > json_start:
                    json_str = agent_output\[json_start:json_end\]
                    task_data = json\.loads\(json_str\)
                else:
                    return \{
                        'success': False,
                        'error': 'Failed to parse task output as JSON'
                    \}
            else:
                task_data = agent_output'''

# New pattern
NEW_PATTERN = '''            if isinstance(agent_output, str):
                # Try parsing the entire string as JSON first
                try:
                    task_data = json.loads(agent_output)
                except json.JSONDecodeError:
                    # Extract JSON from response if there's surrounding text
                    json_start = agent_output.find('{')
                    json_end = agent_output.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = agent_output[json_start:json_end]
                        task_data = json.loads(json_str)
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to parse task output as JSON'
                        }
            else:
                task_data = agent_output'''

AGENT_FILES = [
    "agents/research/phase1_ideation/feasibility_analyst/agent.py",
    "agents/research/phase1_ideation/goal_planner/agent.py",
    "agents/research/phase1_ideation/problem_framer/agent.py",
    "agents/research/phase2_knowledge/knowledge_synthesizer/agent.py",
    "agents/research/phase2_knowledge/literature_miner/agent.py",
    "agents/research/phase3_experimentation/code_generator/agent.py",
    "agents/research/phase3_experimentation/experiment_runner/agent.py",
    "agents/research/phase4_interpretation/bias_detector/agent.py",
    "agents/research/phase4_interpretation/compliance_checker/agent.py",
    "agents/research/phase4_interpretation/insight_generator/agent.py",
    "agents/research/phase5_publication/archiver/agent.py",
    "agents/research/phase5_publication/paper_writer/agent.py",
    "agents/research/phase5_publication/peer_reviewer/agent.py",
    "agents/research/phase5_publication/reputation_manager/agent.py",
]

def fix_agent_file(filepath):
    """Fix JSON parsing in an agent file."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Simple string replacement
    old_text = """            if isinstance(agent_output, str):
                # Extract JSON from response
                json_start = agent_output.find('{')
                json_end = agent_output.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = agent_output[json_start:json_end]
                    task_data = json.loads(json_str)
                else:
                    return {
                        'success': False,
                        'error': 'Failed to parse task output as JSON'
                    }
            else:
                task_data = agent_output"""

    if old_text in content:
        content = content.replace(old_text, NEW_PATTERN)

        with open(filepath, 'w') as f:
            f.write(content)

        print(f"✅ Fixed {filepath}")
        return True
    else:
        print(f"⚠️  Skipped {filepath} (already fixed or different structure)")
        return False

def main():
    """Fix all agent files."""
    print("Fixing JSON parsing in all agent files...\n")

    fixed = 0
    skipped = 0

    for filepath in AGENT_FILES:
        if os.path.exists(filepath):
            if fix_agent_file(filepath):
                fixed += 1
            else:
                skipped += 1
        else:
            print(f"❌ File not found: {filepath}")

    print(f"\n✅ Fixed {fixed} agent files")
    print(f"⚠️  Skipped {skipped} files (already fixed)")

if __name__ == "__main__":
    main()
