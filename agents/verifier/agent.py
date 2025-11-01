"""Verifier Agent implementation using OpenAI API."""

import os
from shared.openai_agent import Agent, create_openai_agent

from .system_prompt import VERIFIER_SYSTEM_PROMPT
from .tools import (
    verify_task_result,
    validate_output_schema,
    check_quality_metrics,
    release_payment,
    reject_and_refund,
    submit_verification_message,
    run_verification_code,
    run_unit_tests,
    validate_code_output,
    search_web,
    verify_fact,
    check_data_source_credibility,
    research_best_practices,
)


def create_verifier_agent() -> Agent:
    """
    Create and configure the Verifier agent with advanced verification capabilities.

    The Verifier now includes:
    - Code execution for automated testing
    - Web search for fact-checking
    - Data source credibility assessment

    Returns:
        Configured OpenAI Agent instance
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("VERIFIER_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    tools = [
        # Core verification
        verify_task_result,
        validate_output_schema,
        check_quality_metrics,
        # Payment management
        release_payment,
        reject_and_refund,
        # Code execution
        run_verification_code,
        run_unit_tests,
        validate_code_output,
        # Web search & fact-checking
        search_web,
        verify_fact,
        check_data_source_credibility,
        research_best_practices,
        # Coordination
        submit_verification_message,
    ]

    agent = create_openai_agent(
        api_key=api_key,
        model=model,
        system_prompt=VERIFIER_SYSTEM_PROMPT,
        tools=tools,
    )

    return agent


# Example usage
async def run_verifier_example():
    """Example of using the verifier agent with advanced verification."""
    agent = create_verifier_agent()

    request = """
    Verify task task-123 with comprehensive checks:

    1. Basic verification:
       - Required fields: ["summary", "insights", "data"]
       - Quality threshold: 80
       - Max errors: 2

    2. Code-based verification:
       - Write Python code to verify data completeness is >= 95%
       - Run statistical analysis on the insights

    3. Fact-checking:
       - The task claims "Average SaaS churn rate is 5% monthly"
       - Use web search to verify this claim

    4. Data source credibility:
       - Check if data sources mentioned are credible

    If all verification passes, release payment payment-456.
    """

    result = await agent.run(request)
    print(result)


async def run_code_verification_example():
    """Example of code-based verification."""
    agent = create_verifier_agent()

    request = """
    Task task-123 returned analysis results. Verify quality by running this code:

    ```python
    import json
    import sys

    # Load task results
    task_result = json.loads(sys.argv[1])

    # Check data completeness
    data = task_result.get('data', [])
    completeness = len([x for x in data if x is not None]) / len(data) * 100

    # Check insights quality
    insights = task_result.get('insights', [])
    has_insights = len(insights) >= 3

    # Validation
    if completeness >= 95 and has_insights:
        print(f"PASS: Completeness {completeness}%, {len(insights)} insights")
        sys.exit(0)
    else:
        print(f"FAIL: Completeness {completeness}%, {len(insights)} insights")
        sys.exit(1)
    ```

    If code verification passes, release payment.
    """

    result = await agent.run(request)
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_verifier_example())
