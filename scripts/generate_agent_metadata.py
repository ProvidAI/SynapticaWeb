#!/usr/bin/env python
"""
Generate JSON metadata files for all research agents.

These metadata files conform to agent metadata standards and include:
- Agent identity (name, domain, description)
- API endpoints and specifications
- Capabilities and services offered
- Pricing information
- Version and contact info
"""

import json
import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH when running this script directly
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from shared.database import Agent as AgentModel
from shared.database import SessionLocal

# Output directory for metadata files
METADATA_DIR = Path(__file__).parent.parent / "agent_metadata"


def generate_agent_metadata(agent: AgentModel) -> dict:
    """
    Generate comprehensive metadata for an agent.

    Args:
        agent: Agent database model

    Returns:
        Dict containing agent metadata in standard format
    """
    # Base metadata structure
    metadata = {
        "version": "1.0.0",
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description or f"{agent.name} - Research agent for AI marketplace",
        "domain": agent.agent_id,

        # Capabilities from database
        "capabilities": agent.capabilities if agent.capabilities else [
            "research", "analysis", "data-processing"
        ],

        # API endpoint information
        "endpoints": {
            "base_url": f"https://api.providai.io/agents/{agent.agent_id}",
            "execute": {
                "method": "POST",
                "path": f"/agents/{agent.agent_id}/execute",
                "description": "Execute agent task",
                "parameters": {
                    "task_description": {
                        "type": "string",
                        "required": True,
                        "description": "Description of the task to execute"
                    },
                    "context": {
                        "type": "object",
                        "required": False,
                        "description": "Additional context for the task"
                    }
                },
                "response": {
                    "type": "object",
                    "properties": {
                        "success": "boolean",
                        "result": "object",
                        "metadata": "object"
                    }
                }
            },
            "status": {
                "method": "GET",
                "path": f"/agents/{agent.agent_id}/status",
                "description": "Get agent status and availability"
            }
        },

        # Pricing information (from agent metadata if available)
        "pricing": {
            "currency": "HBAR",
            "base_rate": float(agent.meta.get("payment_rate", 0.05)) if agent.meta else 0.05,
            "rate_type": agent.meta.get("payment_model", "per_task") if agent.meta else "per_task",
            "description": f"Base rate for {agent.name} services"
        },

        # Authentication
        "authentication": {
            "type": "bearer",
            "description": "Bearer token authentication via x402 payment protocol"
        },

        # Service level
        "service_level": {
            "availability": "99.9%",
            "average_response_time": "30s",
            "max_concurrent_tasks": 10
        },

        # Contact and legal
        "contact": {
            "support_email": "support@providai.io",
            "documentation": f"https://docs.providai.io/agents/{agent.agent_id}"
        },

        "terms_of_service": "https://providai.io/terms",
        "privacy_policy": "https://providai.io/privacy",

        # Technical metadata
        "created_at": agent.created_at.isoformat() if hasattr(agent, 'created_at') and agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if hasattr(agent, 'updated_at') and agent.updated_at else None,
        "status": agent.status or "active",

        # ERC-8004 compliance
        "erc8004_version": "0.3",
        "agent_type": "research_agent",
        "blockchain": {
            "network": "hedera_testnet",
            "registry_address": os.getenv("IDENTITY_REGISTRY_ADDRESS", ""),
        }
    }

    return metadata


def save_metadata_file(agent_id: str, metadata: dict) -> Path:
    """
    Save metadata to JSON file.

    Args:
        agent_id: Agent identifier
        metadata: Metadata dictionary

    Returns:
        Path to saved file
    """
    # Create output directory
    METADATA_DIR.mkdir(exist_ok=True)

    # Save to file
    filepath = METADATA_DIR / f"{agent_id}.json"
    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=2)

    return filepath


def generate_all_metadata():
    """Generate metadata files for all active agents."""

    print("=" * 80)
    print("GENERATING AGENT METADATA FILES")
    print("=" * 80)

    # Load agents from database
    db = SessionLocal()
    try:
        agents = db.query(AgentModel).filter(AgentModel.status == "active").all()

        if not agents:
            print("\n❌ No active agents found in database")
            return

        print(f"\n📋 Found {len(agents)} active agents")
        print(f"📁 Output directory: {METADATA_DIR}")
        print()

        generated = []

        for i, agent in enumerate(agents, 1):
            print(f"[{i}/{len(agents)}] {agent.name} ({agent.agent_id})")

            # Generate metadata
            metadata = generate_agent_metadata(agent)

            # Save to file
            filepath = save_metadata_file(agent.agent_id, metadata)
            generated.append(filepath)

            print(f"   ✅ Saved to: {filepath}")

        print("\n" + "=" * 80)
        print("METADATA GENERATION COMPLETE")
        print("=" * 80)
        print(f"\n✅ Generated {len(generated)} metadata files")
        print(f"📁 Location: {METADATA_DIR}")

        print("\n📝 Next Steps:")
        print("   1. Review generated metadata files")
        print("   2. Upload metadata to IPFS or web server")
        print("   3. Update registration script with metadata URIs")
        print("   4. Redeploy IdentityRegistry contract with new ABI")
        print("   5. Register agents with metadata URIs")

    finally:
        db.close()


if __name__ == "__main__":
    generate_all_metadata()
