"""Agent tools - Negotiator, Executor, and Verifier as callable tools."""

import logging
import os
from typing import Any, Dict, Optional

from strands import tool

from agents.executor.system_prompt import EXECUTOR_SYSTEM_PROMPT
from agents.executor.tools.research_api_executor import (
    execute_research_agent,
    get_agent_metadata,
    list_research_agents,
)

# Import system prompts
from agents.negotiator.system_prompt import NEGOTIATOR_SYSTEM_PROMPT

# Import tools for each agent
from agents.negotiator.tools import (
    compare_agent_scores,
    create_payment_request,
    find_agents,
    get_payment_status,
    resolve_agent_by_domain,
)
from agents.negotiator.tools.payment_tools import (
    authorize_payment as _authorize_payment,
)
from agents.verifier.system_prompt import VERIFIER_SYSTEM_PROMPT
from agents.verifier.research_system_prompt import RESEARCH_VERIFIER_SYSTEM_PROMPT
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
from agents.verifier.tools.research_verification_tools import (
    calculate_quality_score,
    check_citation_quality,
    generate_feedback_report,
    validate_statistical_significance,
    verify_research_output,
)
from shared.a2a import A2AAgentClient
from shared.openai_agent import create_openai_agent
from shared.task_progress import update_progress

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
    agent_domain: str,
    task_description: str,
    execution_parameters: Optional[Dict[str, Any]] = None,
    todo_id: Optional[str] = None,
    todo_list: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Execute tasks using research agents from the FastAPI server (port 5001).

    This agent:
    - Calls research agents via HTTP API (no simulation)
    - Returns real agent output
    - Note: TODO completion is now handled by verification flow in execute_microtask

    Args:
        task_id: Unique identifier for the task
        agent_domain: Domain of agent from negotiator
        task_description: Description of what to execute
        execution_parameters: Optional parameters for execution
        todo_id: Optional TODO item ID (e.g., "todo_0") for microtask tracking
        todo_list: Optional TODO list for updating item status

    Returns:
        Dict containing:
        - success: bool
        - result: Actual agent output
        - agent_used: Which agent was selected
    """

    try:
        # Use microtask-specific step name if todo_id provided
        step_name = f"executor_{todo_id}" if todo_id else "executor"

        # Update progress: executor started
        update_progress(task_id, step_name, "running", {
            "message": f"Executing task{f': {task_description[:50]}...' if task_description else ''}",
            "todo_id": todo_id
        })

        params_str = f"\nExecution Parameters: {execution_parameters}" if execution_parameters else ""
        todo_str = f"\nTODO ID: {todo_id}" if todo_id else ""

        # Updated RESEARCH API prompt
        query = f"""
        Task ID: {task_id}{todo_str}

        Agent Domain: {agent_domain}

        Task Description:
        {task_description}
        {params_str}

        You MUST follow this workflow EXACTLY:

        1. CALL execute_research_agent with:
            - agent_domain (the selected agent's domain)
            - task_description (the task to perform)
            - context (include any execution_parameters)
            - metadata (include task_id and todo_id for tracking)

        CRITICAL RULES:
        - You MUST actually CALL the tools - do NOT simulate or describe
        - Return the ACTUAL result from execute_research_agent
        - Do NOT summarize or paraphrase the agent's output

        Return:
        - The full agent result (NOT a summary)
        - Success status
        """

        # A2A transport attempt first
        client = _get_a2a_client("EXECUTOR_A2A_URL")
        if client:
            try:
                response_text = await client.invoke_text(
                    query, metadata={"task_id": task_id, "todo_id": todo_id} if task_id else None
                )

                # Note: TODO completion is now handled by verification flow in execute_microtask

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

        # Local execution using research agents API
        api_key = get_openai_api_key()
        model = os.getenv("EXECUTOR_MODEL", "gpt-4-turbo-preview")

        agent = create_openai_agent(
            api_key=api_key,
            model=model,
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            tools=[
                list_research_agents,
                execute_research_agent,
                get_agent_metadata,
            ],
        )

        td_lower = (task_description or "").lower()
        is_web_search = False
        # Heuristic on agent domain
        if isinstance(agent_domain, str) and any(k in agent_domain for k in ("literature", "miner", "paper", "knowledge", "search")):
            is_web_search = True
        # Heuristic on task description
        if any(
            kw in td_lower
            for kw in (
                "literature",
                "paper",
                "arxiv",
                "semantic scholar",
                "web search",
                "tavily",
                "knowledge synthesis",
                "research papers",
                "citations",
            )
        ):
            is_web_search = True
        if is_web_search:
            update_progress(task_id, "web_search", "running", {
                "message": "Searching the web for relevant papers and sources (Tavily + academic indexes)",
                "todo_id": todo_id
            })

        response = await agent.run(query)

        # Log executor response
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE START =====")
        logger.info(f"[executor_agent] {response}")
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE END =====")

        # Update progress: executor completed
        update_progress(task_id, step_name, "completed", {
            "message": "✓ Task execution completed",
            "response": str(response)[:500],  # Truncate for progress log
            "todo_id": todo_id
        })

        # Close web_search phase if opened
        if is_web_search:
            update_progress(task_id, "web_search", "completed", {
                "message": "✓ Web search results retrieved",
                "response_preview": str(response)[:300]
            })

        # Note: TODO completion is now handled by verification flow in execute_microtask

        return {
            "success": True,
            "task_id": task_id,
            "response": str(response),
            "transport": "local",
        }

    except Exception as e:
        logger.error(f"[executor_agent] Execution failed: {e}", exc_info=True)

        step_name = f"executor_{todo_id}" if todo_id else "executor"
        update_progress(task_id, step_name, "failed", {
            "message": "Task execution failed",
            "error": str(e),
            "todo_id": todo_id
        })

        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
        }


# Helper functions for human-in-the-loop verification
async def _extract_verification_score(verifier_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract verification scores from verifier agent result with enhanced logging and robustness."""
    import re
    import json

    response_text = verifier_result.get("response", "")

    logger.info(f"[_extract_verification_score] Starting extraction from response length: {len(response_text)}")
    logger.info(f"[_extract_verification_score] Full response text:\n{response_text}")

    # Strategy 1: Try to find JSON with scores - improved pattern that handles nested objects
    # Look for "overall_score" and find the enclosing JSON object
    start = response_text.find('"overall_score"')
    if start != -1:
        logger.info(f"[_extract_verification_score] Found 'overall_score' at position {start}")
        # Search backwards for opening brace
        brace_start = response_text.rfind('{', 0, start)
        if brace_start != -1:
            logger.info(f"[_extract_verification_score] Found opening brace at position {brace_start}")
            # Search forwards for matching closing brace
            brace_count = 0
            for i in range(brace_start, len(response_text)):
                if response_text[i] == '{':
                    brace_count += 1
                elif response_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = response_text[brace_start:i+1]
                            logger.info(f"[_extract_verification_score] Attempting to parse JSON: {json_str[:500]}...")
                            scores_data = json.loads(json_str)
                            # Validate it has the fields we expect
                            if "overall_score" in scores_data:
                                logger.info(f"[_extract_verification_score] ✓ Successfully extracted JSON scores: {scores_data}")
                                return scores_data
                        except json.JSONDecodeError as e:
                            logger.warning(f"[_extract_verification_score] JSON decode failed: {e}")
                            break

    logger.warning("[_extract_verification_score] JSON extraction failed, trying regex patterns...")

    # Strategy 2: Try to extract scores from text using regex (fallback if JSON parsing failed)
    overall_score_match = re.search(r'[Oo]verall[_ ][Ss]core["\s:]+(\d+)', response_text)
    overall_score = float(overall_score_match.group(1)) if overall_score_match else 0

    if overall_score_match:
        logger.info(f"[_extract_verification_score] Regex found overall_score: {overall_score}")
    else:
        logger.warning("[_extract_verification_score] Regex could not find overall_score")

    # Extract dimension scores
    dimension_scores = {}
    dimensions = ["completeness", "correctness", "academic_rigor", "clarity", "innovation", "ethics"]
    for dim in dimensions:
        pattern = rf'{dim}["\s:]+(\d+)'
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            dimension_scores[dim] = float(match.group(1))
            logger.info(f"[_extract_verification_score] Regex found {dim}: {dimension_scores[dim]}")
        else:
            logger.warning(f"[_extract_verification_score] Regex could not find {dim}")

    # Extract feedback
    feedback_match = re.search(r'[Ff]eedback["\s:]+(.+?)(?:\n\n|\Z)', response_text, re.DOTALL)
    feedback = feedback_match.group(1).strip() if feedback_match else "No feedback available"

    logger.info(f"[_extract_verification_score] Final extracted scores: overall={overall_score}, dimensions={dimension_scores}")

    return {
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "feedback": feedback
    }


def _check_task_cancelled(task_id: str) -> bool:
    """Check if task has been cancelled by user."""
    from api.main import tasks_storage

    if task_id in tasks_storage:
        return tasks_storage[task_id].get("cancelled", False)
    return False


async def _request_human_verification(
    task_id: str,
    todo_id: str,
    payment_id: Optional[str],
    quality_score: float,
    dimension_scores: Dict[str, float],
    feedback: str,
    task_result: Any,
    agent_name: str,
) -> None:
    """Store verification data and request human review."""
    # Import here to avoid circular dependency
    from api.main import tasks_storage

    if task_id not in tasks_storage:
        tasks_storage[task_id] = {}

    tasks_storage[task_id]["verification_pending"] = True
    tasks_storage[task_id]["verification_data"] = {
        "todo_id": todo_id,
        "payment_id": payment_id,
        "quality_score": quality_score,
        "dimension_scores": dimension_scores,
        "feedback": feedback,
        "task_result": task_result,
        "agent_name": agent_name,
        "ethics_passed": dimension_scores.get("ethics", 100) >= 90,
    }
    tasks_storage[task_id]["verification_decision"] = None

    # Update progress to show waiting for human
    update_progress(task_id, f"verification_{todo_id}", "waiting_for_human", {
        "message": f"⏸ Verification requires human review (score: {quality_score}/100)",
        "quality_score": quality_score,
        "dimension_scores": dimension_scores,
        "payment_id": payment_id,
        "todo_id": todo_id
    })


async def _wait_for_human_decision(task_id: str, todo_id: str, timeout: int = 3600) -> Dict[str, Any]:
    """Wait for human decision on verification (polls every 2 seconds, timeout after 1 hour)."""
    import asyncio
    from api.main import tasks_storage

    max_attempts = timeout // 2  # 2 second intervals
    attempts = 0

    while attempts < max_attempts:
        if task_id in tasks_storage and tasks_storage[task_id].get("verification_decision"):
            decision = tasks_storage[task_id]["verification_decision"]
            return decision

        await asyncio.sleep(2)
        attempts += 1

    # Timeout - auto-reject
    logger.warning(f"[_wait_for_human_decision] Timeout waiting for human decision on {task_id}/{todo_id}")
    update_progress(task_id, f"verification_{todo_id}", "failed", {
        "message": "❌ Verification timeout - auto-rejected after 1 hour",
        "auto_rejected": True,
        "reason": "timeout"
    })

    return {
        "approved": False,
        "reason": "Verification timeout - no human response after 1 hour"
    }


@tool
async def execute_microtask(
    task_id: str,
    todo_id: str,
    task_name: str,
    task_description: str,
    capability_requirements: str,
    budget_limit: Optional[float] = None,
    min_reputation_score: Optional[float] = 0.2,
    execution_parameters: Optional[Dict[str, Any]] = None,
    todo_list: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Execute a complete microtask: negotiation → authorization → execution → verification.

    This is a high-level tool that handles the entire workflow for a single microtask:
    1. Mark TODO as in_progress
    2. Discover and negotiate with agent via negotiator_agent
    3. Authorize payment (funds held in escrow)
    4. Execute task via executor_agent
    5. Verify results via verifier_agent
    6. Auto-approve if score >= 50 AND ethics >= 90, otherwise request human review
    7. Release payment on approval or refund on rejection
    8. Mark TODO as completed/failed based on verification outcome

    Use this instead of calling negotiator/authorize/executor/verifier separately.

    Args:
        task_id: Task ID
        todo_id: TODO item ID (e.g., "todo_0")
        task_name: Name of the microtask
        task_description: Detailed description of what to do
        capability_requirements: Required agent capabilities
        budget_limit: Maximum budget (optional)
        min_reputation_score: Minimum reputation (default 0.2)
        execution_parameters: Additional parameters for execution
        todo_list: TODO list for status updates

    Returns:
        Dict with:
        - success: bool
        - result: Execution result from agent
        - agent_used: Which agent was selected
        - verification_score: Quality score from verifier
        - auto_approved: True if auto-approved, False if human review required
        - todo_status: Final status of the TODO item
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[execute_microtask] Starting microtask {todo_id}: {task_name}")

        # CHECK CANCELLATION: Before starting
        if _check_task_cancelled(task_id):
            logger.warning(f"[execute_microtask] Task {task_id} was cancelled by user. Stopping execution.")
            return {
                "success": False,
                "error": "Task cancelled by user",
                "todo_status": "cancelled"
            }

        # Step 1: Mark TODO as in_progress
        from agents.orchestrator.tools.todo_tools import update_todo_item
        await update_todo_item(task_id, todo_id, "in_progress", todo_list)
        logger.info(f"[execute_microtask] Marked {todo_id} as in_progress")

        # CHECK CANCELLATION: Before negotiation
        if _check_task_cancelled(task_id):
            logger.warning(f"[execute_microtask] Task {task_id} cancelled during setup. Stopping.")
            await update_todo_item(task_id, todo_id, "cancelled", todo_list)
            return {
                "success": False,
                "error": "Task cancelled by user",
                "todo_status": "cancelled"
            }

        # Step 2: Discover and negotiate with agent
        logger.info(f"[execute_microtask] Calling negotiator for {todo_id}")
        negotiator_result = await negotiator_agent(
            task_id=task_id,
            capability_requirements=capability_requirements,
            budget_limit=budget_limit,
            min_reputation_score=min_reputation_score,
            task_name=task_name,
            todo_id=todo_id,
        )

        if not negotiator_result.get("success"):
            logger.error(f"[execute_microtask] Negotiation failed for {todo_id}")
            await update_todo_item(task_id, todo_id, "failed", todo_list)
            return {
                "success": False,
                "error": "Agent negotiation failed",
                "todo_id": todo_id,
                "negotiator_result": negotiator_result,
            }

        # Parse negotiator response to extract payment_id and agent_domain
        response_text = negotiator_result.get("response", "")

        # Extract payment_id (looking for patterns like "payment_id": "..." or "Payment ID: ...")
        import re
        payment_id_match = re.search(r'[Pp]ayment[_ ][Ii][Dd]["\s:]+([a-f0-9-]+)', response_text)
        payment_id = payment_id_match.group(1) if payment_id_match else None

        # Extract agent_domain from JSON in negotiator response
        agent_domain = None
        agent_name = None

        # Try to extract JSON from negotiator response using brace-matching
        try:
            json_match = None
            brace_count = 0
            start_idx = -1

            for i, char in enumerate(response_text):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        # Found a complete JSON object
                        json_str = response_text[start_idx:i+1]
                        try:
                            json_data = json.loads(json_str)
                            # Check if this looks like our negotiator response
                            if "selected_agent" in json_data or "payment_id" in json_data:
                                json_match = json_data
                                break
                        except json.JSONDecodeError:
                            continue

            if json_match:
                logger.info(f"[execute_microtask] Successfully extracted JSON from negotiator response")

                # Extract selected_agent info
                if "selected_agent" in json_match:
                    selected_agent = json_match["selected_agent"]
                    if isinstance(selected_agent, dict):
                        agent_domain = selected_agent.get("domain")
                        agent_name = selected_agent.get("domain")  # Use domain as name
                        logger.info(f"[execute_microtask] Extracted agent from JSON: domain={agent_domain}")

                # Extract payment_id from JSON if not already extracted
                if "payment_id" in json_match and not payment_id:
                    payment_id = json_match["payment_id"]
                    logger.info(f"[execute_microtask] Extracted payment_id from JSON: {payment_id}")
            else:
                logger.warning(f"[execute_microtask] Could not extract JSON from negotiator response, trying regex fallback")

                # Fallback to regex patterns if JSON extraction fails
                # Pattern: "domain": "..." inside selected_agent or standalone
                domain_match = re.search(r'["\']?domain["\']?\s*:\s*["\']([a-zA-Z0-9_-]+)["\']', response_text, re.IGNORECASE)
                if domain_match:
                    agent_domain = domain_match.group(1)
                    agent_name = agent_domain

        except Exception as e:
            logger.error(f"[execute_microtask] Error extracting negotiator data: {e}", exc_info=True)

        logger.info(f"[execute_microtask] Extracted payment_id={payment_id}, agent_domain={agent_domain}, agent_name={agent_name}")
        logger.info(f"[execute_microtask] Full negotiator response for debugging: {response_text[:500]}")

        # CHECK CANCELLATION: Before payment authorization
        if _check_task_cancelled(task_id):
            logger.warning(f"[execute_microtask] Task {task_id} cancelled after negotiation. Stopping.")
            await update_todo_item(task_id, todo_id, "cancelled", todo_list)
            return {
                "success": False,
                "error": "Task cancelled by user",
                "todo_status": "cancelled"
            }

        # Step 3: Authorize payment
        if payment_id:
            logger.info(f"[execute_microtask] Authorizing payment {payment_id}")
            auth_result = await authorize_payment_request(payment_id)
            if not auth_result.get("success"):
                logger.warning(f"[execute_microtask] Payment authorization failed, but continuing: {auth_result}")
        else:
            logger.warning("[execute_microtask] No payment_id found in negotiator response, skipping authorization")

        # CHECK CANCELLATION: Before executing task
        if _check_task_cancelled(task_id):
            logger.warning(f"[execute_microtask] Task {task_id} cancelled before execution. Stopping.")
            await update_todo_item(task_id, todo_id, "cancelled", todo_list)
            return {
                "success": False,
                "error": "Task cancelled by user",
                "todo_status": "cancelled"
            }

        # Step 4: Execute task
        logger.info(f"[execute_microtask] Calling executor for {todo_id}")
        executor_result = await executor_agent(
            task_id=task_id,
            agent_domain=agent_domain or "unknown",
            task_description=task_description,
            execution_parameters=execution_parameters,
            todo_id=todo_id,
            todo_list=todo_list,
        )

        # Step 5: Verify results
        logger.info(f"[execute_microtask] Calling verifier for {todo_id}")
        try:
            # FIX: Ensure execution_parameters is a dict, not a string
            logger.info(f"[execute_microtask] execution_parameters type: {type(execution_parameters).__name__}")
            logger.info(f"[execute_microtask] execution_parameters value: {execution_parameters}")

            if execution_parameters and not isinstance(execution_parameters, dict):
                logger.error(f"[execute_microtask] ERROR: execution_parameters is {type(execution_parameters).__name__}, not dict! Converting to dict.")
                # Try to parse as JSON if it's a string
                if isinstance(execution_parameters, str):
                    import json
                    try:
                        execution_parameters = json.loads(execution_parameters)
                        logger.info(f"[execute_microtask] Successfully parsed execution_parameters as JSON")
                    except (json.JSONDecodeError, TypeError):
                        logger.error(f"[execute_microtask] Failed to parse execution_parameters as JSON, wrapping in dict")
                        execution_parameters = {"raw": execution_parameters}
                else:
                    execution_parameters = {}

            verification_criteria = {
                "expected_format": execution_parameters.get("expected_format") if execution_parameters else None,
                "quality_requirements": execution_parameters.get("quality_requirements") if execution_parameters else None,
            }

            # Extract and parse the executor's response
            # The executor_result is a dict like: {"success": True, "response": "...", "task_id": "...", "transport": "..."}
            # We need to extract just the response content for verification
            executor_response_text = executor_result.get("response", "")

            # Try to parse as JSON if it's a JSON string
            import json
            try:
                executor_response_parsed = json.loads(executor_response_text)
                # Ensure it's a dict, not a list or primitive
                if not isinstance(executor_response_parsed, dict):
                    logger.info(f"[execute_microtask] Parsed JSON is {type(executor_response_parsed).__name__}, wrapping in dict")
                    executor_response_parsed = {"output": executor_response_parsed, "format": "json"}
                else:
                    logger.info(f"[execute_microtask] Successfully parsed executor response as JSON dict")
            except (json.JSONDecodeError, TypeError):
                # If not JSON, wrap text in a structured dict for verification
                logger.info(f"[execute_microtask] Executor response is plain text ({len(executor_response_text)} chars), wrapping in dict")
                executor_response_parsed = {
                    "output": executor_response_text,
                    "content": executor_response_text,
                    "format": "text"
                }

            verifier_result = await verifier_agent(
                task_id=task_id,
                payment_id=payment_id or "unknown",
                task_result=executor_response_parsed,  # Pass parsed response, not the wrapper dict
                verification_criteria=verification_criteria,
                verification_mode="standard",
            )

            # DETAILED LOGGING: See what verifier actually returned
            logger.info(f"[execute_microtask] Verifier success status: {verifier_result.get('success')}")
            logger.info(f"[execute_microtask] Verifier raw response (first 1000 chars): {verifier_result.get('response', '')[:1000]}")

            if not verifier_result.get("success"):
                logger.error(f"[execute_microtask] Verifier returned failure: {verifier_result.get('error')}")
                # Trigger human review instead of auto-approve with all dimension scores
                verification_score_data = {
                    "overall_score": 45,  # Below 50 threshold
                    "dimension_scores": {
                        "completeness": 40,
                        "correctness": 40,
                        "academic_rigor": 40,
                        "clarity": 50,
                        "innovation": 50,
                        "ethics": 85
                    },
                    "feedback": f"⚠️ Verification system error: {verifier_result.get('error', 'Unknown error')}\n\nPlease manually review the output."
                }
            else:
                # Step 6: Extract verification score and decide on payment
                verification_score_data = await _extract_verification_score(verifier_result)
                logger.info(f"[execute_microtask] Extracted score data: {verification_score_data}")

            quality_score = verification_score_data.get("overall_score", 0)
            ethics_score = verification_score_data.get("dimension_scores", {}).get("ethics", 0)

            # Validate extraction - if we got 0 scores, extraction failed
            if quality_score == 0 and ethics_score == 0:
                logger.error(f"[execute_microtask] Score extraction failed - got zeros. Response was:")
                logger.error(f"{verifier_result.get('response', '')[:2000]}")
                # Trigger human review with proper fallback scores for ALL dimensions
                quality_score = 45
                ethics_score = 85
                verification_score_data = {
                    "overall_score": 45,
                    "dimension_scores": {
                        "completeness": 40,
                        "correctness": 40,
                        "academic_rigor": 40,
                        "clarity": 50,
                        "innovation": 50,
                        "ethics": 85
                    },
                    "feedback": "⚠️ Score extraction failed. Please manually review."
                }

            logger.info(f"[execute_microtask] Final verification scores - Overall: {quality_score}, Ethics: {ethics_score}")

        except Exception as verification_error:
            logger.error(f"[execute_microtask] Verification exception: {verification_error}", exc_info=True)
            logger.error(f"[execute_microtask] Exception type: {type(verification_error).__name__}")
            logger.error(f"[execute_microtask] Full traceback:", exc_info=True)
            # Trigger human review instead of auto-approve with proper fallback scores for ALL dimensions
            logger.warning(f"[execute_microtask] Triggering human review due to verification error")
            quality_score = 45
            ethics_score = 85
            verification_score_data = {
                "overall_score": 45,
                "dimension_scores": {
                    "completeness": 40,
                    "correctness": 40,
                    "academic_rigor": 40,
                    "clarity": 50,
                    "innovation": 50,
                    "ethics": 85
                },
                "feedback": f"⚠️ Verification crashed: {str(verification_error)}\n\nPlease manually review the output."
            }

        # Decision logic: Auto-approve if score >= 70 AND ethics >= 80
        if quality_score >= 70 and ethics_score >= 80:
            # Auto-approve
            logger.info(f"[execute_microtask] Auto-approving payment {payment_id} (score: {quality_score})")
            update_progress(task_id, f"verification_{todo_id}", "completed", {
                "message": f"✓ Auto-approved: Quality score {quality_score}/100",
                "quality_score": quality_score,
                "auto_approved": True
            })

            if payment_id:
                from agents.verifier.tools.payment_tools import release_payment
                await release_payment(payment_id, f"Auto-approved: Quality score {quality_score}/100")

            # Update agent reputation after successful verification
            from agents.verifier.tools.reputation_tools import increase_agent_reputation
            try:
                reputation_result = await increase_agent_reputation(
                    agent_id=agent_domain or agent_name or "unknown",
                    quality_score=quality_score / 100,  # Convert to 0-1 scale
                    task_id=task_id,
                    verification_result=verification_score_data
                )
                logger.info(f"[execute_microtask] Reputation updated: {reputation_result.get('new_reputation', 'N/A')}")
            except Exception as rep_error:
                logger.error(f"[execute_microtask] Failed to update reputation: {rep_error}", exc_info=True)

            # Mark TODO as completed
            from agents.orchestrator.tools.todo_tools import update_todo_item
            await update_todo_item(task_id, todo_id, "completed", todo_list)

            return {
                "success": True,
                "task_id": task_id,
                "todo_id": todo_id,
                "result": executor_result.get("response", ""),
                "agent_used": agent_domain or "unknown",
                "todo_status": "completed",
                "verification_score": quality_score,
                "auto_approved": True,
                "message": f"✓ Microtask '{task_name}' completed and verified (score: {quality_score}/100)"
            }
        else:
            # Requires human review
            logger.info(f"[execute_microtask] Requesting human verification for {todo_id} (score: {quality_score}, ethics: {ethics_score})")

            # Store verification data for human review
            await _request_human_verification(
                task_id=task_id,
                todo_id=todo_id,
                payment_id=payment_id,
                quality_score=quality_score,
                dimension_scores=verification_score_data.get("dimension_scores", {}),
                feedback=verification_score_data.get("feedback", ""),
                task_result=executor_result.get("response", ""),
                agent_name=agent_name or agent_domain or "unknown",
            )

            # Wait for human decision
            decision = await _wait_for_human_decision(task_id, todo_id)

            if decision["approved"]:
                logger.info(f"[execute_microtask] Human approved verification for {todo_id}")
                if payment_id:
                    from agents.verifier.tools.payment_tools import release_payment
                    await release_payment(payment_id, "Approved by human reviewer")

                # Update agent reputation after human approval
                from agents.verifier.tools.reputation_tools import increase_agent_reputation
                try:
                    reputation_result = await increase_agent_reputation(
                        agent_id=agent_domain or agent_name or "unknown",
                        quality_score=quality_score / 100,  # Convert to 0-1 scale
                        task_id=task_id,
                        verification_result=verification_score_data
                    )
                    logger.info(f"[execute_microtask] Reputation updated after human approval: {reputation_result.get('new_reputation', 'N/A')}")
                except Exception as rep_error:
                    logger.error(f"[execute_microtask] Failed to update reputation: {rep_error}", exc_info=True)

                # Mark TODO as completed
                from agents.orchestrator.tools.todo_tools import update_todo_item
                await update_todo_item(task_id, todo_id, "completed", todo_list)

                return {
                    "success": True,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "result": executor_result.get("response", ""),
                    "agent_used": agent_domain or "unknown",
                    "todo_status": "completed",
                    "verification_score": quality_score,
                    "human_approved": True,
                    "message": f"✓ Microtask '{task_name}' approved by human reviewer"
                }
            else:
                logger.info(f"[execute_microtask] Human rejected verification for {todo_id}")
                if payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(payment_id, decision.get("reason", "Rejected by human reviewer"))

                # Decrease agent reputation after rejection
                from agents.verifier.tools.reputation_tools import decrease_agent_reputation
                try:
                    reputation_result = await decrease_agent_reputation(
                        agent_id=agent_domain or agent_name or "unknown",
                        quality_score=quality_score / 100,  # Convert to 0-1 scale
                        task_id=task_id,
                        verification_result=verification_score_data,
                        failure_reason=decision.get("reason", "Rejected by human reviewer")
                    )
                    logger.info(f"[execute_microtask] Reputation decreased after rejection: {reputation_result.get('new_reputation', 'N/A')}")
                except Exception as rep_error:
                    logger.error(f"[execute_microtask] Failed to update reputation: {rep_error}", exc_info=True)

                # Mark TODO as failed
                from agents.orchestrator.tools.todo_tools import update_todo_item
                await update_todo_item(task_id, todo_id, "failed", todo_list)

                return {
                    "success": False,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "result": executor_result.get("response", ""),
                    "agent_used": agent_domain or "unknown",
                    "todo_status": "failed",
                    "verification_score": quality_score,
                    "human_rejected": True,
                    "error": decision.get("reason", "Rejected by human reviewer"),
                    "message": f"✗ Microtask '{task_name}' rejected by human reviewer"
                }

    except Exception as e:
        logger.error(f"[execute_microtask] Failed for {todo_id}: {e}", exc_info=True)

        # Mark TODO as failed
        from agents.orchestrator.tools.todo_tools import update_todo_item
        await update_todo_item(task_id, todo_id, "failed", todo_list)

        return {
            "success": False,
            "task_id": task_id,
            "todo_id": todo_id,
            "error": str(e),
            "todo_status": "failed",
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

        import json
        from agents.verifier.tools.research_verification_tools import calculate_quality_score

        # CRITICAL FIX: Call calculate_quality_score directly instead of relying on LLM
        # This ensures the dict is passed correctly and avoids the 'str' has no attribute 'get' error
        logger.info(f"[verifier_agent] Calling calculate_quality_score directly with dict (type: {type(task_result).__name__})")

        # Add type validation and logging to catch the exact error
        logger.info(f"[verifier_agent] verification_criteria type: {type(verification_criteria).__name__}")
        logger.info(f"[verifier_agent] verification_criteria content: {verification_criteria}")
        logger.info(f"[verifier_agent] task_result type: {type(task_result).__name__}")
        if isinstance(task_result, dict):
            logger.info(f"[verifier_agent] task_result keys: {list(task_result.keys())}")
        else:
            logger.error(f"[verifier_agent] ERROR: task_result is {type(task_result).__name__}, not dict!")

        # Ensure verification_criteria is a dict
        if not isinstance(verification_criteria, dict):
            logger.error(f"[verifier_agent] ERROR: verification_criteria is {type(verification_criteria).__name__}, wrapping in dict")
            verification_criteria = {"raw": str(verification_criteria)}

        # Extract phase and agent_role from verification_criteria if available
        phase = verification_criteria.get("phase", "experimentation")
        agent_role = verification_criteria.get("agent_role", "unknown")
        phase_validation = {}

        try:
            # Call the scoring function directly with the dict
            quality_score_result = await calculate_quality_score(
                output=task_result,  # Pass the dict directly, not JSON string
                phase=phase,
                agent_role=agent_role,
                phase_validation=phase_validation
            )

            logger.info(f"[verifier_agent] Direct quality score calculation succeeded")
            logger.info(f"[verifier_agent] Scores: {quality_score_result.get('dimension_scores', {})}")

            # Format the scores for the LLM to review
            scores_summary = json.dumps(quality_score_result, indent=2)

        except Exception as score_error:
            logger.error(f"[verifier_agent] Direct quality scoring failed: {score_error}", exc_info=True)
            # If direct scoring fails, we'll let the LLM try
            quality_score_result = None
            scores_summary = f"Direct scoring failed: {score_error}"

        # Convert task_result to JSON string for display in prompt
        if isinstance(task_result, dict):
            task_result_str = json.dumps(task_result, indent=2)
        else:
            task_result_str = str(task_result)

        # Build query based on whether we have pre-calculated scores
        if quality_score_result:
            query = f"""
        Task ID: {task_id}
        Payment ID: {payment_id}
        Verification Mode: {verification_mode}

        Task Result to Verify:
        ```json
        {task_result_str}
        ```

        **QUALITY SCORES (Pre-calculated)**:
        The quality scoring system has already analyzed this output. Here are the results:
        ```json
        {scores_summary}
        ```

        **YOUR TASK**:
        Review the task result and the pre-calculated scores above, then provide your verification assessment using the EXACT scores from above.

        **CRITICAL REQUIREMENTS**:
        1. Use the EXACT dimension scores provided above (completeness, correctness, academic_rigor, clarity, innovation, ethics)
        2. Use the EXACT overall_score provided above
        3. Add your qualitative feedback based on the task result
        4. Return your response in the required JSON format specified in your system prompt
        5. Include ALL 6 dimension scores in your response

        Provide your complete assessment in the required JSON format with the scores above.
        """
        else:
            query = f"""
        Task ID: {task_id}
        Payment ID: {payment_id}
        Verification Mode: {verification_mode}

        Task Result to Verify:
        ```json
        {task_result_str}
        ```

        Verification Criteria:
        {verification_criteria}

        **SCORING NOTE**: Direct quality scoring failed ({scores_summary}).
        Please provide a manual assessment with scores for all 6 dimensions.

        **SCORING CRITERIA** (Each dimension 0-100):
        - **Completeness** (≥80 to pass): All required information is present and thorough
        - **Correctness** (≥85 to pass): Information is accurate, factually correct, no errors
        - **Academic Rigor** (≥75 to pass): Methodology is sound, evidence-based, well-researched
        - **Clarity** (≥70 to pass): Well-organized, easy to understand, professional presentation
        - **Innovation** (≥60 to pass): Creative approach, novel insights, or unique perspective
        - **Ethics** (≥90 to pass - STRICT): No ethical violations, limitations acknowledged, no bias

        **WEIGHTED OVERALL SCORE CALCULATION**:
        Overall = (Completeness×0.2) + (Correctness×0.25) + (Academic_Rigor×0.2) + (Clarity×0.15) + (Innovation×0.1) + (Ethics×0.1)

        Provide your complete assessment in the required JSON format with all dimensions scored.
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

        # Use research mode with deterministic scoring tools
        agent = create_openai_agent(
            api_key=api_key,
            model=model,
            system_prompt=RESEARCH_VERIFIER_SYSTEM_PROMPT,
            tools=[
                # Core verification
                verify_task_result,
                validate_output_schema,
                check_quality_metrics,
                # Code execution
                run_verification_code,
                run_unit_tests,
                validate_code_output,
                # Web search & fact-checking
                search_web,
                verify_fact,
                check_data_source_credibility,
                research_best_practices,
                # Research-specific tools with deterministic scoring
                verify_research_output,
                calculate_quality_score,
                check_citation_quality,
                validate_statistical_significance,
                generate_feedback_report,
                # Payment management
                release_payment,
                reject_and_refund,
            ],
        )

        # If we have pre-calculated scores, use them directly instead of calling the LLM
        if quality_score_result:
            logger.info("[verifier_agent] Using pre-calculated quality scores directly")
            logger.info(f"[verifier_agent] Pre-calculated scores: {quality_score_result}")

            # Format a response that includes the scores in a parseable format
            response_with_scores = json.dumps({
                "overall_score": quality_score_result.get("overall_score", 0),
                "dimension_scores": quality_score_result.get("dimension_scores", {}),
                "feedback": quality_score_result.get("feedback", "Quality analysis completed."),
                "decision": quality_score_result.get("decision", "review_required"),
                "verification_passed": quality_score_result.get("overall_score", 0) >= 70
            }, indent=2)

            logger.info("[verifier_agent] ===== USING PRE-CALCULATED SCORES =====")
            logger.info(f"[verifier_agent] {response_with_scores}")

            return {
                "success": True,
                "task_id": task_id,
                "payment_id": payment_id,
                "response": response_with_scores,
                "transport": "direct_scoring",
            }
        else:
            # Fallback to LLM if direct scoring failed
            logger.warning("[verifier_agent] Direct scoring failed, falling back to LLM verification")
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
