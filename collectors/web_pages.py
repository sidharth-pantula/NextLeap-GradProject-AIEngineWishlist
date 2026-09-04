"""Web Page Crawler and Content Extractor for Discovered Public URLs."""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from database.db import Database, get_db

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


class WebPageExtractor:
    """Retrieves and extracts clean main content from discovered web search URLs.
    
    Adheres strictly to content classification:
    - USER_GENERATED: Forum discussions, Reddit, Quora, customer reviews, public Q&A
    - COMMERCIAL/PRODUCT_CONTEXT: Product descriptions, retail landing pages, sale banners
    - EDITORIAL: Fashion magazine articles, buyer guides, blog posts
    - OTHER: General pages
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })

    def classify_content_type(self, url: str, title: str, text: str) -> str:
        """Classify page source type to separate user voices from marketing claims."""
        url_lower = url.lower()
        title_lower = title.lower()

        # User generated discussions
        user_gen_domains = ["reddit.com", "quora.com", "forum", "community", "reviews"]
        if any(d in url_lower for d in user_gen_domains):
            return "USER_GENERATED"

        # Commercial product context
        commercial_terms = ["/p/", "/buy/", "/product/", "/dp/", "cart", "checkout", "price:"]
        if any(term in url_lower for term in commercial_terms) or "buy now" in text[:300].lower():
            return "COMMERCIAL/PRODUCT_CONTEXT"

        # Editorial / Articles / Guides
        editorial_terms = ["blog", "article", "guide", "tips", "news", "vogue", "gq", "elle", "fashion-magazine"]
        if any(term in url_lower for term in editorial_terms) or "author" in text[:400].lower():
            return "EDITORIAL"

        return "OTHER"

    def fetch_and_extract(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Fetch page content respectfully without bypassing paywalls/CAPTCHAs."""
        now = datetime.now(timezone.utc).isoformat()
        domain = urlparse(url).netloc

        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: status {response.status_code}")
                return None

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove noise scripts, styles, navigations
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            # Extract paragraphs / clean text
            paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all(["p", "article", "section"])]
            main_text = "\n\n".join([p for p in paragraphs if len(p) > 40])

            if not main_text:
                main_text = soup.get_text(separator=" ", strip=True)

            # Limit text length to avoid bloat
            cleaned_text = re.sub(r'\s+', ' ', main_text)[:5000].strip()

            if not cleaned_text or len(cleaned_text) < 50:
                return None

            classified_type = self.classify_content_type(url, title, cleaned_text)

            return {
                "url": url,
                "domain": domain,
                "title": title,
                "text": cleaned_text,
                "content_type": classified_type,
                "retrieved_at": now
            }
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    def normalize_to_raw_feedback(self, page_data: Dict[str, Any], query: str = "", category: str = "web_research") -> Dict[str, Any]:
        """Convert extracted web discussion into normalized raw_feedback."""
        now = datetime.now(timezone.utc).isoformat()
        clean_url = page_data.get("url", "")
        feedback_id = f"web_{abs(hash(clean_url))}"

        source_type_map = {
            "USER_GENERATED": "forum_discussion",
            "COMMERCIAL/PRODUCT_CONTEXT": "product_qna",
            "EDITORIAL": "shopping_discussion",
            "OTHER": "web_article"
        }
        source_type = source_type_map.get(page_data.get("content_type", "OTHER"), "forum_discussion")

        return {
            "feedback_id": feedback_id,
            "source": "web",
            "source_type": source_type,
            "source_id": clean_url,
            "date": page_data.get("retrieved_at", now),
            "text": page_data["text"],
            "title": page_data.get("title", ""),
            "url": clean_url,
            "product": None,
            "category": category,
            "rating": None,
            "engagement": 0,
            "metadata_json": {
                "domain": page_data.get("domain", ""),
                "content_type": page_data.get("content_type", "OTHER"),
                "query": query
            },
            "collection_timestamp": now
        }
