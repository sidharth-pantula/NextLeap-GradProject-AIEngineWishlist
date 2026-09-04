"""Text Cleaning and Sanitization Module for VoC Raw Feedback."""
import html
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


# Known spam and bot patterns
BOT_PATTERNS = [
    r"i am a bot",
    r"auto-moderator",
    r"this is a reminder to ensure that your recent submission",
    r"read and follow the new rules in the sidebar",
    r"subscribe to (my|our) channel",
    r"follow me on instagram",
    r"download .* now using my link",
    r"use code \w+ for \d+% off",
    r"telegram channel link"
]

AFFILIATE_PATTERNS = [
    r"amzn\.to/\w+",
    r"bit\.ly/\w+",
    r"tinyurl\.com/\w+",
    r"myntr\.in/\w+",
    r"fkrt\.it/\w+"
]


class TextCleaner:
    """Sanitizes raw text, removes HTML tags, normalizes whitespace, and filters spam."""

    def __init__(self, min_char_length: int = 15):
        self.min_char_length = min_char_length

    def strip_html(self, text: str) -> str:
        """Remove HTML markup safely and unescape HTML entities."""
        if not text:
            return ""
        # Quick tag check before BeautifulSoup parse
        if "<" in text and ">" in text:
            soup = BeautifulSoup(text, "html.parser")
            text = soup.get_text(separator=" ")
        return html.unescape(text)

    def normalize_whitespace(self, text: str) -> str:
        """Remove excessive newlines, tabs, and spaces."""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def detect_spam_or_bot(self, text: str) -> Tuple[bool, List[str]]:
        """Identify automated bot messages, spam copy, or pure affiliate promotions."""
        flags = []
        text_lower = text.lower()

        for pattern in BOT_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append("bot_or_spam_pattern")
                break

        for pattern in AFFILIATE_PATTERNS:
            if re.search(pattern, text_lower):
                flags.append("affiliate_link")
                break

        # Gibberish or repeated characters check (e.g. "aaaaa", ".....")
        if re.search(r'(.)\1{6,}', text):
            flags.append("character_repetition")

        is_spam = len(flags) > 0
        return is_spam, flags

    def clean(self, raw_text: Optional[str]) -> Dict[str, Any]:
        """Perform full sanitization pipeline on raw input text."""
        if not raw_text or not isinstance(raw_text, str):
            return {
                "cleaned_text": "",
                "is_valid": False,
                "flags": ["empty_or_null"]
            }

        # Step 1: Strip HTML & unescape
        text = self.strip_html(raw_text)

        # Step 2: Normalize Unicode & whitespace
        text = self.normalize_whitespace(text)

        # Step 3: Check spam / bot markers
        is_spam, flags = self.detect_spam_or_bot(text)

        # Step 4: Validate length
        if len(text) < self.min_char_length:
            flags.append("too_short")

        is_valid = ("too_short" not in flags) and ("bot_or_spam_pattern" not in flags) and ("character_repetition" not in flags)

        return {
            "cleaned_text": text,
            "is_valid": is_valid,
            "flags": flags
        }
