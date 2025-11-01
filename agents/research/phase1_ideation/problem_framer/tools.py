"""Tools for Problem Framer agent."""

import json
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime


async def parse_research_query(query: str) -> Dict[str, Any]:
    """
    Parse and analyze a research query to extract key components.

    Args:
        query: Raw research query from user

    Returns:
        Parsed components of the query
    """
    # Extract key question words
    question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who']
    query_lower = query.lower()

    question_type = None
    for word in question_words:
        if word in query_lower:
            question_type = word
            break

    # Extract potential domain keywords
    domains = {
        'blockchain': ['blockchain', 'crypto', 'defi', 'web3', 'dlt', 'distributed ledger'],
        'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 'agent', 'llm'],
        'economics': ['economic', 'market', 'finance', 'payment', 'transaction', 'cost'],
        'distributed_systems': ['distributed', 'decentralized', 'p2p', 'consensus', 'network'],
        'security': ['security', 'trust', 'privacy', 'encryption', 'authentication'],
    }

    identified_domains = []
    for domain, keywords in domains.items():
        if any(kw in query_lower for kw in keywords):
            identified_domains.append(domain)

    # Extract potential metrics
    metrics_keywords = ['impact', 'effect', 'performance', 'efficiency', 'cost', 'rate', 'score', 'adoption']
    identified_metrics = [m for m in metrics_keywords if m in query_lower]

    return {
        "original_query": query,
        "question_type": question_type,
        "identified_domains": identified_domains,
        "potential_metrics": identified_metrics,
        "query_length": len(query.split()),
        "has_comparison": 'vs' in query_lower or 'versus' in query_lower or 'compared' in query_lower,
        "temporal_aspect": any(t in query_lower for t in ['future', 'trend', 'evolution', 'history']),
        "parsed_at": datetime.utcnow().isoformat()
    }


