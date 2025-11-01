"""Problem Framer Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from agents.research.base_research_agent import BaseResearchAgent
from .system_prompt import PROBLEM_FRAMER_SYSTEM_PROMPT
from .tools import (
    parse_research_query,
    generate_hypothesis,
    scope_research_problem,
    check_research_novelty,
    assess_feasibility,
    extract_keywords,
)
from shared.research.validators import validate_problem_statement


class ProblemFramerAgent(BaseResearchAgent):
    """
    Problem Framer Agent for converting research queries into formal problems.

    This agent:
    - Converts vague queries into formal research questions
    - Generates testable hypotheses
    - Defines research scope and boundaries
    - Extracts keywords for literature search
    - Assesses feasibility and novelty
    """

    def __init__(self):
        """Initialize Problem Framer Agent."""
        super().__init__(
            agent_id="problem-framer-001",
            name="Research Problem Framer",
            description="Converts vague research queries into formal research questions with hypotheses and scope",
            capabilities=[
                "research-framing",
                "hypothesis-generation",
                "domain-taxonomy",
                "scope-definition",
                "keyword-extraction",
            ],
            pricing={
                "model": "pay-per-use",
                "rate": "0.1 HBAR",
                "unit": "per_framing"
            }
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return PROBLEM_FRAMER_SYSTEM_PROMPT

    def get_tools(self) -> List:
        """Get the tools for this agent."""
        return [
            parse_research_query,
            generate_hypothesis,
            scope_research_problem,
            check_research_novelty,
            assess_feasibility,
            extract_keywords,
        ]

    async def frame_problem(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Frame a research problem from a query.

        Args:
            query: User's research query
            context: Optional context (constraints, preferences, etc.)

        Returns:
            Framed problem with all components
        """
        # Build request for the agent
        request = f"""
        Frame the following research query into a formal research problem:

        Query: {query}

        Context:
        - Budget: {context.get('budget', 5.0) if context else 5.0} HBAR
        - Time: {context.get('timeframe', '30 days') if context else '30 days'}
        - Domain preference: {context.get('domain', 'Not specified') if context else 'Not specified'}

        Please:
        1. Parse the query to understand its components
        2. Generate a formal research question
        3. Create a testable hypothesis
        4. Define clear scope and boundaries
        5. Extract relevant keywords (10-15)
        6. Assess feasibility and novelty
        7. Provide the output in the specified JSON format
        """

        # Execute agent
        result = await self.execute(request)

        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'Failed to frame problem')
            }

        try:
            # Parse the agent's response
            agent_output = result['result']

            # If the output is a string, try to parse it as JSON
            if isinstance(agent_output, str):
                # Try to extract JSON from the response
                json_start = agent_output.find('{')
                json_end = agent_output.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = agent_output[json_start:json_end]
                    problem_data = json.loads(json_str)
                else:
                    # Agent didn't return JSON, construct from response
                    problem_data = self._construct_problem_from_text(agent_output, query)
            else:
                problem_data = agent_output

            # Validate the output
            is_valid, error, validated_problem = validate_problem_statement(problem_data)

            if not is_valid:
                return {
                    'success': False,
                    'error': f'Validation failed: {error}',
                    'raw_output': problem_data
                }

            # Store as artifact in database (would implement this)
            # self._store_artifact(validated_problem)

            return {
                'success': True,
                'problem_statement': validated_problem.dict(),
                'agent_id': self.agent_id,
                'metadata': {
                    'framing_model': self.model,
                    'original_query': query,
                    'payment_due': self.get_payment_rate()
                }
            }

        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Failed to parse agent output as JSON: {str(e)}',
                'raw_output': result['result']
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing problem statement: {str(e)}'
            }

    def _construct_problem_from_text(self, text: str, query: str) -> Dict[str, Any]:
        """
        Construct problem statement from text response if JSON parsing fails.

        Args:
            text: Agent's text response
            query: Original query

        Returns:
            Problem statement dictionary
        """
        # This is a fallback method to extract information from text
        # In production, the agent should always return proper JSON
        return {
            "query": query,
            "research_question": self._extract_research_question(text) or query,
            "hypothesis": self._extract_hypothesis(text) or f"There exists a relationship related to: {query}",
            "scope": {
                "included": ["To be determined"],
                "excluded": ["To be determined"],
                "timeframe": "Not specified",
                "domain_boundaries": "To be defined"
            },
            "keywords": self._extract_keywords_from_text(text, query),
            "domain": "Research",
            "feasibility_score": 0.5,
            "novelty_score": 0.5,
            "rationale": "Extracted from text response"
        }

    def _extract_research_question(self, text: str) -> Optional[str]:
        """Extract research question from text."""
        # Look for patterns like "research question:" or "RQ:"
        patterns = ['research question:', 'formal question:', 'rq:', 'question:']
        text_lower = text.lower()

        for pattern in patterns:
            if pattern in text_lower:
                start = text_lower.find(pattern) + len(pattern)
                # Find the end (next newline or period)
                end = text.find('\n', start)
                if end == -1:
                    end = text.find('.', start) + 1
                if end > start:
                    return text[start:end].strip()
        return None

    def _extract_hypothesis(self, text: str) -> Optional[str]:
        """Extract hypothesis from text."""
        patterns = ['hypothesis:', 'h1:', 'primary hypothesis:', 'we hypothesize']
        text_lower = text.lower()

        for pattern in patterns:
            if pattern in text_lower:
                start = text_lower.find(pattern) + len(pattern)
                end = text.find('\n', start)
                if end == -1:
                    end = text.find('.', start) + 1
                if end > start:
                    return text[start:end].strip()
        return None

    def _extract_keywords_from_text(self, text: str, query: str) -> List[str]:
        """Extract keywords from text and query."""
        keywords = []

        # Look for keyword section
        if 'keywords:' in text.lower():
            start = text.lower().find('keywords:') + 9
            end = text.find('\n', start)
            if end > start:
                keyword_str = text[start:end]
                keywords = [k.strip() for k in keyword_str.split(',')]

        # Add words from query
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'how', 'what', 'why', 'does'}
        query_words = [w for w in query.lower().split() if w not in stop_words and len(w) > 3]
        keywords.extend(query_words[:5])

        # Ensure minimum keywords
        if len(keywords) < 3:
            keywords.extend(['research', 'analysis', 'study'])

        return list(set(keywords))[:15]  # Unique keywords, max 15


# Create singleton instance
problem_framer_agent = ProblemFramerAgent()


# Convenience function for use as tool by other agents
async def frame_research_problem(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Tool function for framing research problems.

    Args:
        query: Research query to frame
        context: Optional context

    Returns:
        Framed problem statement
    """
    return await problem_framer_agent.frame_problem(query, context)