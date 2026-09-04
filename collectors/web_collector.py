"""Public Web Research & Serper Search Collector with strict budget control."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from database.db import Database, get_db
from .serper_budget_manager import SerperBudgetManager

load_dotenv()

SERPER_API_ENDPOINT = "https://google.serper.dev/search"
DEFAULT_QUERIES_PATH = "config/web_search_queries.json"


class WebCollector:
    """Discovers public fashion shopping conversations using Serper Google Search API.
    
    Adheres strictly to the FREE_ONLY budget limit:
    - 50 absolute max requests
    - Initial test run: strictly 10 requests
    - Pagination OFF, Retry OFF, Background loop OFF
    - Result caching in SQLite
    """

    def __init__(
        self,
        budget_manager: Optional[SerperBudgetManager] = None,
        db: Optional[Database] = None,
        queries_path: str = DEFAULT_QUERIES_PATH
    ):
        self.db = db or get_db()
        self.budget_manager = budget_manager or SerperBudgetManager(db=self.db)
        self.queries_path = queries_path

    def search(
        self,
        query: str,
        category: str = "general_fashion",
        is_initial_test: bool = True,
        batch_request_count: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute a single Serper Google search request if allowed by budget manager."""
        clean_query = query.strip()
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Check cache
        cached = self.budget_manager.get_cached_results(clean_query)
        if cached:
            self.budget_manager.record_request(
                query=clean_query,
                category=category,
                request_number=batch_request_count,
                status="CACHED",
                result_count=len(cached),
                error=None
            )
            return cached

        # Step 2: Pre-flight budget check
        allowed, reason = self.budget_manager.can_make_request(
            batch_request_count=batch_request_count,
            is_initial_test=is_initial_test
        )
        if not allowed:
            self.budget_manager.record_request(
                query=clean_query,
                category=category,
                request_number=batch_request_count,
                status="BLOCKED",
                result_count=0,
                error=reason
            )
            raise RuntimeError(f"Serper API call blocked: {reason}")

        # Step 3: Execute single HTTP request (Pagination OFF, Retry OFF)
        api_key = self.budget_manager.api_key
        is_brave = api_key.startswith("BSA") if api_key else False

        try:
            if is_brave:
                endpoint = "https://api.search.brave.com/res/v1/web/search"
                headers = {
                    "X-Subscription-Token": api_key,
                    "Accept": "application/json"
                }
                params = {"q": clean_query, "count": 10}
                response = requests.get(endpoint, headers=headers, params=params, timeout=15)
            else:
                endpoint = "https://google.serper.dev/search"
                headers = {
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                }
                payload = {"q": clean_query}
                response = requests.post(endpoint, headers=headers, json=payload, timeout=15)

            response.raise_for_status()
            data = response.json()
        except Exception as e:
            err_msg = str(e)
            self.budget_manager.record_request(
                query=clean_query,
                category=category,
                request_number=batch_request_count + 1,
                status="FAILURE",
                result_count=0,
                error=err_msg
            )
            raise RuntimeError(f"Web search failed: {err_msg}")

        # Step 4: Parse search results (supporting both Brave and Serper structures)
        stored_results = []
        if is_brave:
            # Brave returns web results under data['web']['results'] and discussions under data['discussions']['results']
            web_results = data.get("web", {}).get("results", [])
            disc_results = data.get("discussions", {}).get("results", [])
            all_items = web_results + disc_results
            for rank_idx, item in enumerate(all_items, 1):
                url = item.get("url", item.get("link", ""))
                title = item.get("title", "")
                snippet = item.get("description", item.get("snippet", ""))
                domain = urlparse(url).netloc if url else ""
                if url and snippet:
                    stored_results.append({
                        "query": clean_query,
                        "research_category": category,
                        "search_timestamp": now,
                        "rank": rank_idx,
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "domain": domain,
                        "duplicate_count": 0,
                        "first_discovered_at": now,
                        "last_discovered_at": now,
                        "retrieval_status": "pending"
                    })
        else:
            organic_results = data.get("organic", [])
            for item in organic_results:
                url = item.get("link", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                rank = item.get("position", 0)
                domain = urlparse(url).netloc if url else ""
                stored_results.append({
                    "query": clean_query,
                    "research_category": category,
                    "search_timestamp": now,
                    "rank": rank,
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "domain": domain,
                    "duplicate_count": 0,
                    "first_discovered_at": now,
                    "last_discovered_at": now,
                    "retrieval_status": "pending"
                })

        # Step 5: Save to web_search_results table in SQLite
        if stored_results:
            sql = """
            INSERT INTO web_search_results (
                query, research_category, search_timestamp, rank, title, url,
                snippet, domain, duplicate_count, first_discovered_at,
                last_discovered_at, retrieval_status
            ) VALUES (
                :query, :research_category, :search_timestamp, :rank, :title, :url,
                :snippet, :domain, :duplicate_count, :first_discovered_at,
                :last_discovered_at, :retrieval_status
            );
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, stored_results)

        # Step 6: Log successful request
        self.budget_manager.record_request(
            query=clean_query,
            category=category,
            request_number=batch_request_count + 1,
            status="SUCCESS",
            result_count=len(stored_results),
            error=None
        )

        return stored_results

    def run_initial_test(self, limit: int = 10) -> Dict[str, Any]:
        """Run strictly 10 representative searches and output a comprehensive budget and discovery report."""
        if not os.path.exists(self.queries_path):
            raise FileNotFoundError(f"Query config not found: {self.queries_path}")

        with open(self.queries_path, "r", encoding="utf-8") as f:
            query_data = json.load(f)

        test_queries = query_data.get("initial_test_queries", [])[:limit]
        executed_queries = []
        errors = []
        requests_used_in_test = 0

        for i, q_item in enumerate(test_queries):
            query_str = q_item["query"]
            category_str = q_item["category"]

            try:
                results = self.search(
                    query=query_str,
                    category=category_str,
                    is_initial_test=True,
                    batch_request_count=requests_used_in_test
                )
                requests_used_in_test += 1
                executed_queries.append({
                    "query": query_str,
                    "category": category_str,
                    "results_count": len(results),
                    "sample_title": results[0]["title"] if results else "No results",
                    "sample_domain": results[0]["domain"] if results else ""
                })
            except Exception as e:
                errors.append({
                    "query": query_str,
                    "error": str(e)
                })
                break

        summary = self.budget_manager.get_budget_summary()
        summary["test_executed_queries"] = executed_queries
        summary["test_errors"] = errors
        summary["test_requests_used"] = requests_used_in_test
        return summary