async def generate_hypothesis(
    research_question: str,
    domain: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate testable hypothesis from research question.

    Args:
        research_question: Formal research question
        domain: Research domain
        context: Additional context for hypothesis generation

    Returns:
        Generated hypothesis with null hypothesis
    """
    # Identify variables in research question
    impact_terms = ['impact', 'effect', 'influence', 'affect', 'cause']
    has_causal = any(term in research_question.lower() for term in impact_terms)

    # Identify quantitative aspects
    quant_terms = ['how much', 'how many', 'rate', 'percentage', 'cost', 'time']
    is_quantitative = any(term in research_question.lower() for term in quant_terms)

    # Generate hypothesis structure
    if has_causal and is_quantitative:
        hypothesis_type = "causal_quantitative"
        template = "X causes a Y% change in Z"
    elif has_causal:
        hypothesis_type = "causal_qualitative"
        template = "X has a significant positive/negative effect on Z"
    elif is_quantitative:
        hypothesis_type = "descriptive_quantitative"
        template = "Z exhibits Y characteristic with measurable value"
    else:
        hypothesis_type = "exploratory"
        template = "There exists a relationship between X and Z"

    return {
        "hypothesis_type": hypothesis_type,
        "template_used": template,
        "is_directional": has_causal,
        "is_quantitative": is_quantitative,
        "requires_control_group": has_causal,
        "suggested_test_type": "experimental" if has_causal else "observational",
        "minimum_sample_size": 100 if is_quantitative else 30,
        "domain": domain
    }


async def scope_research_problem(
    research_question: str,
    domains: List[str],
    constraints: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Define clear scope and boundaries for the research.

    Args:
        research_question: The formal research question
        domains: Identified research domains
        constraints: Optional constraints (time, resources, etc.)

    Returns:
        Detailed scope definition
    """
    scope = {
        "included": [],
        "excluded": [],
        "timeframe": "Not specified",
        "domain_boundaries": "",
        "geographical_scope": "Global",
        "data_requirements": [],
        "technical_requirements": []
    }

    # Blockchain-specific scope elements
    if 'blockchain' in domains:
        scope["included"].extend([
            "Decentralized systems",
            "On-chain transactions",
            "Smart contracts",
            "Consensus mechanisms"
        ])
        scope["excluded"].extend([
            "Centralized databases",
            "Traditional payment systems",
            "Off-chain computations (unless bridged)"
        ])
        scope["data_requirements"].append("Access to blockchain transaction data")
        scope["technical_requirements"].append("Web3 integration capabilities")

    # AI-specific scope elements
    if 'ai' in domains:
        scope["included"].extend([
            "Autonomous agents",
            "Machine learning models",
            "Decision-making algorithms",
            "Agent interactions"
        ])
        scope["excluded"].extend([
            "Rule-based systems",
            "Human-operated systems",
            "Non-intelligent automation"
        ])
        scope["data_requirements"].append("Agent performance metrics")
        scope["technical_requirements"].append("AI model evaluation framework")

    # Economic scope elements
    if 'economics' in domains or 'economic' in research_question.lower():
        scope["included"].extend([
            "Transaction costs",
            "Market dynamics",
            "Pricing mechanisms",
            "Economic incentives"
        ])
        scope["data_requirements"].append("Transaction volume and cost data")

    # Apply constraints if provided
    if constraints:
        if 'timeframe' in constraints:
            scope["timeframe"] = constraints['timeframe']
        if 'budget' in constraints:
            scope["resource_constraints"] = f"Budget: {constraints['budget']} HBAR"
        if 'data_sources' in constraints:
            scope["data_requirements"].extend(constraints['data_sources'])

    # Set domain boundaries
    scope["domain_boundaries"] = f"Research limited to {', '.join(domains)} domains"

    # Remove duplicates
    scope["included"] = list(set(scope["included"]))
    scope["excluded"] = list(set(scope["excluded"]))
    scope["data_requirements"] = list(set(scope["data_requirements"]))
    scope["technical_requirements"] = list(set(scope["technical_requirements"]))

    return scope


async def check_research_novelty(
    research_question: str,
    keywords: List[str]
) -> Dict[str, Any]:
    """
    Check novelty of research question using citation databases (simulated).

    Args:
        research_question: The research question to check
        keywords: Keywords for searching

    Returns:
        Novelty assessment
    """
    # In a real implementation, this would query ArXiv, Semantic Scholar, etc.
    # For now, we'll simulate with keyword matching

    # Simulate checking for similar research
    similar_work_indicators = {
        'blockchain ai agents': 0.3,  # Some work exists
        'erc-8004 protocol': 0.8,  # Relatively novel
        'x402 payments': 0.9,  # Very novel
        'decentralized marketplace': 0.4,  # Common topic
        'agent micropayments': 0.7,  # Somewhat novel
        'autonomous transactions': 0.5,  # Moderate novelty
    }

    # Calculate novelty based on keyword combinations
    keyword_pairs = []
    for i, kw1 in enumerate(keywords):
        for kw2 in keywords[i+1:]:
            pair = f"{kw1} {kw2}".lower()
            keyword_pairs.append(pair)

    novelty_scores = []
    for pair in keyword_pairs[:5]:  # Check first 5 pairs
        # Check if pair matches any indicator
        for indicator, score in similar_work_indicators.items():
            if all(word in pair or word in indicator for word in pair.split()):
                novelty_scores.append(score)
                break
        else:
            # No match found, assume moderate novelty
            novelty_scores.append(0.6)

    avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.5

    return {
        "novelty_score": round(avg_novelty, 2),
        "similar_works_found": len([s for s in novelty_scores if s < 0.5]),
        "keyword_pairs_checked": len(keyword_pairs[:5]),
        "assessment": (
            "Highly novel" if avg_novelty > 0.7
            else "Moderately novel" if avg_novelty > 0.4
            else "Limited novelty"
        ),
        "recommendation": (
            "Proceed with research" if avg_novelty > 0.4
            else "Consider refining research question for more novelty"
        ),
        "checked_at": datetime.utcnow().isoformat()
    }


async def assess_feasibility(
    research_question: str,
    scope: Dict[str, Any],
    available_resources: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Assess feasibility of the research question.

    Args:
        research_question: The research question
        scope: Research scope definition
        available_resources: Available resources (time, budget, data)

    Returns:
        Feasibility assessment
    """
    feasibility_factors = {
        "data_availability": 1.0,
        "technical_complexity": 1.0,
        "time_requirements": 1.0,
        "resource_requirements": 1.0,
        "ethical_considerations": 1.0
    }

    # Assess data availability
    data_reqs = scope.get("data_requirements", [])
    if len(data_reqs) > 5:
        feasibility_factors["data_availability"] = 0.6  # Many data requirements
    elif len(data_reqs) > 2:
        feasibility_factors["data_availability"] = 0.8

    # Assess technical complexity
    tech_reqs = scope.get("technical_requirements", [])
    if len(tech_reqs) > 3:
        feasibility_factors["technical_complexity"] = 0.7
    elif len(tech_reqs) > 1:
        feasibility_factors["technical_complexity"] = 0.85

    # Assess scope size
    included_items = len(scope.get("included", []))
    if included_items > 10:
        feasibility_factors["time_requirements"] = 0.6  # Large scope
    elif included_items > 5:
        feasibility_factors["time_requirements"] = 0.8

    # Check resources if provided
    if available_resources:
        if available_resources.get("budget", 10) < 5:
            feasibility_factors["resource_requirements"] = 0.7  # Limited budget
        if available_resources.get("time_days", 30) < 14:
            feasibility_factors["time_requirements"] *= 0.8  # Time pressure

    # Calculate overall feasibility
    overall_feasibility = sum(feasibility_factors.values()) / len(feasibility_factors)

    return {
        "feasibility_score": round(overall_feasibility, 2),
        "factors": feasibility_factors,
        "primary_challenges": [
            factor for factor, score in feasibility_factors.items() if score < 0.7
        ],
        "assessment": (
            "Highly feasible" if overall_feasibility > 0.85
            else "Feasible" if overall_feasibility > 0.7
            else "Challenging but feasible" if overall_feasibility > 0.5
            else "Potentially infeasible"
        ),
        "recommendations": [
            f"Address {factor.replace('_', ' ')}"
            for factor, score in feasibility_factors.items() if score < 0.7
        ]
    }


async def extract_keywords(
    research_question: str,
    domain: str,
    max_keywords: int = 15
) -> List[str]:
    """
    Extract relevant keywords for literature search.

    Args:
        research_question: The research question
        domain: Research domain
        max_keywords: Maximum number of keywords to extract

    Returns:
        List of keywords
    """
    # Core domain keywords
    domain_keywords = {
        'blockchain': ['blockchain', 'distributed ledger', 'DLT', 'consensus', 'smart contracts'],
        'ai': ['artificial intelligence', 'AI agents', 'machine learning', 'autonomous systems', 'LLM'],
        'economics': ['marketplace', 'transactions', 'payments', 'economic incentives', 'pricing'],
        'distributed_systems': ['decentralized', 'P2P', 'distributed computing', 'network topology']
    }

    keywords = set()

    # Add domain-specific keywords
    for key, terms in domain_keywords.items():
        if key.lower() in domain.lower():
            keywords.update(terms[:3])  # Add top 3 from each matching domain

    # Extract from research question
    # Remove common words
    stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this', 'it', 'from', 'be', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'how', 'why', 'when', 'where', 'which', 'who'}

    words = research_question.lower().replace('?', '').replace('.', '').replace(',', '').split()
    relevant_words = [w for w in words if w not in stop_words and len(w) > 3]
    keywords.update(relevant_words[:5])

    # Add specific protocol/technology keywords if mentioned
    if 'erc' in research_question.lower():
        keywords.add('ERC-8004')
    if 'x402' in research_question.lower() or 'payment' in research_question.lower():
        keywords.add('x402')
        keywords.add('micropayments')
    if 'hedera' in research_question.lower():
        keywords.add('Hedera')
        keywords.add('Hashgraph')

    # Convert to list and limit
    keyword_list = list(keywords)[:max_keywords]

    # Ensure minimum keywords
    if len(keyword_list) < 5:
        keyword_list.extend(['distributed systems', 'agent economy', 'protocols'])

    return keyword_list[:max_keywords]