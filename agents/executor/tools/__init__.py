"""Tools for Executor agent."""

from .contract_tools import (
    get_agent_metadata_for_execution,
    list_all_agents,
    query_agent_by_domain,
    query_agent_by_id,
)
from .execution_tools import (
    create_tools_from_metadata,
    execute_agent_tool_from_metadata,
    execute_shell_command,
    fetch_metadata_from_uri,
    get_tool_template,
    use_agent_tool,
)
from .meta_tools import create_dynamic_tool, list_dynamic_tools, load_and_execute_tool

__all__ = [
    "create_dynamic_tool",
    "load_and_execute_tool",
    "list_dynamic_tools",
    "execute_shell_command",
    "get_tool_template",
    "query_agent_by_id",
    "query_agent_by_domain",
    "list_all_agents",
    "get_agent_metadata_for_execution",
    "fetch_metadata_from_uri",
    "create_tools_from_metadata",
    "execute_agent_tool_from_metadata",
    "use_agent_tool",
]
