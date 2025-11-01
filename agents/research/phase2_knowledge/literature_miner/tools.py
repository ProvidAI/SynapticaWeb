"""Tools for Literature Miner agent."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random  # For simulation


async def search_arxiv(
    keywords: List[str],
    max_results: int = 10,
    date_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search ArXiv for relevant papers.

    Args:
        keywords: Search keywords
        max_results: Maximum number of results
        date_range: Date range filter (e.g., "2020-2024")

    Returns:
        Search results from ArXiv
    """
    # In production, this would use the ArXiv API
    # For demo, we'll simulate with relevant papers

    # Simulated papers relevant to blockchain and AI agents
    simulated_papers = [
        {
            "title": "Blockchain-Based Micropayments for Autonomous AI Agent Marketplaces",
            "authors": ["Alice Chen", "Bob Smith", "Carol Johnson"],
            "abstract": "We present a novel framework for enabling micropayments between autonomous AI agents using blockchain technology. Our approach leverages smart contracts for trustless transactions and demonstrates a 40% reduction in transaction costs compared to traditional payment systems.",
            "published_date": "2024-03-15",
            "arxiv_id": "2403.12345",
            "citations_count": 23
        },
        {
            "title": "ERC-8004: A Discovery Protocol for Decentralized Agent Networks",
            "authors": ["David Lee", "Emma Wilson"],
            "abstract": "This paper introduces ERC-8004, a standardized protocol for agent discovery in decentralized networks. We show how capability-based discovery can improve agent matching efficiency by 60% in marketplace scenarios.",
            "published_date": "2024-02-20",
            "arxiv_id": "2402.98765",
            "citations_count": 18
        },
        {
            "title": "Trust Mechanisms in Multi-Agent Blockchain Systems: A Survey",
            "authors": ["Frank Miller", "Grace Park", "Henry Zhang"],
            "abstract": "We survey existing trust mechanisms for multi-agent systems operating on blockchain networks. Our analysis covers 50+ implementations and identifies key patterns for establishing trust without centralized authorities.",
            "published_date": "2023-11-10",
            "arxiv_id": "2311.54321",
            "citations_count": 45
        },
        {
            "title": "Optimizing Gas Costs for Agent-to-Agent Transactions on Ethereum",
            "authors": ["Ian Roberts", "Julia Brown"],
            "abstract": "We propose optimization techniques for reducing gas costs in agent-to-agent transactions on Ethereum. Our methods achieve 35% gas savings through batching and state channel implementations.",
            "published_date": "2023-09-05",
            "arxiv_id": "2309.11111",
            "citations_count": 31
        },
        {
            "title": "Autonomous Economic Agents: Theory and Implementation",
            "authors": ["Kevin White", "Laura Davis"],
            "abstract": "This paper presents a theoretical framework for autonomous economic agents and demonstrates practical implementations using DLT technology. We show emergence of efficient markets in simulated environments.",
            "published_date": "2023-07-20",
            "arxiv_id": "2307.22222",
            "citations_count": 52
        }
    ]

    # Filter based on keywords
    relevant_papers = []
    for paper in simulated_papers:
        # Calculate keyword matches
        text = f"{paper['title']} {paper['abstract']}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)

        if matches > 0:
            paper['keyword_matches'] = matches
            paper['source'] = 'ArXiv'
            relevant_papers.append(paper)

    # Sort by keyword matches and take top results
    relevant_papers.sort(key=lambda x: x['keyword_matches'], reverse=True)

    return {
        "source": "ArXiv",
        "papers": relevant_papers[:max_results],
        "total_found": len(relevant_papers),
        "search_query": " OR ".join(keywords),
        "searched_at": datetime.utcnow().isoformat()
    }


async def search_semantic_scholar(
    keywords: List[str],
    max_results: int = 10,
    min_citations: Optional[int] = None
) -> Dict[str, Any]:
    """
    Search Semantic Scholar for relevant papers.

    Args:
        keywords: Search keywords
        max_results: Maximum number of results
        min_citations: Minimum citation count filter

    Returns:
        Search results from Semantic Scholar
    """
    # Simulated papers from Semantic Scholar with different focus
    simulated_papers = [
        {
            "title": "Consensus Mechanisms for Agent Coordination in Distributed Systems",
            "authors": ["Michael Anderson", "Nancy Taylor"],
            "abstract": "We analyze consensus mechanisms suitable for agent coordination in distributed systems, comparing blockchain-based approaches with traditional distributed computing solutions.",
            "published_date": "2023-12-01",
            "doi": "10.1234/consensus.2023",
            "citations_count": 67
        },
        {
            "title": "Economic Incentives in Decentralized Agent Markets",
            "authors": ["Oliver Martinez", "Patricia Garcia"],
            "abstract": "This study examines economic incentive structures in decentralized agent marketplaces, proposing game-theoretic models for optimal pricing strategies.",
            "published_date": "2024-01-10",
            "doi": "10.5678/economics.2024",
            "citations_count": 29
        },
        {
            "title": "Scalability Challenges in Blockchain-Based Agent Systems",
            "authors": ["Quinn Robinson", "Rachel Adams"],
            "abstract": "We identify and address key scalability challenges when deploying multi-agent systems on blockchain infrastructure, proposing layer-2 solutions for improved throughput.",
            "published_date": "2023-08-15",
            "doi": "10.9012/scalability.2023",
            "citations_count": 41
        }
    ]

    # Filter based on keywords and citations
    relevant_papers = []
    for paper in simulated_papers:
        text = f"{paper['title']} {paper['abstract']}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)

        if matches > 0:
            if min_citations is None or paper['citations_count'] >= min_citations:
                paper['keyword_matches'] = matches
                paper['source'] = 'Semantic Scholar'
                relevant_papers.append(paper)

    relevant_papers.sort(key=lambda x: (x['keyword_matches'], x['citations_count']), reverse=True)

    return {
        "source": "Semantic Scholar",
        "papers": relevant_papers[:max_results],
        "total_found": len(relevant_papers),
        "search_query": " AND ".join(keywords[:3]),  # Different query style
        "searched_at": datetime.utcnow().isoformat()
    }


