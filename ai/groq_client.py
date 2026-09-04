"""Resilient Groq LLM Client with JSON enforcement, rate limiting, and fallback handling."""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen/qwen3.8-27b"
FALLBACK_MODEL = "qwen/qwen3.6-27b"


class GroqClient:
    """Manages LLM inference requests to Groq with rate limit handling and structured JSON output."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        temperature: float = 0.1
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.max_retries = max_retries
        self.temperature = temperature
        self._client = None
        self.total_tokens_used = 0
        self.total_calls_made = 0

    def _get_client(self):
        """Initialize groq.Groq client on demand."""
        if not self.api_key:
            return None
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        """Check if Groq API key is present and configured."""
        return bool(self.api_key and self.api_key.strip())

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute chat completion enforcing JSON response."""
        client = self._get_client()
        if not client:
            return None

        model_name = model_override or self.model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(1, self.max_retries + 1):
            try:
                self.total_calls_made += 1
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                )

                if hasattr(response, "usage") and response.usage:
                    self.total_tokens_used += response.usage.total_tokens

                content = response.choices[0].message.content
                return json.loads(content)

            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"Groq API call attempt {attempt} failed: {e}")
                
                # Check for rate limit / 429
                if "rate limit" in err_str or "429" in err_str:
                    sleep_sec = 2 ** attempt
                    time.sleep(sleep_sec)
                elif attempt < self.max_retries:
                    time.sleep(1)
                else:
                    logger.error(f"Groq API call failed after {self.max_retries} attempts: {e}")
                    return None

        return None

    def complete_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Optional[str]:
        """Execute chat completion returning free-form text/markdown."""
        client = self._get_client()
        if not client:
            return None

        model_name = model_override or self.model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(1, self.max_retries + 1):
            try:
                self.total_calls_made += 1
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=self.temperature
                )

                if hasattr(response, "usage") and response.usage:
                    self.total_tokens_used += response.usage.total_tokens

                return response.choices[0].message.content

            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"Groq API text completion attempt {attempt} failed: {e}")
                
                if "rate limit" in err_str or "429" in err_str:
                    sleep_sec = 2 ** attempt
                    time.sleep(sleep_sec)
                elif attempt < self.max_retries:
                    time.sleep(1)
                else:
                    logger.error(f"Groq API call failed after {self.max_retries} attempts: {e}")
                    return None

        return None

