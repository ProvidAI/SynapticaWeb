"""Tavily Web Search tools for research agents."""

import os
from typing import Any, Dict, List, Optional

import httpx


async def tavily_search(
	query: str,
	max_results: int = 5,
	include_answer: bool = True,
	time_range: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Search the web using Tavily for up-to-date, relevant results.

	Args:
	    query: Search query string
	    max_results: Maximum number of results to return (1-20)
	    include_answer: Whether to ask Tavily for an aggregated answer
	    time_range: Optional time range filter (e.g., 'd', 'w', 'm', 'y')

	Returns:
	    Dict with success flag, optional answer, and results list
	"""
	api_key = os.getenv("TAVILY_API_KEY", "").strip()
	if not api_key:
		return {"success": False, "error": "TAVILY_API_KEY not set"}

	payload = {
		"api_key": api_key,
		"query": query,
		"search_depth": "advanced",
		"max_results": max(1, min(int(max_results), 20)),
		"include_answer": include_answer,
	}
	if time_range:
		payload["time_range"] = time_range

	try:
		async with httpx.AsyncClient(timeout=20.0) as client:
			resp = await client.post("https://api.tavily.com/search", json=payload)
			if resp.status_code != 200:
				return {"success": False, "error": f"Tavily HTTP {resp.status_code}: {resp.text}"}
			data = resp.json()
	except Exception as e:
		return {"success": False, "error": f"Tavily request failed: {str(e)}"}

	results = []
	for item in data.get("results", []):
		results.append(
			{
				"title": item.get("title"),
				"url": item.get("url"),
				"content": item.get("content"),
				"score": item.get("score"),
				"published": item.get("published_date"),
				"source": item.get("source"),
			}
		)

	return {
		"success": True,
		"answer": data.get("answer") if include_answer else None,
		"results": results,
		"query": query,
	}


async def tavily_research_search(
	keywords: List[str],
	research_question: str,
	max_results: int = 10,
	time_range: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Research-oriented Tavily search that structures results like literature items.

	Args:
	    keywords: List of keywords to include
	    research_question: The overarching research question
	    max_results: Max number of structured items
	    time_range: Optional time range filter for recency

	Returns:
	    Dict containing 'papers' style entries derived from web results
	"""
	query = f"{research_question} | " + " ".join(keywords[:8])
	raw = await tavily_search(query=query, max_results=max_results, include_answer=False, time_range=time_range)
	if not raw.get("success"):
		return raw

	papers = []
	for r in raw.get("results", []):
		papers.append(
			{
				"title": (r.get("title") or "Web Resource")[:200],
				"authors": ["Web Source"],
				"abstract": (r.get("content") or "")[:2000],
				"published_date": r.get("published"),
				"journal": None,
				"arxiv_id": None,
				"doi": None,
				"url": r.get("url"),
				"source": r.get("source") or "Tavily",
				"citations_count": 0,
				"relevance_score": r.get("score") or 0.5,
			}
		)

	return {
		"success": True,
		"source": "Tavily",
		"papers": papers[: max(1, min(int(max_results), 20))],
		"total_found": len(papers),
		"search_query": query,
	}


