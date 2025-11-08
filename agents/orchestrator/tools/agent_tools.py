"""Agent tools - Negotiator, Executor, and Verifier as callable tools."""

import logging
import os
from typing import Any, Dict, Optional

from strands import tool

from shared.a2a import A2AAgentClient
from shared.openai_agent import create_openai_agent
from shared.task_progress import update_progress

from agents.executor.system_prompt import EXECUTOR_SYSTEM_PROMPT
from agents.executor.tools import (
    create_dynamic_tool,
    execute_shell_command,
    get_tool_template,
    list_dynamic_tools,
    load_and_execute_tool,
    execute_local_agent,
    list_local_agents,
)

# Import system prompts
from agents.negotiator.system_prompt import NEGOTIATOR_SYSTEM_PROMPT

# Import tools for each agent
from agents.negotiator.tools import (
    create_payment_request,
    find_agents,
    resolve_agent_by_domain,
    compare_agent_scores,
    get_payment_status,
)
from agents.verifier.system_prompt import VERIFIER_SYSTEM_PROMPT
from agents.verifier.tools import (
    check_data_source_credibility,
    check_quality_metrics,
    reject_and_refund,
    release_payment,
    research_best_practices,
    run_unit_tests,
    run_verification_code,
    search_web,
    validate_code_output,
    validate_output_schema,
    verify_fact,
    verify_task_result,
)
from agents.negotiator.tools.payment_tools import authorize_payment as _authorize_payment

logger = logging.getLogger(__name__)

_A2A_CLIENTS: Dict[str, A2AAgentClient] = {}


def _get_a2a_client(env_var: str) -> Optional[A2AAgentClient]:
    """Return (and cache) an A2A client for the configured endpoint."""

    url = os.getenv(env_var, "").strip()
    if not url:
        return None

    normalized_url = url.rstrip("/")
    client = _A2A_CLIENTS.get(env_var)

    if client and client.base_url == normalized_url:
        return client

    client = A2AAgentClient(url)
    _A2A_CLIENTS[env_var] = client
    return client


def get_openai_api_key() -> str:
    """Get configured OpenAI API key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return api_key


@tool
async def negotiator_agent(
    task_id: str,
    capability_requirements: str,
    budget_limit: Optional[float] = None,
    min_reputation_score: Optional[float] = 0.2,
    task_name: Optional[str] = None,
    todo_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Discover and negotiate with marketplace agents using ERC-8004 protocol.

    This agent:
    - Discovers agents by capability from ERC-8004 registry
    - Evaluates pricing and reputation
    - Negotiates terms and creates payment channels (x402)

    Args:
        task_id: Unique identifier for the task
        capability_requirements: Description of required agent capabilities
        budget_limit: Maximum budget for the task (optional)
        min_reputation_score: Minimum reputation score (0-1, default 0.7)
        task_name: Optional name of the task being negotiated for
        todo_id: Optional TODO item ID (e.g., "todo_0") to create unique progress step

    Returns:
        Dict containing:
        - selected_agent: Chosen agent details
        - payment_id: Payment request ID (escrow not yet funded)
        - negotiation_summary: Summary of negotiation
    """
    try:
        # Construct message with task name if provided
        if task_name:
            message = f"Finding agent for: {task_name}"
        else:
            message = "Finding and negotiating with marketplace agents"

        # Use microtask-specific step name if todo_id provided, otherwise use generic "negotiator"
        step_name = f"negotiator_{todo_id}" if todo_id else "negotiator"

        # Update progress: negotiator started
        update_progress(task_id, step_name, "running", {
            "message": message,
            "capability_requirements": capability_requirements,
            "budget_limit": budget_limit,
            "task_name": task_name,
            "todo_id": todo_id
        })

        query = f"""
        Task ID: {task_id}
        TODO ID: {todo_id if todo_id else "N/A"}

        I need to find and negotiate with a marketplace agent with the following capabilities:
        {capability_requirements}

        Requirements:
        - Budget limit: {budget_limit if budget_limit else "No specific limit"}
        - Minimum reputation score: {min_reputation_score}

        Please:
        1. Discover suitable agents from the ERC-8004 registry
        2. Evaluate their pricing and reputation
        3. Select the best agent based on cost-effectiveness and reliability
        4. Draft an x402 payment proposal (do NOT authorize or fund escrow)

        Return the selected agent details, payment proposal terms, and payment ID for orchestrator approval.
        """

        metadata = {
            "task_id": task_id,
            "budget_limit": budget_limit,
            "min_reputation_score": min_reputation_score,
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        client = _get_a2a_client("NEGOTIATOR_A2A_URL")
        if client:
            try:
                response_text = await client.invoke_text(
                    query,
                    metadata=metadata or None,
                )
                return {
                    "success": True,
                    "task_id": task_id,
                    "response": str(response_text),
                    "transport": "a2a",
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Negotiator A2A endpoint %s failed (%s); falling back to local execution",
                    client.base_url,
                    exc,
                )

        api_key = get_openai_api_key()
        model = os.getenv("NEGOTIATOR_MODEL", "gpt-4-turbo-preview")
        agent = create_openai_agent(
            api_key=api_key,
            model=model,
            system_prompt=NEGOTIATOR_SYSTEM_PROMPT,
            tools=[
                find_agents,
                resolve_agent_by_domain,
                compare_agent_scores,
                create_payment_request,
                get_payment_status,
            ],
        )

        response = await agent.run(query)

        # Log the full negotiator response
        logger.info("[negotiator_agent] ===== NEGOTIATOR RESPONSE START =====")
        logger.info(f"[negotiator_agent] {response}")
        logger.info("[negotiator_agent] ===== NEGOTIATOR RESPONSE END =====")

        # Parse response to extract agent selection details for progress update
        response_str = str(response)

        # Construct completion message with task name if provided
        if task_name:
            completion_message = f"✓ Agent selected for: {task_name}"
        else:
            completion_message = "✓ Agent discovered and selected"

        # Use same step name as the start message
        step_name = f"negotiator_{todo_id}" if todo_id else "negotiator"

        # Update progress: negotiator completed with agent selection info
        # Note: ranked_agents and best_agent are already included via compare_agent_scores
        update_progress(task_id, step_name, "completed", {
            "message": completion_message,
            "response": response_str[:500],  # Truncate for progress log
            "task_name": task_name,
            "todo_id": todo_id
        })

        return {
            "success": True,
            "task_id": task_id,
            "response": response_str,
            "transport": "local",
        }

    except Exception as e:
        # Use same step name for error reporting
        step_name = f"negotiator_{todo_id}" if todo_id else "negotiator"

        # Update progress: negotiator failed
        update_progress(task_id, step_name, "failed", {
            "message": "Agent negotiation failed",
            "error": str(e),
            "todo_id": todo_id
        })

        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
        }

