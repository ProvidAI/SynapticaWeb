"""Base class for all research agents."""

import os
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from shared.openai_agent import Agent, create_openai_agent
from shared.database import SessionLocal, Agent as AgentModel, AgentReputation
from datetime import datetime
import json


class BaseResearchAgent(ABC):
    """
    Base class for all research agents in the pipeline.

    This class provides common functionality for:
    - Agent registration in ERC-8004
    - Strands SDK agent creation
    - Reputation tracking
    - Payment handling
    - Output validation
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str],
        pricing: Dict[str, Any],
        model: str = "gpt-4-turbo-preview",
    ):
        """
        Initialize base research agent.

        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
            description: Agent description
            capabilities: List of capabilities for ERC-8004 discovery
            pricing: Pricing model (e.g., {"model": "pay-per-use", "rate": "0.1 HBAR"})
            model: OpenAI model to use
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.pricing = pricing
        self.model = model

        # Check for OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        # No need to create client here, will be created in create_agent()

        # Initialize agent (will be created in create_agent)
        self.agent: Optional[Agent] = None

        # Register agent in database
        self._register_in_database()

    def _register_in_database(self):
        """Register agent in database if not already registered."""
        db = SessionLocal()
        try:
            # Check if agent exists
            existing = db.query(AgentModel).filter(AgentModel.agent_id == self.agent_id).first()

            if not existing:
                # Create new agent record
                agent_record = AgentModel(
                    agent_id=self.agent_id,
                    name=self.name,
                    agent_type="research",
                    description=self.description,
                    capabilities=self.capabilities,
                    status="active",
                    meta={
                        "pricing": self.pricing,
                        "model": self.model,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                db.add(agent_record)

                # Create reputation record
                reputation = AgentReputation(
                    agent_id=self.agent_id,
                    reputation_score=0.5,  # Start at neutral
                    payment_multiplier=1.0,
                )
                db.add(reputation)

                db.commit()
                print(f"Registered agent {self.agent_id} in database")
            else:
                print(f"Agent {self.agent_id} already registered")

        finally:
            db.close()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def get_tools(self) -> List:
        """
        Get the tools for this agent.

        Returns:
            List of tool functions
        """
        pass

    def create_agent(self) -> Agent:
        """
        Create OpenAI agent instance.

        Returns:
            Configured Agent instance
        """
        self.agent = Agent(
            model=self.model,
            system_prompt=self.get_system_prompt(),
            tools=self.get_tools(),
        )
        return self.agent

    async def execute(self, request: str, **kwargs) -> Dict[str, Any]:
        """
        Execute agent with request.

        Args:
            request: Request string for the agent
            **kwargs: Additional parameters (json_mode, max_tokens, etc.)

        Returns:
            Agent response as dictionary
        """
        if not self.agent:
            self.create_agent()

        try:
            # Run agent with JSON mode enabled by default for research agents
            json_mode = kwargs.get('json_mode', True)
            max_tokens = kwargs.get('max_tokens', 4096)

            result = await self.agent._agent.run(request, json_mode=json_mode, max_tokens=max_tokens)

            # Update success metrics
            self._update_reputation(success=True, quality_score=0.8)

            return {
                "success": True,
                "agent_id": self.agent_id,
                "result": result,
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": self.model,
                }
            }

        except Exception as e:
            # Update failure metrics
            self._update_reputation(success=False, quality_score=0.0)

            return {
                "success": False,
                "agent_id": self.agent_id,
                "error": str(e),
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": self.model,
                }
            }

    def _update_reputation(self, success: bool, quality_score: float):
        """
        Update agent reputation based on task outcome.

        Args:
            success: Whether task was successful
            quality_score: Quality score (0-1)
        """
        db = SessionLocal()
        try:
            reputation = db.query(AgentReputation).filter(
                AgentReputation.agent_id == self.agent_id
            ).first()

            if reputation:
                reputation.total_tasks += 1
                if success:
                    reputation.successful_tasks += 1
                else:
                    reputation.failed_tasks += 1

                # Update average quality score
                reputation.average_quality_score = (
                    (reputation.average_quality_score * (reputation.total_tasks - 1) + quality_score)
                    / reputation.total_tasks
                )

                # Calculate new reputation score (simple formula)
                if reputation.total_tasks > 0:
                    success_rate = reputation.successful_tasks / reputation.total_tasks
                    reputation.reputation_score = (
                        0.6 * success_rate + 0.4 * reputation.average_quality_score
                    )

                    # Update payment multiplier based on reputation
                    if reputation.reputation_score >= 0.8:
                        reputation.payment_multiplier = 1.2  # 20% bonus
                    elif reputation.reputation_score >= 0.6:
                        reputation.payment_multiplier = 1.0  # Normal rate
                    elif reputation.reputation_score >= 0.4:
                        reputation.payment_multiplier = 0.9  # 10% penalty
                    else:
                        reputation.payment_multiplier = 0.8  # 20% penalty

                db.commit()

        finally:
            db.close()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get agent metadata for ERC-8004 registration.

        Returns:
            Agent metadata dictionary
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "pricing": self.pricing,
            "api_spec": self.get_api_spec(),
            "owner": os.getenv("HEDERA_ACCOUNT_ID", "0.0.0"),
            "verified": False,  # Will be verified after testing
            "reputation_score": self.get_reputation_score(),
        }

    def get_api_spec(self) -> Dict[str, Any]:
        """
        Get API specification for this agent.

        This is used by the Executor to create dynamic tools.

        Returns:
            API specification dictionary
        """
        # Default spec - override in subclasses for custom endpoints
        return {
            "endpoint": f"https://research-agents.hedera.ai/api/{self.agent_id}",
            "method": "POST",
            "parameters": [
                {"name": "request", "type": "str", "description": "Request for the agent"},
                {"name": "context", "type": "dict", "description": "Additional context"},
            ],
            "response_schema": {
                "success": "bool",
                "result": "any",
                "error": "str",
            },
            "auth_type": "bearer",
            "description": self.description,
        }

    def get_reputation_score(self) -> float:
        """
        Get current reputation score from database.

        Returns:
            Reputation score (0-1)
        """
        db = SessionLocal()
        try:
            reputation = db.query(AgentReputation).filter(
                AgentReputation.agent_id == self.agent_id
            ).first()

            if reputation:
                return reputation.reputation_score
            return 0.5  # Default neutral score

        finally:
            db.close()

    def get_payment_rate(self) -> float:
        """
        Get current payment rate including reputation multiplier.

        Returns:
            Adjusted payment rate in HBAR
        """
        base_rate = float(self.pricing.get("rate", "0.1").replace(" HBAR", ""))

        db = SessionLocal()
        try:
            reputation = db.query(AgentReputation).filter(
                AgentReputation.agent_id == self.agent_id
            ).first()

            if reputation:
                return base_rate * reputation.payment_multiplier
            return base_rate

        finally:
            db.close()

    def validate_output(self, output: Any) -> tuple[bool, Optional[str]]:
        """
        Validate agent output.

        Override this in subclasses to provide specific validation.

        Args:
            output: Agent output to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Default validation - just check output exists
        if not output:
            return False, "Empty output"
        return True, None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.agent_id}: {self.name}>"