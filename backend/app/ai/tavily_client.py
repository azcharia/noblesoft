"""
Tavily Web Search Client
Retrieval-only external web intelligence for GPT-OSS synthesis
"""
import asyncio
from importlib import import_module
import logging
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class TavilySearchClient:
    """Client wrapper for Tavily Search API."""

    def __init__(self):
        self.client: Optional[Any] = None
        if settings.is_tavily_enabled:
            tavily_module = import_module("tavily")
            self.client = tavily_module.TavilyClient(api_key=settings.tavily_api_key)

    def search(
        self,
        query: str,
        topic: str = "general",
        time_range: Optional[str] = None,
        max_results: Optional[int] = None,
        search_depth: str = "basic",
    ) -> Dict[str, Any]:
        """
        Execute Tavily search and normalize output for orchestration service.
        """
        if not settings.is_tavily_enabled or self.client is None:
            raise Exception("Tavily search is disabled by configuration")

        normalized_query = " ".join((query or "").split())[:400]
        effective_max_results = max_results or settings.TAVILY_MAX_RESULTS
        if effective_max_results < 1:
            effective_max_results = 1
        if effective_max_results > 10:
            effective_max_results = 10

        payload: Dict[str, Any] = {
            "query": normalized_query,
            "search_depth": search_depth,
            "max_results": effective_max_results,
            "topic": topic,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_usage": True,
        }
        if time_range:
            payload["time_range"] = time_range

        try:
            try:
                response = self.client.search(**payload)
            except TypeError:
                fallback_payload = {
                    "query": normalized_query,
                    "max_results": effective_max_results,
                }
                response = self.client.search(**fallback_payload)

            if not isinstance(response, dict):
                response = {}

            results = response.get("results")
            if not isinstance(results, list):
                results = []

            sources: List[Dict[str, Any]] = []
            normalized_results: List[Dict[str, Any]] = []
            for index, item in enumerate(results[:effective_max_results], start=1):
                if not isinstance(item, dict):
                    continue

                title = str(item.get("title") or "Sumber web")
                url = str(item.get("url") or "")
                content = str(item.get("content") or "").strip()
                score = item.get("score")

                compact_content = content[:600]
                if len(content) > 600:
                    compact_content = f"{compact_content.rstrip()}..."

                summary_line = compact_content or title
                if url:
                    summary_line = f"{title}: {summary_line} ({url})"
                else:
                    summary_line = f"{title}: {summary_line}"

                sources.append(
                    {
                        "type": "web",
                        "content": summary_line,
                        "metadata": {
                            "rank": index,
                            "title": title,
                            "url": url,
                            "score": score,
                            "published_date": item.get("published_date"),
                        },
                    }
                )

                normalized_results.append(
                    {
                        "title": title,
                        "url": url,
                        "content": compact_content,
                        "score": score,
                    }
                )

            request_id = str(response.get("request_id") or "")
            tool_call = {
                "id": request_id or "tavily-search",
                "type": "search",
                "name": "tavily_search",
                "arguments": {
                    "query": normalized_query,
                    "topic": topic,
                    "time_range": time_range,
                    "max_results": effective_max_results,
                    "search_depth": search_depth,
                },
            }

            return {
                "query": normalized_query,
                "answer": str(response.get("answer") or "").strip(),
                "results": normalized_results,
                "sources": sources,
                "tool_calls": [tool_call],
                "response_time": response.get("response_time"),
                "usage": response.get("usage") if isinstance(response.get("usage"), dict) else None,
                "request_id": request_id or None,
            }

        except Exception as e:
            logger.error("Tavily search error: %s", str(e))
            raise Exception(f"Failed to run Tavily search: {str(e)}")

    async def search_async(
        self,
        query: str,
        topic: str = "general",
        time_range: Optional[str] = None,
        max_results: Optional[int] = None,
        search_depth: str = "basic",
    ) -> Dict[str, Any]:
        """Async wrapper for Tavily search."""
        return await asyncio.to_thread(
            self.search,
            query,
            topic,
            time_range,
            max_results,
            search_depth,
        )
