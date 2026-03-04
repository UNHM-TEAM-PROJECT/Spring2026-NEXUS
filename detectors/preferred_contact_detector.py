"""
preferred contact Detector
=========================================
Detects instructor preferred contact in syllabus documents.
Prefers preferred contact near typical headings; falls back to first valid email.
"""

import re
import logging
from typing import Dict, Any, Optional, List

# Detection Configuration
PREFERRED_CONFIDENCE_SCORE = 0.95

# Email regex
PREFERRED_RX = re.compile(
    r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@(?:unh|usnh)\.edu"
)

# Heading keywords to look for
HEADING_CLUES = [
    # Preferred variations
    "preferred contact method",
    "preferred method of contact",
    "preferred way to contact",
    "preferred initial contact",
    "prefer email",
    "(email preferred)",
    "(preferred)",

    # Best way variations
    "best way to reach",
    "best way to contact",
    "best way to communicate",

    # Primary variations
    "primary contact method",
    "primary method of contact",
    "primary communication method",
    "primary method of communication",
    "(primary)",
]


class PreferredDetector:
    def __init__(self):
        self.field_name = 'preferred'
        self.logger = logging.getLogger('detector.preferred')

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        normalized = text.lower()
        normalized = normalized.replace('：', ':')
        normalized = normalized.replace('—', '-')
        normalized = normalized.replace('–', '-')
        normalized = normalized.replace('\u2014', '-')
        normalized = normalized.replace('\u2013', '-')
        normalized = ' '.join(normalized.split())
        return normalized

    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info("Starting detection for field: preferred")

        if not text:
            return self._not_found()

        # Scan ENTIRE document for heading clues (no line limit)
        lines = text.splitlines()
        candidate = self._find_near_heading(lines)

        if candidate:
            return self._found(candidate, method="heading_window")

        # If no preference phrase found, return Missing
        return self._not_found()

    def _find_near_heading(self, lines: List[str]) -> Optional[str]:
        """Find email when preference phrase is found.
        If phrase mentions 'above' or 'email', search header section for email."""

        # Words that should appear near preference phrase for validation
        contact_indicators = ["email", "e-mail", "contact", "reach", "office", "communicate"]

        for i, raw in enumerate(lines):
            line = raw.strip()
            normalized_line = self._normalize_text(line)

            # Check if any heading clue appears in the normalized line
            for clue in HEADING_CLUES:
                if self._normalize_text(clue) in normalized_line:

                    if clue in ["(primary)", "(preferred)"]:
                        # Check if (primary)/(preferred) is on the SAME LINE as phone/mobile
                        phone_indicators = ["phone", "mobile", "telephone", "cell"]

                        # Only skip if phone word and (primary)/(preferred) are on SAME line
                        if any(phone_word in normalized_line for phone_word in phone_indicators):

                            # If email/e-mail is on same line, it's OK even if phone word exists
                            if "email" in normalized_line or "e-mail" in normalized_line:
                                pass  # Email on same line → (preferred) refers to email ✓
                            else:
                                continue  # Phone on same line, no email → Skip

                    # Get context: previous line + current line + next 2 lines
                    context_lines = [normalized_line]
                    if i > 0:
                        context_lines.insert(0, self._normalize_text(lines[i-1]))
                    if i + 1 < len(lines):
                        context_lines.append(self._normalize_text(lines[i+1]))
                    if i + 2 < len(lines):
                        context_lines.append(self._normalize_text(lines[i+2]))

                    context = " ".join(context_lines)

                    # Only proceed if contact indicator appears in context
                    has_contact_indicator = any(indicator in context for indicator in contact_indicators)
                    if not has_contact_indicator:
                        continue  # Skip this match - doesn't look like contact section

                    # Strategy 1: Check nearby lines (±2 lines) for email
                    search_lines = []
                    if i >= 2:
                        search_lines.append(lines[i-2])
                    if i >= 1:
                        search_lines.append(lines[i-1])
                    search_lines.append(line)
                    if i + 1 < len(lines):
                        search_lines.append(lines[i+1])
                    if i + 2 < len(lines):
                        search_lines.append(lines[i+2])

                    for search_line in search_lines:
                        m = PREFERRED_RX.search(search_line)
                        if m:
                            return m.group(0)

                    # Strategy 2: If phrase mentions "above" or is in "Email:" section,
                    # search header area (first 150 lines) for email
                    if "above" in normalized_line or "email" in normalized_line or "e-mail" in normalized_line:
                        # Search first 150 lines for email
                        header_lines = lines[:min(150, len(lines))]
                        for header_line in header_lines:
                            m = PREFERRED_RX.search(header_line)
                            if m:
                                return m.group(0)

        return None

    def _found(self, content: str, method: str) -> Dict[str, Any]:
        self.logger.info(f"FOUND: preferred via {method}")
        return {
            "field_name": self.field_name,
            "found": True,
            "content": content,
            "confidence": PREFERRED_CONFIDENCE_SCORE,
            "metadata": {"method": method}
        }

    def _not_found(self) -> Dict[str, Any]:
        self.logger.info("NOT_FOUND: preferred")
        return {
            "field_name": self.field_name,
            "found": False,
            "content": "Missing",
            "confidence": 0.0,
            "metadata": {}
        }


if __name__ == "__main__":
    test_cases = [
        ("Email (preferred): jane.doe@unh.edu", True),
        ("Best way to reach me: john.smith@unh.edu", True),
        ("Primary contact: test@unh.edu", True),
        ("Email: prof@unh.edu", False),
        ("Contact: prof@unh.edu", False),
    ]

    detector = PreferredDetector()
    print("Testing Preferred Detector (NO FALLBACKS):")
    print("=" * 60)
    for text, should_find in test_cases:
        result = detector.detect(text)
        found = result.get('found')
        status = "✓" if found == should_find else "✗"
        print(f"{status} {text[:50]:<50} Found: {found}")