@tool
async def authorize_payment_request(payment_id: str) -> Dict[str, Any]:
    """Authorize an x402 payment proposal by funding TaskEscrow.

    This helper is reserved for the Orchestrator agent after it reviews and
    approves a payment proposal drafted by the Negotiator. It funds the
    TaskEscrow contract and emits the corresponding A2A authorization message.

    Args:
        payment_id: Identifier of the pending payment proposal.

    Returns:
        Result dictionary including authorization details or error context.
    """

    try:
        response = await _authorize_payment(payment_id)
        return {"success": True, **response}
    except Exception as exc:
        return {"success": False, "payment_id": payment_id, "error": str(exc)}


@tool
async def executor_agent(
    task_id: str,
    agent_metadata: Dict[str, Any],
    task_description: str,
    execution_parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute tasks using LOCAL research agents only.

    Updated Behavior:
    - Ignore marketplace agent metadata
    - ALWAYS list local agents first
    - Select the most relevant local agent
    - Execute using execute_local_agent
    """

    try:
        # Update progress: executor started
        update_progress(task_id, "executor", "running", {
            "message": "Executing task using local agent flow",
            "agent_metadata_ignored": agent_metadata  # logged for traceability
        })

        params_str = f"\nExecution Parameters: {execution_parameters}" if execution_parameters else ""

        # Updated LOCAL-ONLY prompt
        query = f"""
        Task ID: {task_id}

        Task Description:
        {task_description}
        {params_str}

        IMPORTANT: Ignore all metadata. Do NOT analyze it or reference it.

        You MUST follow this workflow EXACTLY:

        1. CALL list_local_agents to view all available local agents
        2. Select the BEST agent for this task
        3. CALL execute_local_agent with:
            - agent_domain (the selected agent)
            - task_description
            - context: include task_id and execution_parameters if provided

        RULES:
        - You MUST call the tools, not describe them
        - You MUST show results of tool calls
        - Do NOT create or reference dynamic tools
        - Do NOT reference agent_metadata at all

        Return:
        - execution_result from the executed local agent
        - selected_agent used
        - execution_log of the steps taken
        """

        # A2A transport attempt first
        client = _get_a2a_client("EXECUTOR_A2A_URL")
        if client:
            try:
                response_text = await client.invoke_text(
                    query, metadata={"task_id": task_id} if task_id else None
                )
                return {
                    "success": True,
                    "task_id": task_id,
                    "response": str(response_text),
                    "transport": "a2a",
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Executor A2A endpoint %s failed (%s); falling back to local execution",
                    client.base_url,
                    exc,
                )

        # Local execution
        api_key = get_openai_api_key()
        model = os.getenv("EXECUTOR_MODEL", "gpt-4-turbo-preview")

        agent = create_openai_agent(
            api_key=api_key,
            model=model,
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            tools=[
                execute_local_agent,
                list_local_agents,
            ],
        )

        response = await agent.run(query)

        # Log executor response
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE START =====")
        logger.info(f"[executor_agent] {response}")
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE END =====")

        # Update progress: executor completed
        update_progress(task_id, "executor", "completed", {
            "message": "Task execution completed",
            "response": str(response)[:500]  # Truncate for progress log
        })

        return {
            "success": True,
            "task_id": task_id,
            "response": str(response),
            "transport": "local",
        }

    except Exception as e:
        update_progress(task_id, "executor", "failed", {
            "message": "Task execution failed",
            "error": str(e)
        })

        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
        }

@tool
async def verifier_agent(
    task_id: str,
    payment_id: str,
    task_result: Dict[str, Any],
    verification_criteria: Dict[str, Any],
    verification_mode: str = "standard",
) -> Dict[str, Any]:
    """
    Verify task quality, validate outputs, and release payments.

    This agent:
    - Validates task completion quality
    - Executes code-based verification tests
    - Fact-checks claims via web search
    - Assesses data source credibility
    - Releases or rejects payments based on verification

    Args:
        task_id: Unique identifier for the task
        payment_id: Payment authorization ID from negotiator
        task_result: Result data from executor to verify
        verification_criteria: Expected criteria (schema, metrics, tests)
        verification_mode: Verification depth - "standard", "thorough", or "strict"

    Returns:
        Dict containing:
        - verification_passed: Boolean indicating if verification passed
        - verification_report: Detailed verification findings
        - quality_score: Overall quality score (0-1)
        - payment_status: Payment released/rejected
    """
    try:
        # Update progress: verifier started
        update_progress(task_id, "verifier", "running", {
            "message": "Verifying task results and quality",
            "verification_mode": verification_mode,
            "payment_id": payment_id
        })

        query = f"""
        Task ID: {task_id}
        Payment ID: {payment_id}
        Verification Mode: {verification_mode}

        Task Result to Verify:
        {task_result}

        Verification Criteria:
        {verification_criteria}

        Please perform {verification_mode} verification:
        1. Validate the output against the expected schema
        2. Check quality metrics (completeness, accuracy, relevance)
        3. Run verification code/tests if applicable
        4. Fact-check any claims using web search
        5. Assess data source credibility
        6. Generate a verification report with quality score
        7. Release payment if verification passes, reject if it fails

        Return verification status, detailed report, quality score, and payment status.
        """

        client = _get_a2a_client("VERIFIER_A2A_URL")
        if client:
            try:
                response_text = await client.invoke_text(
                    query,
                    metadata={
                        "task_id": task_id,
                        "payment_id": payment_id,
                        "mode": verification_mode,
                    },
                )
                return {
                    "success": True,
                    "task_id": task_id,
                    "payment_id": payment_id,
                    "response": str(response_text),
                    "transport": "a2a",
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Verifier A2A endpoint %s failed (%s); falling back to local execution",
                    client.base_url,
                    exc,
                )

        api_key = get_openai_api_key()
        model = os.getenv("VERIFIER_MODEL", "gpt-4-turbo-preview")
        agent = create_openai_agent(
            api_key=api_key,
            model=model,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            tools=[
                verify_task_result,
                validate_output_schema,
                check_quality_metrics,
                run_verification_code,
                run_unit_tests,
                validate_code_output,
                search_web,
                verify_fact,
                check_data_source_credibility,
                research_best_practices,
                release_payment,
                reject_and_refund,
            ],
        )

        response = await agent.run(query)

        # Log the full verifier response
        logger.info("[verifier_agent] ===== VERIFIER RESPONSE START =====")
        logger.info(f"[verifier_agent] {response}")
        logger.info("[verifier_agent] ===== VERIFIER RESPONSE END =====")

        return {
            "success": True,
            "task_id": task_id,
            "payment_id": payment_id,
            "response": str(response),
            "transport": "local",
        }

    except Exception as e:
        logger.error(f"[verifier_agent] Verification failed: {e}", exc_info=True)
        return {
            "success": False,
            "task_id": task_id,
            "payment_id": payment_id,
            "error": str(e),
        }
