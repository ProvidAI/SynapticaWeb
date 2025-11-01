"""Execution utilities for Executor agent."""

import json
import subprocess
from typing import Any, Dict, Optional

import httpx
from strands import tool


@tool
async def fetch_metadata_from_uri(metadata_uri: str) -> Dict[str, Any]:
    """
    Fetch agent metadata from a URI (IPFS, HTTP, etc.).

    Args:
        metadata_uri: URI pointing to agent metadata JSON

    Returns:
        Parsed metadata dictionary following ERC-8004 format:
        {
            "name": str,
            "version": str,
            "description": str,
            "capabilities": List[str],
            "api": {
                "baseUrl": str,
                "endpoints": [...],
                "authentication": str,
                "rateLimit": str
            },
            "pricing": {...},
            "contact": {...},
            "tags": List[str],
            "license": str
        }
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(metadata_uri)
            response.raise_for_status()
            metadata = response.json()
            
            return {
                "success": True,
                "metadata": metadata,
            }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error fetching metadata: {str(e)}",
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON in metadata: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error fetching metadata: {str(e)}",
        }


@tool
async def create_tools_from_metadata(
    task_id: str,
    agent_metadata: Dict[str, Any],
    metadata_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create dynamic tools from agent metadata JSON.

    Args:
        task_id: Associated task ID
        agent_metadata: Basic agent info (agent_id, domain, address)
        metadata_json: Full metadata JSON from URI with API endpoints

    Returns:
        Dictionary with created tools information
    """
    created_tools = []
    errors = []

    api_info = metadata_json.get("api", {})
    base_url = api_info.get("baseUrl", "")
    endpoints = api_info.get("endpoints", [])
    auth_type = api_info.get("authentication", "bearer_token")
    
    # Normalize auth type
    if auth_type == "bearer_token":
        auth_type = "bearer"
    elif "api_key" in auth_type.lower():
        auth_type = "api_key"

    for endpoint in endpoints:
        endpoint_path = endpoint.get("path", "")
        method = endpoint.get("method", "POST")
        description = endpoint.get("description", "")
        parameters = endpoint.get("parameters", {})
        
        # Build full endpoint URL
        if endpoint_path.startswith("http"):
            full_endpoint = endpoint_path
        else:
            # Ensure proper URL joining
            base = base_url.rstrip("/")
            path = endpoint_path.lstrip("/")
            full_endpoint = f"{base}/{path}" if path else base

        # Convert parameters dict to list format for tool creation
        param_list = []
        for param_name, param_type in parameters.items():
            param_list.append({
                "name": param_name,
                "type": str(param_type) if isinstance(param_type, type) else param_type,
                "description": f"Parameter {param_name}",
            })

        # Generate tool name from endpoint path
        tool_name = endpoint_path.replace("/", "_").replace("-", "_").lstrip("_")
        if not tool_name:
            tool_name = f"execute_{method.lower()}"
        tool_name = f"call_{agent_metadata.get('domain', 'agent').replace('-', '_')}_{tool_name}"

        tool_spec = {
            "endpoint": full_endpoint,
            "method": method,
            "parameters": param_list,
            "auth_type": auth_type,
            "description": description or f"Call {agent_metadata.get('name', 'agent')} {endpoint_path} endpoint",
        }

        try:
            from .meta_tools import create_dynamic_tool
            
            result = await create_dynamic_tool(
                task_id=task_id,
                tool_name=tool_name,
                agent_metadata=agent_metadata,
                tool_spec=tool_spec,
            )
            created_tools.append(result)
        except Exception as e:
            errors.append({
                "endpoint": endpoint_path,
                "error": str(e),
            })

    return {
        "success": len(created_tools) > 0,
        "created_tools": created_tools,
        "errors": errors,
        "total_endpoints": len(endpoints),
        "successful": len(created_tools),
    }