async def calculate_relevance_score(
    paper: Dict[str, Any],
    keywords: List[str],
    research_question: str
) -> float:
    """
    Calculate relevance score for a paper.

    Args:
        paper: Paper metadata
        keywords: Research keywords
        research_question: The research question

    Returns:
        Relevance score (0-1)
    """
    score = 0.0

    # Keyword matching (40% weight)
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    keyword_matches = sum(1 for kw in keywords if kw.lower() in text)
    keyword_score = min(keyword_matches / len(keywords), 1.0) * 0.4
    score += keyword_score

    # Research question relevance (30% weight)
    rq_words = research_question.lower().split()
    rq_matches = sum(1 for word in rq_words if len(word) > 3 and word in text)
    rq_score = min(rq_matches / len(rq_words), 1.0) * 0.3
    score += rq_score

    # Recency (15% weight)
    if 'published_date' in paper:
        try:
            pub_date = datetime.fromisoformat(paper['published_date'])
            days_old = (datetime.now() - pub_date).days
            if days_old < 365:  # Less than 1 year
                recency_score = 0.15
            elif days_old < 730:  # Less than 2 years
                recency_score = 0.12
            elif days_old < 1095:  # Less than 3 years
                recency_score = 0.08
            else:
                recency_score = 0.05
            score += recency_score
        except:
            score += 0.075  # Default recency

    # Citation impact (15% weight)
    citations = paper.get('citations_count', 0)
    if citations > 50:
        citation_score = 0.15
    elif citations > 20:
        citation_score = 0.12
    elif citations > 10:
        citation_score = 0.08
    elif citations > 5:
        citation_score = 0.05
    else:
        citation_score = 0.02
    score += citation_score

    return round(min(score, 1.0), 2)


async def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate papers from multiple sources.

    Args:
        papers: List of papers from various sources

    Returns:
        Deduplicated list of papers
    """
    seen = set()
    unique_papers = []

    for paper in papers:
        # Create a signature based on title and first author
        title = paper.get('title', '').lower().strip()
        first_author = paper.get('authors', [''])[0].lower().strip() if paper.get('authors') else ''
        signature = f"{title[:50]}_{first_author}"

        if signature not in seen:
            seen.add(signature)
            unique_papers.append(paper)
        else:
            # If duplicate, merge information (keep the one with more info)
            for i, unique in enumerate(unique_papers):
                if f"{unique['title'][:50].lower()}_{unique.get('authors', [''])[0].lower()}" == signature:
                    # Merge missing fields
                    if not unique.get('doi') and paper.get('doi'):
                        unique_papers[i]['doi'] = paper['doi']
                    if not unique.get('arxiv_id') and paper.get('arxiv_id'):
                        unique_papers[i]['arxiv_id'] = paper['arxiv_id']
                    if paper.get('citations_count', 0) > unique.get('citations_count', 0):
                        unique_papers[i]['citations_count'] = paper['citations_count']
                    break

    return unique_papers


async def rank_papers_by_relevance(
    papers: List[Dict[str, Any]],
    keywords: List[str],
    research_question: str,
    top_n: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Rank papers by relevance to research question.

    Args:
        papers: List of papers to rank
        keywords: Research keywords
        research_question: The research question
        top_n: Return only top N papers

    Returns:
        Ranked list of papers
    """
    # Calculate relevance score for each paper
    for paper in papers:
        paper['relevance_score'] = await calculate_relevance_score(
            paper, keywords, research_question
        )

    # Sort by relevance score
    papers.sort(key=lambda x: x['relevance_score'], reverse=True)

    # Return top N if specified
    if top_n:
        return papers[:top_n]
    return papers


async def create_paper_url(paper: Dict[str, Any]) -> str:
    """
    Create URL for accessing the paper.

    Args:
        paper: Paper metadata

    Returns:
        URL to access the paper
    """
    if paper.get('arxiv_id'):
        return f"https://arxiv.org/abs/{paper['arxiv_id']}"
    elif paper.get('doi'):
        return f"https://doi.org/{paper['doi']}"
    elif paper.get('url'):
        return paper['url']
    else:
        # Generate search URL as fallback
        title = paper.get('title', '').replace(' ', '+')
        return f"https://scholar.google.com/scholar?q={title}"


async def extract_paper_metadata(raw_paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize paper metadata from raw source data.

    Args:
        raw_paper_data: Raw paper data from source

    Returns:
        Normalized paper metadata
    """
    # Normalize author names
    authors = raw_paper_data.get('authors', [])
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    # Ensure date format
    pub_date = raw_paper_data.get('published_date', '')
    if pub_date and not pub_date.startswith('20'):
        # Try to parse and reformat
        try:
            pub_date = datetime.fromisoformat(pub_date).strftime('%Y-%m-%d')
        except:
            pub_date = None

    # Create normalized metadata
    metadata = {
        "title": raw_paper_data.get('title', 'Unknown Title'),
        "authors": authors,
        "abstract": raw_paper_data.get('abstract', 'No abstract available'),
        "published_date": pub_date,
        "journal": raw_paper_data.get('journal'),
        "arxiv_id": raw_paper_data.get('arxiv_id'),
        "doi": raw_paper_data.get('doi'),
        "url": await create_paper_url(raw_paper_data),
        "citations_count": raw_paper_data.get('citations_count'),
        "source": raw_paper_data.get('source', 'Unknown')
    }

    return metadata