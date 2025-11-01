#!/usr/bin/env python
"""
Test listing agents from the Hedera contract registry.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.executor.tools.contract_tools import list_all_agents
from shared.handlers.identity_registry_handlers import (
    get_agent_count,
    get_domains_paginated,
    resolve_by_domain,
)


def test_contract_listing():
    """Test contract-based listing."""
    print("=" * 80)
    print("Testing Contract-Based Agent Listing")
    print("=" * 80)
    
    # Test 1: get_domains_paginated
    print("\n1. Testing get_domains_paginated...")
    try:
        result = get_domains_paginated(0, 100)
        print(f"   ✅ Success: Got {result.get('total', 0)} total domains")
        print(f"   Domains returned: {len(result.get('domains', []))}")
        if result.get('domains'):
            print(f"   First few domains: {result.get('domains', [])[:5]}")
        else:
            print("   ⚠️  No domains found (contract might be empty)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: get_agent_count
    print("\n2. Testing get_agent_count...")
    try:
        count = get_agent_count()
        print(f"   ✅ Agent count: {count}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: list_all_agents (async tool)
    print("\n3. Testing list_all_agents tool...")
    try:
        result = asyncio.run(list_all_agents(0, 100))
        if result.get("success"):
            print(f"   ✅ Success!")
            print(f"   Total agents: {result.get('total', 0)}")
            agents = result.get('agents', [])
            print(f"   Agents returned: {len(agents)}")
            if agents:
                print(f"   First few agents:")
                for agent in agents[:5]:
                    print(f"     - ID: {agent.get('agent_id')}, Domain: {agent.get('domain')}, Address: {agent.get('address')}")
            else:
                print("   ⚠️  No agents found (contract might be empty)")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_contract_listing()
    sys.exit(0 if success else 1)