@tool
async def execute_agent_tool_from_metadata(
    task_id: str,
    agent_id: Optional[int] = None,
    domain: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute an agent tool by fetching metadata and creating/executing the tool.

    This is the main workflow function:
    1. Query agent from registry
    2. Fetch metadata from URI
    3. Create dynamic tool from endpoint
    4. Execute the tool

    Args:
        task_id: Task ID for tool tracking
        agent_id: Agent ID from contract (optional)
        domain: Agent domain name (optional)
        endpoint_path: Specific API endpoint path to use (optional, uses first if not specified)
        parameters: Parameters to pass to the tool
        api_key: Optional API key for authentication

    Returns:
        Execution result
    """
    try:
        # Step 1: Get agent metadata from registry
        from .contract_tools import get_agent_metadata_for_execution
        
        agent_info = await get_agent_metadata_for_execution(agent_id=agent_id, domain=domain)
        if not agent_info.get("success"):
            return {
                "success": False,
                "error": f"Agent not found: {agent_info.get('error', 'Unknown error')}",
            }

        # Step 2: Fetch metadata from URI
        metadata_uri = agent_info.get("metadata_uri")
        if not metadata_uri:
            return {
                "success": False,
                "error": "Agent metadata URI not available. Cannot create tools without metadata.",
            }

        fetch_result = await fetch_metadata_from_uri(metadata_uri)
        if not fetch_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to fetch metadata: {fetch_result.get('error', 'Unknown error')}",
            }

        metadata_json = fetch_result["metadata"]

        # Step 3: Find the endpoint
        api_info = metadata_json.get("api", {})
        endpoints = api_info.get("endpoints", [])
        
        if not endpoints:
            return {
                "success": False,
                "error": "No API endpoints found in metadata",
            }

        # Find specific endpoint or use first
        selected_endpoint = None
        if endpoint_path:
            for ep in endpoints:
                if ep.get("path") == endpoint_path:
                    selected_endpoint = ep
                    break
            if not selected_endpoint:
                return {
                    "success": False,
                    "error": f"Endpoint '{endpoint_path}' not found in metadata",
                }
        else:
            selected_endpoint = endpoints[0]
            endpoint_path = selected_endpoint.get("path", "")

        # Step 4: Create tool for this endpoint
        base_url = api_info.get("baseUrl", "")
        if endpoint_path.startswith("http"):
            full_endpoint = endpoint_path
        else:
            base = base_url.rstrip("/")
            path = endpoint_path.lstrip("/")
            full_endpoint = f"{base}/{path}" if path else base

        auth_type = api_info.get("authentication", "bearer_token")
        if auth_type == "bearer_token":
            auth_type = "bearer"
        elif "api_key" in auth_type.lower():
            auth_type = "api_key"

        endpoint_params = selected_endpoint.get("parameters", {})
        param_list = []
        for param_name, param_type in endpoint_params.items():
            param_list.append({
                "name": param_name,
                "type": str(param_type) if isinstance(param_type, type) else param_type,
                "description": f"Parameter {param_name}",
            })

        tool_name = endpoint_path.replace("/", "_").replace("-", "_").lstrip("_")
        if not tool_name:
            tool_name = f"execute_{selected_endpoint.get('method', 'POST').lower()}"
        tool_name = f"call_{agent_info.get('domain', 'agent').replace('-', '_')}_{tool_name}"

        tool_spec = {
            "endpoint": full_endpoint,
            "method": selected_endpoint.get("method", "POST"),
            "parameters": param_list,
            "auth_type": auth_type,
            "description": selected_endpoint.get("description", ""),
        }

        from .meta_tools import create_dynamic_tool, load_and_execute_tool

        # Step 5: Create the tool
        create_result = await create_dynamic_tool(
            task_id=task_id,
            tool_name=tool_name,
            agent_metadata={
                "agent_id": agent_info.get("agent_id"),
                "domain": agent_info.get("domain"),
                "address": agent_info.get("address"),
                "name": metadata_json.get("name", agent_info.get("domain")),
            },
            tool_spec=tool_spec,
        )

        # Step 6: Execute the tool
        exec_params = parameters or {}
        if api_key and auth_type != "none":
            exec_params["api_key"] = api_key

        exec_result = await load_and_execute_tool(
            tool_name=tool_name,
            parameters=exec_params,
        )

        return {
            "success": exec_result.get("success", False),
            "tool_created": create_result,
            "execution_result": exec_result,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error executing agent tool: {str(e)}",
        }


@tool
async def execute_shell_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a shell command.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds

    Returns:
        Command execution result
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@tool
async def get_tool_template(template_type: str = "basic") -> Dict[str, Any]:
    """
    Get a template for creating dynamic tools.

    Args:
        template_type: Type of template (basic, authenticated, streaming)

    Returns:
        Tool template code and documentation
    """
    templates = {
        "basic": '''
async def {tool_name}(input_data: str) -> Dict[str, Any]:
    """
    Basic tool template.

    Args:
        input_data: Input data

    Returns:
        Result dictionary
    """
    import httpx

    endpoint = "{endpoint_url}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"data": input_data}
        )
        response.raise_for_status()
        return response.json()
''',
        "authenticated": '''
async def {tool_name}(input_data: str, api_key: str) -> Dict[str, Any]:
    """
    Authenticated tool template.

    Args:
        input_data: Input data
        api_key: API authentication key

    Returns:
        Result dictionary
    """
    import httpx

    endpoint = "{endpoint_url}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"data": input_data},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        return response.json()
''',
        "streaming": '''
async def {tool_name}(input_data: str) -> Dict[str, Any]:
    """
    Streaming tool template.

    Args:
        input_data: Input data

    Returns:
        Streamed results
    """
    import httpx

    endpoint = "{endpoint_url}"
    results = []

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", endpoint, json={"data": input_data}) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                results.append(chunk)

    return {"chunks": results}
''',
    }

    template = templates.get(template_type, templates["basic"])

    return {
        "template_type": template_type,
        "template_code": template,
        "usage": "Replace {tool_name} and {endpoint_url} with actual values",
    }


@tool
async def use_agent_tool(
    agent_id: Optional[int] = None,
    domain: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use an agent tool by querying registry, fetching metadata, and executing.

    This is a convenience function that combines:
    - Querying agent from registry
    - Fetching metadata from URI
    - Creating dynamic tool from metadata
    - Executing the tool

    Args:
        agent_id: Agent ID from contract (optional)
        domain: Agent domain name (optional)
        endpoint_path: Specific API endpoint path (optional, uses first if not specified)
        parameters: Parameters to pass to the tool
        api_key: Optional API key for authentication
        task_id: Task ID for tracking (optional, auto-generated if not provided)

    Returns:
        Execution result with tool output
    """
    import uuid
    
    if not task_id:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    return await execute_agent_tool_from_metadata(
        task_id=task_id,
        agent_id=agent_id,
        domain=domain,
        endpoint_path=endpoint_path,
        parameters=parameters,
        api_key=api_key,
    )
