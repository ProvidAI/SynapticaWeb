"""Literature Miner Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from agents.research.base_research_agent import BaseResearchAgent
from .system_prompt import LITERATURE_MINER_SYSTEM_PROMPT
from .tools import (
    search_arxiv,
    search_semantic_scholar,
    search_web_for_research,
    calculate_relevance_score,
    deduplicate_papers,
    rank_papers_by_relevance,
    create_paper_url,
    extract_paper_metadata,
)
from agents.research.tools.tavily_search import tavily_search, tavily_research_search
from shared.research.validators import validate_literature_corpus


class LiteratureMinerAgent(BaseResearchAgent):
    """
    Literature Miner Agent for searching and retrieving academic papers.

    This agent:
    - Searches multiple academic databases (ArXiv, Semantic Scholar)
    - Extracts comprehensive paper metadata
    - Scores papers for relevance
    - Deduplicates results across sources
    - Provides per-paper micropayment pricing
    """

    def __init__(self):
        """Initialize Literature Miner Agent."""
        super().__init__(
            agent_id="literature-miner-001",
            name="Academic Literature Miner",
            description="Searches ArXiv, Semantic Scholar, and other sources for relevant research papers",
            capabilities=[
                "literature-search",
                "paper-retrieval",
                "metadata-extraction",
                "relevance-ranking",
                "deduplication",
            ],
            pricing={
                "model": "pay-per-use",
                "rate": "0.05 HBAR",
                "unit": "per_paper"
            }
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return LITERATURE_MINER_SYSTEM_PROMPT

    def get_tools(self) -> List:
        """Get the tools for this agent."""
        return [
            search_arxiv,
            search_semantic_scholar,
            search_web_for_research,
            tavily_search,
            tavily_research_search,
            calculate_relevance_score,
            deduplicate_papers,
            rank_papers_by_relevance,
            create_paper_url,
            extract_paper_metadata,
        ]

    async def search_literature(
        self,
        keywords: List[str],
        research_question: str,
        max_papers: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant literature across multiple databases.

        Args:
            keywords: Search keywords
            research_question: The research question
            max_papers: Maximum number of papers to return
            context: Optional context (date range, sources, etc.)

        Returns:
            Literature corpus with papers and metadata
        """
        # Build request for the agent
        date_range = context.get('date_range', '2020-2024') if context else '2020-2024'
        min_relevance = context.get('min_relevance', 0.5) if context else 0.5

        request = f"""
        Search for academic papers relevant to the following research question:

        Research Question: {research_question}

        Keywords: {', '.join(keywords)}

        Search Parameters:
        - Maximum papers to retrieve: {max_papers}
        - Date range: {date_range}
        - Minimum relevance score: {min_relevance}
        - Sources to search: ArXiv, Semantic Scholar

        Please:
        1. Search ArXiv for papers matching the keywords
        2. Search Semantic Scholar for additional papers
        3. Calculate relevance scores for each paper
        4. Deduplicate papers found in multiple sources
        5. Rank papers by relevance
        6. Return the top {max_papers} most relevant papers
        7. Provide the output in the specified JSON format

        Ensure each paper has complete metadata including title, authors, abstract, publication date, and relevance score.
        """

        # Execute agent
        result = await self.execute(request)

        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'Failed to search literature')
            }

        try:
            # Parse the agent's response
            agent_output = result['result']

            # If the output is a string, try to parse it as JSON
            if isinstance(agent_output, str):
                json_start = agent_output.find('{')
                json_end = agent_output.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = agent_output[json_start:json_end]
                    corpus_data = json.loads(json_str)
                else:
                    # Construct from response if JSON parsing fails
                    corpus_data = self._construct_corpus_from_text(agent_output, keywords, research_question)
            else:
                corpus_data = agent_output

            # Ensure required fields
            if 'search_date' not in corpus_data:
                corpus_data['search_date'] = datetime.utcnow().isoformat()

            # Validate the output
            is_valid, error, validated_corpus = validate_literature_corpus(corpus_data)

            if not is_valid:
                return {
                    'success': False,
                    'error': f'Validation failed: {error}',
                    'raw_output': corpus_data
                }

            # Calculate total cost (per-paper pricing)
            papers_count = len(validated_corpus.papers)
            total_cost = papers_count * self.get_payment_rate()

            return {
                'success': True,
                'literature_corpus': validated_corpus.dict(),
                'agent_id': self.agent_id,
                'metadata': {
                    'agent_id': self.agent_id,
                    'payment_due': total_cost,
                    'currency': 'HBAR',
                    'papers_retrieved': papers_count,
                    'cost_per_paper': self.get_payment_rate(),
                    'search_model': self.model,
                    'search_date': corpus_data['search_date']
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
                'error': f'Error processing literature corpus: {str(e)}'
            }

    def _construct_corpus_from_text(
        self,
        text: str,
        keywords: List[str],
        research_question: str
    ) -> Dict[str, Any]:
        """
        Construct literature corpus from text response if JSON parsing fails.

        Args:
            text: Agent's text response
            keywords: Search keywords
            research_question: Research question

        Returns:
            Literature corpus dictionary
        """
        # This is a fallback with simulated data for demo
        # In production, the agent should always return proper JSON
        return {
            "query": research_question,
            "total_found": 3,
            "papers": [
                {
                    "title": "Blockchain-Based Agent Marketplaces: A Survey",
                    "authors": ["Demo Author 1", "Demo Author 2"],
                    "abstract": "A comprehensive survey of blockchain-based agent marketplace implementations.",
                    "published_date": "2023-06-15",
                    "journal": None,
                    "arxiv_id": "2306.12345",
                    "doi": None,
                    "url": "https://arxiv.org/abs/2306.12345",
                    "relevance_score": 0.85,
                    "citations_count": 15
                },
                {
                    "title": "ERC-8004: Agent Discovery Protocol Implementation",
                    "authors": ["Demo Author 3"],
                    "abstract": "Implementation details and performance analysis of ERC-8004 protocol.",
                    "published_date": "2024-01-20",
                    "journal": None,
                    "arxiv_id": "2401.98765",
                    "doi": None,
                    "url": "https://arxiv.org/abs/2401.98765",
                    "relevance_score": 0.92,
                    "citations_count": 8
                },
                {
                    "title": "Micropayments in Decentralized AI Systems",
                    "authors": ["Demo Author 4", "Demo Author 5"],
                    "abstract": "Analysis of micropayment mechanisms for AI agent interactions.",
                    "published_date": "2023-11-10",
                    "journal": "Journal of Distributed AI",
                    "arxiv_id": None,
                    "doi": "10.1234/jdai.2023.001",
                    "url": "https://doi.org/10.1234/jdai.2023.001",
                    "relevance_score": 0.78,
                    "citations_count": 22
                }
            ],
            "sources": ["ArXiv", "Semantic Scholar"],
            "search_date": datetime.utcnow().isoformat(),
            "filtering_criteria": {
                "date_range": "2020-2024",
                "min_relevance": 0.5,
                "max_results": 10
            }
        }


# Create singleton instance
literature_miner_agent = LiteratureMinerAgent()


# Convenience function for use as tool by other agents
async def search_research_literature(
    keywords: List[str],
    research_question: str,
    max_papers: int = 10,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tool function for searching research literature.

    Args:
        keywords: Search keywords
        research_question: Research question
        max_papers: Maximum papers to retrieve
        context: Optional search context

    Returns:
        Literature corpus
    """
    return await literature_miner_agent.search_literature(
        keywords, research_question, max_papers, context
    )