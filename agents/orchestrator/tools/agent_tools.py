"""Agent tools - Negotiator, Executor, and Verifier as callable tools."""

import logging
import os
from typing import Any, Dict, Optional

from strands import tool

from shared.a2a import A2AAgentClient
from shared.openai_agent import create_openai_agent
from shared.task_progress import update_progress

from agents.executor.system_prompt import EXECUTOR_SYSTEM_PROMPT
from agents.executor.tools.research_api_executor import (
    list_research_agents,
    execute_research_agent,
    get_agent_metadata,
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
    agent_domain: str,
    task_description: str,
    execution_parameters: Optional[Dict[str, Any]] = None,
    todo_id: Optional[str] = None,
    todo_list: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Execute tasks using research agents from the FastAPI server (port 5000).

    This agent:
    - Calls research agents via HTTP API (no simulation)
    - Returns real agent output
    - Marks microtask as completed when done

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

                # Mark microtask as completed
                if todo_id:
                    from agents.orchestrator.tools.todo_tools import update_todo_item
                    await update_todo_item(task_id, todo_id, "completed", todo_list)

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

        response = await agent.run(query)

        # Log executor response
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE START =====")
        logger.info(f"[executor_agent] {response}")
        logger.info("[executor_agent] ===== EXECUTOR RESPONSE END =====")

        # Check if response contains error indicators
        response_str = str(response).lower()
        error_keywords = ["failed to connect", "error", "exception", "failed", "http", "403", "404", "500"]
        has_error = any(keyword in response_str for keyword in error_keywords)

        # Also check for success indicators - if we find actual results, it's likely successful
        success_keywords = ["research", "analysis", "findings", "results", "summary", "conclusion"]
        has_success = any(keyword in response_str for keyword in success_keywords) and len(response_str) > 200

        # If we detect errors and no clear success, treat as failure
        if has_error and not has_success:
            logger.error(f"[executor_agent] Detected execution failure in response")

            # Classify error type based on response content
            error_type = "quality"  # Default
            retryable = True
            troubleshooting = ["Review task description and requirements"]

            if "failed to connect" in response_str or "connection refused" in response_str:
                error_type = "connectivity"
                retryable = False
                troubleshooting = [
                    "Start research agents server: ./start_research_agents.sh",
                    "Check if port 5000 or 5001 is available",
                    "Test connectivity: curl http://localhost:5000/health"
                ]
            elif "timed out" in response_str or "timeout" in response_str:
                error_type = "timeout"
                retryable = True
                troubleshooting = [
                    "Task may be too complex",
                    "Consider breaking into smaller subtasks",
                    "Check if research agents are overloaded"
                ]
            elif "not found" in response_str or "404" in response_str:
                error_type = "not_found"
                retryable = False
                troubleshooting = [
                    "Verify agent domain is correct",
                    "Check available agents in registry",
                    "Register the agent if it doesn't exist"
                ]

            # Update progress: executor failed
            update_progress(task_id, step_name, "failed", {
                "message": f"✗ Task execution failed - {error_type} error",
                "response": str(response)[:500],
                "todo_id": todo_id,
                "error_type": error_type
            })

            return {
                "success": False,
                "task_id": task_id,
                "error": "Research agent execution failed",
                "error_type": error_type,
                "retryable": retryable,
                "troubleshooting": troubleshooting,
                "response": str(response),
                "transport": "local",
            }

        # Update progress: executor completed
        update_progress(task_id, step_name, "completed", {
            "message": "✓ Task execution completed",
            "response": str(response)[:500],  # Truncate for progress log
            "todo_id": todo_id
        })

        # Mark microtask as completed
        if todo_id:
            from agents.orchestrator.tools.todo_tools import update_todo_item
            await update_todo_item(task_id, todo_id, "completed", todo_list)

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
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Execute a complete microtask with verification and retry logic.

    NEW FLOW WITH VERIFIER INTEGRATION:
    1. Mark TODO as in_progress
    2. Discover and negotiate with agent via negotiator_agent (creates payment proposal)
    3. Execute task via executor_agent (payment NOT authorized yet, held pending verification)
    4. Verify output quality via verifier_agent
       - IF PASS: Authorize payment → Release payment → Mark completed
       - IF FAIL: Retry with same agent (max 3 times)
       - IF 3 FAILURES: Find fallback agent → Retry with new agent
       - IF FALLBACK FAILS: Reject payment → Mark failed

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
        max_retries: Maximum retry attempts with same agent (default 3)

    Returns:
        Dict with:
        - success: bool
        - result: Execution result from agent
        - agent_used: Which agent was selected
        - todo_status: Final status of the TODO item
        - verification_passed: bool
        - quality_score: float (0-100)
        - retry_count: int
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[execute_microtask] Starting microtask {todo_id}: {task_name}")

        # Step 1: Mark TODO as in_progress
        from agents.orchestrator.tools.todo_tools import update_todo_item
        await update_todo_item(task_id, todo_id, "in_progress", todo_list)
        logger.info(f"[execute_microtask] Marked {todo_id} as in_progress")

        # Step 2: Discover and negotiate with agent (creates payment proposal)
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

        # Extract payment_id and agent_domain
        import re
        payment_id_match = re.search(r'[Pp]ayment[_ ][Ii][Dd]["\s:]+([a-f0-9-]+)', response_text)
        payment_id = payment_id_match.group(1) if payment_id_match else None

        agent_domain_match = re.search(r'[Aa]gent[_ ][Ii][Dd]["\s:]+(\d+)', response_text)
        if not agent_domain_match:
            agent_domain_match = re.search(r'[Dd]omain["\s:]+([a-zA-Z0-9-]+)', response_text)
        agent_domain = agent_domain_match.group(1) if agent_domain_match else None

        logger.info(f"[execute_microtask] Extracted payment_id={payment_id}, agent_domain={agent_domain}")

        # PHASE 1.3: Health check before retries
        from agents.orchestrator.tools.health_checks import check_research_api_health

        logger.info(f"[execute_microtask] Performing research API health check before execution")
        api_health = await check_research_api_health()

        if not api_health.get("healthy"):
            logger.error(f"[execute_microtask] Research API health check failed: {api_health.get('error')}")

            # Update progress with health check failure
            update_progress(task_id, f"health_check_{todo_id}", "failed", {
                "message": f"✗ Research API unavailable - cannot execute task",
                "todo_id": todo_id,
                "error": api_health.get("error"),
                "troubleshooting": api_health.get("troubleshooting", [])
            })

            # Reject payment if created
            if payment_id:
                from agents.verifier.tools.payment_tools import reject_and_refund
                await reject_and_refund(payment_id, f"Research API unavailable: {api_health.get('error')}")

            await update_todo_item(task_id, todo_id, "failed", todo_list)

            return {
                "success": False,
                "task_id": task_id,
                "todo_id": todo_id,
                "error": "Research agents API is unavailable",
                "error_type": "connectivity",
                "root_cause": api_health.get("root_cause", api_health.get("error")),
                "troubleshooting": api_health.get("troubleshooting", []),
                "agent_used": agent_domain or "unknown",
                "todo_status": "failed",
                "retry_possible": False,
                "fallback_attempted": False,
                "health_check_failed": True
            }

        logger.info(f"[execute_microtask] Research API health check passed ({api_health.get('response_time', 0):.2f}s)")

        # Track failed agents for fallback selection
        failed_agents = []
        retry_count = 0
        executor_result = None
        verification_passed = False
        quality_score = 0
        verification_feedback = ""

        # Retry loop: Try with same agent up to max_retries times
        while retry_count < max_retries and not verification_passed:
            attempt_num = retry_count + 1
            logger.info(f"[execute_microtask] Execution attempt {attempt_num}/{max_retries} for {todo_id}")

            # Update progress
            update_progress(task_id, f"execution_attempt_{todo_id}", "running", {
                "message": f"Executing task (attempt {attempt_num}/{max_retries})",
                "todo_id": todo_id,
                "attempt": attempt_num,
                "agent_domain": agent_domain
            })

            # Step 3: Execute task (payment NOT authorized yet)
            logger.info(f"[execute_microtask] Calling executor for {todo_id} (attempt {attempt_num})")
            executor_result = await executor_agent(
                task_id=task_id,
                agent_domain=agent_domain or "unknown",
                task_description=task_description,
                execution_parameters=execution_parameters,
                todo_id=todo_id,
                todo_list=None,  # Don't mark completed yet - wait for verification
            )

            if not executor_result.get("success"):
                error_type = executor_result.get("error_type", "unknown")
                is_retryable = executor_result.get("retryable", True)

                logger.error(f"[execute_microtask] Executor failed for {todo_id} (attempt {attempt_num}), error_type={error_type}, retryable={is_retryable}")

                # Update progress with execution failure
                update_progress(task_id, f"execution_failed_{todo_id}", "failed", {
                    "message": f"✗ Execution failed - {error_type} error (attempt {attempt_num}/{max_retries})",
                    "todo_id": todo_id,
                    "attempt": attempt_num,
                    "error": executor_result.get("error", "Unknown error"),
                    "error_type": error_type,
                    "troubleshooting": executor_result.get("troubleshooting", [])
                })

                # SMART RETRY LOGIC: Fail fast on non-retryable errors
                if not is_retryable:
                    logger.warning(f"[execute_microtask] Non-retryable error detected ({error_type}), skipping retries")

                    # Reject payment if created
                    if payment_id:
                        from agents.verifier.tools.payment_tools import reject_and_refund
                        await reject_and_refund(payment_id, f"{error_type} error: {executor_result.get('error')}")

                    await update_todo_item(task_id, todo_id, "failed", todo_list)

                    return {
                        "success": False,
                        "task_id": task_id,
                        "todo_id": todo_id,
                        "error": f"Task failed due to {error_type} error (non-retryable)",
                        "error_type": error_type,
                        "root_cause": executor_result.get("error"),
                        "troubleshooting": executor_result.get("troubleshooting", []),
                        "agent_used": agent_domain or "unknown",
                        "todo_status": "failed",
                        "retry_possible": False,
                        "fallback_attempted": False
                    }

                retry_count += 1
                continue  # Skip verification for failed execution

            # Step 4: Verify output quality ONLY if execution succeeded
            logger.info(f"[execute_microtask] Calling verifier for {todo_id} (attempt {attempt_num})")

            # Build verification criteria
            verification_criteria = {
                "expected_quality_score": 75,
                "phase": "knowledge",  # Default, could be enhanced with task metadata
                "agent_role": "research_agent",
                "task_name": task_name,
                "task_description": task_description
            }

            # Call verifier agent
            verification_result = await verifier_agent(
                task_id=task_id,
                payment_id=payment_id or f"mock_{task_id}_{todo_id}",
                task_result={"agent_output": executor_result.get("response", ""), "agent_domain": agent_domain},
                verification_criteria=verification_criteria,
                verification_mode="standard"
            )

            # Parse verification result
            # The verifier agent returns text response, need to check for acceptance indicators
            verification_response = str(verification_result.get("response", ""))
            verification_response_lower = verification_response.lower()

            # Check if verification itself failed (error in verifier)
            if not verification_result.get("success"):
                logger.error(f"[execute_microtask] Verifier call failed for {todo_id}")
                verification_feedback = verification_result.get("error", "Verifier failed")
                retry_count += 1
                continue

            # Check if executor output contains errors (should never verify error messages)
            executor_output = executor_result.get("response", "").lower()
            if "error" in executor_output or "failed" in executor_output or "exception" in executor_output:
                logger.warning(f"[execute_microtask] Executor output contains errors, treating as verification failure")
                quality_score = 0
                verification_feedback = "Executor returned error response"

                update_progress(task_id, f"verification_{todo_id}_retry", "failed", {
                    "message": f"✗ Verification failed - executor returned error (attempt {attempt_num}/{max_retries})",
                    "todo_id": todo_id,
                    "quality_score": 0,
                    "attempt": attempt_num,
                    "feedback": verification_feedback
                })

                retry_count += 1
                continue

            # Check for quality acceptance
            if "accept" in verification_response_lower or "quality score" in verification_response_lower:
                # Try to extract quality score
                score_match = re.search(r'quality[_ ]score[:\s]+(\d+(?:\.\d+)?)', verification_response)
                if score_match:
                    quality_score = float(score_match.group(1))
                else:
                    quality_score = 75  # Default if can't parse

                # Check if passed (score >= 75 or "accept" mentioned)
                if quality_score >= 75 or ("accept" in verification_response and "reject" not in verification_response):
                    verification_passed = True
                    logger.info(f"[execute_microtask] Verification PASSED for {todo_id} (score: {quality_score})")

                    update_progress(task_id, f"verification_{todo_id}", "completed", {
                        "message": f"✓ Verification passed (quality: {quality_score}/100)",
                        "todo_id": todo_id,
                        "quality_score": quality_score,
                        "attempt": attempt_num
                    })

                    # Step 5: Authorize and release payment
                    if payment_id:
                        logger.info(f"[execute_microtask] Authorizing and releasing payment {payment_id}")

                        # Authorize payment (creates escrow)
                        auth_result = await authorize_payment_request(payment_id)
                        if auth_result.get("success"):
                            logger.info(f"[execute_microtask] Payment authorized: {payment_id}")

                            # Release payment (since verification passed)
                            from agents.verifier.tools.payment_tools import release_payment
                            release_result = await release_payment(payment_id, quality_score, verification_response)
                            logger.info(f"[execute_microtask] Payment released: {release_result}")
                        else:
                            logger.warning(f"[execute_microtask] Payment authorization failed: {auth_result}")

                    # Mark TODO as completed
                    await update_todo_item(task_id, todo_id, "completed", todo_list)

                    return {
                        "success": True,
                        "task_id": task_id,
                        "todo_id": todo_id,
                        "result": executor_result.get("response", ""),
                        "agent_used": agent_domain or "unknown",
                        "todo_status": "completed",
                        "verification_passed": True,
                        "quality_score": quality_score,
                        "retry_count": retry_count,
                        "message": f"✓ Microtask '{task_name}' completed successfully (quality: {quality_score}/100)"
                    }

            # Verification failed
            logger.warning(f"[execute_microtask] Verification FAILED for {todo_id} (attempt {attempt_num})")
            verification_feedback = verification_response[:500]  # Store feedback

            update_progress(task_id, f"verification_{todo_id}_retry", "failed", {
                "message": f"✗ Verification failed (attempt {attempt_num}/{max_retries})",
                "todo_id": todo_id,
                "quality_score": quality_score,
                "attempt": attempt_num,
                "feedback": verification_feedback
            })

            retry_count += 1

        # If we've exhausted retries with same agent, try fallback
        if not verification_passed and retry_count >= max_retries:
            logger.warning(f"[execute_microtask] Max retries reached for {todo_id}, trying fallback agent")
            failed_agents.append(agent_domain)

            update_progress(task_id, f"fallback_{todo_id}", "running", {
                "message": f"Finding backup agent after {max_retries} failures",
                "todo_id": todo_id,
                "failed_agent": agent_domain
            })

            # Find fallback agent
            from agents.orchestrator.tools.fallback_tools import find_fallback_agent

            fallback_result = await find_fallback_agent(
                task_id=task_id,
                todo_id=todo_id,
                failed_agent_id=agent_domain or "unknown",
                capability_requirements=capability_requirements,
                budget_limit=budget_limit,
                min_reputation_score=min_reputation_score
            )

            if not fallback_result.get("success"):
                logger.error(f"[execute_microtask] Fallback agent selection failed: {fallback_result.get('error')}")

                # Reject original payment
                if payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(payment_id, f"Quality verification failed after {max_retries} attempts. No suitable fallback agent found. Score: {quality_score}/100. {verification_feedback}")

                await update_todo_item(task_id, todo_id, "failed", todo_list)

                return {
                    "success": False,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "error": f"Verification failed after {max_retries} attempts, no fallback agent available",
                    "agent_used": agent_domain or "unknown",
                    "todo_status": "failed",
                    "verification_passed": False,
                    "quality_score": quality_score,
                    "retry_count": retry_count,
                    "verification_feedback": verification_feedback,
                    "fallback_attempted": True,
                    "fallback_error": fallback_result.get("error")
                }

            # Got a fallback agent, try one more time
            fallback_agent_data = fallback_result["fallback_agent"]
            fallback_agent_domain = fallback_agent_data["domain"]
            fallback_payment_id = fallback_result["payment_id"]

            logger.info(f"[execute_microtask] Retrying with fallback agent: {fallback_agent_domain}")

            # Mark fallback search as completed
            update_progress(task_id, f"fallback_{todo_id}", "completed", {
                "message": f"✓ Backup agent found: {fallback_agent_domain}",
                "todo_id": todo_id,
                "fallback_agent": fallback_agent_domain,
                "quality_score": fallback_agent_data["quality_score"]
            })

            # Start fallback execution
            update_progress(task_id, f"fallback_execution_{todo_id}", "running", {
                "message": f"Executing with backup agent: {fallback_agent_domain}",
                "todo_id": todo_id,
                "fallback_agent": fallback_agent_domain,
                "quality_score": fallback_agent_data["quality_score"]
            })

            # Execute task with fallback agent
            fallback_executor_result = await executor_agent(
                task_id=task_id,
                agent_domain=fallback_agent_domain,
                task_description=task_description,
                execution_parameters=execution_parameters,
                todo_id=todo_id,
                todo_list=None,  # Don't mark completed yet
            )

            if not fallback_executor_result.get("success"):
                logger.error(f"[execute_microtask] Fallback executor failed for {todo_id}")

                # Mark fallback execution as failed
                update_progress(task_id, f"fallback_execution_{todo_id}", "failed", {
                    "message": f"✗ Fallback agent execution failed",
                    "todo_id": todo_id,
                    "fallback_agent": fallback_agent_domain,
                    "error": fallback_executor_result.get("error", "Unknown error")
                })

                # Reject both payments
                if payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(payment_id, f"Original agent failed verification ({max_retries} attempts)")
                if fallback_payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(fallback_payment_id, "Fallback agent execution failed")

                await update_todo_item(task_id, todo_id, "failed", todo_list)

                return {
                    "success": False,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "error": "Fallback agent execution failed",
                    "agent_used": agent_domain or "unknown",
                    "fallback_agent": fallback_agent_domain,
                    "todo_status": "failed",
                    "verification_passed": False,
                    "quality_score": quality_score,
                    "retry_count": retry_count,
                    "fallback_attempted": True
                }

            # Mark fallback execution as completed
            update_progress(task_id, f"fallback_execution_{todo_id}", "completed", {
                "message": f"✓ Fallback agent execution completed",
                "todo_id": todo_id,
                "fallback_agent": fallback_agent_domain
            })

            # Verify fallback agent output
            logger.info(f"[execute_microtask] Verifying fallback agent output for {todo_id}")

            fallback_verification_criteria = {
                "expected_quality_score": 75,
                "phase": "knowledge",
                "agent_role": "research_agent",
                "task_name": task_name,
                "task_description": task_description
            }

            fallback_verification_result = await verifier_agent(
                task_id=task_id,
                payment_id=fallback_payment_id,
                task_result={"agent_output": fallback_executor_result.get("response", ""), "agent_domain": fallback_agent_domain},
                verification_criteria=fallback_verification_criteria,
                verification_mode="standard"
            )

            fallback_verification_response = str(fallback_verification_result.get("response", "")).lower()

            # Check fallback verification
            fallback_quality_score = 0
            score_match = re.search(r'quality[_ ]score[:\s]+(\d+(?:\.\d+)?)', fallback_verification_response)
            if score_match:
                fallback_quality_score = float(score_match.group(1))

            if fallback_quality_score >= 75 or ("accept" in fallback_verification_response and "reject" not in fallback_verification_response):
                # Fallback succeeded!
                logger.info(f"[execute_microtask] Fallback agent PASSED verification (score: {fallback_quality_score})")

                update_progress(task_id, f"fallback_verification_{todo_id}", "completed", {
                    "message": f"✓ Fallback agent verified (quality: {fallback_quality_score}/100)",
                    "todo_id": todo_id,
                    "quality_score": fallback_quality_score,
                    "fallback_agent": fallback_agent_domain
                })

                # Reject original payment
                if payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(payment_id, f"Original agent failed verification. Fallback agent used instead.")

                # Authorize and release fallback payment
                if fallback_payment_id:
                    auth_result = await authorize_payment_request(fallback_payment_id)
                    if auth_result.get("success"):
                        from agents.verifier.tools.payment_tools import release_payment
                        await release_payment(fallback_payment_id, fallback_quality_score, fallback_verification_response)

                await update_todo_item(task_id, todo_id, "completed", todo_list)

                return {
                    "success": True,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "result": fallback_executor_result.get("response", ""),
                    "agent_used": agent_domain or "unknown",
                    "fallback_agent": fallback_agent_domain,
                    "todo_status": "completed",
                    "verification_passed": True,
                    "quality_score": fallback_quality_score,
                    "retry_count": retry_count,
                    "fallback_attempted": True,
                    "fallback_succeeded": True,
                    "message": f"✓ Microtask '{task_name}' completed with fallback agent (quality: {fallback_quality_score}/100)"
                }
            else:
                # Fallback also failed
                logger.error(f"[execute_microtask] Fallback agent FAILED verification (score: {fallback_quality_score})")

                # Mark fallback verification as failed
                update_progress(task_id, f"fallback_verification_{todo_id}", "failed", {
                    "message": f"✗ Fallback agent failed verification (quality: {fallback_quality_score}/100)",
                    "todo_id": todo_id,
                    "quality_score": fallback_quality_score,
                    "fallback_agent": fallback_agent_domain
                })

                # Reject both payments
                if payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(payment_id, f"Original agent failed verification ({max_retries} attempts)")
                if fallback_payment_id:
                    from agents.verifier.tools.payment_tools import reject_and_refund
                    await reject_and_refund(fallback_payment_id, f"Fallback agent also failed verification (score: {fallback_quality_score}/100)")

                await update_todo_item(task_id, todo_id, "failed", todo_list)

                return {
                    "success": False,
                    "task_id": task_id,
                    "todo_id": todo_id,
                    "error": "Both original and fallback agents failed verification",
                    "agent_used": agent_domain or "unknown",
                    "fallback_agent": fallback_agent_domain,
                    "todo_status": "failed",
                    "verification_passed": False,
                    "quality_score": quality_score,
                    "fallback_quality_score": fallback_quality_score,
                    "retry_count": retry_count,
                    "fallback_attempted": True,
                    "fallback_succeeded": False
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
