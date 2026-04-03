"""
Authors: Erik Bailey, Team Alpha fall 2025
Contributers: Jackie
Date 12/1/2025
Email Detector
=========================================
Detects instructor email addresses in syllabus documents.
Prefers emails near typical headings; falls back to first valid email.

We basically look for unh emails (@unh.edu, @ wildcats.unh.edu)
notably, you should modify this to exclude certain emails that belong to specific departments at UNH, as they are always
on a syllabus and may get picked up accidentally.
"""

import re
import logging
from typing import Dict, Any, Optional, List

# Detection Configuration
MAX_HEADING_SCAN_LINES = 150
MAX_HEADER_CHARS = 1200
EMAIL_CONFIDENCE_SCORE = 0.95
HEADING_LOOKAHEAD_LINES = 5  # lines after a heading to scan for email

EMAIL_RX = re.compile(
    r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*@(?:wildcats\.)?(?:unh|usnh)\.edu",
    re.IGNORECASE
)

# Regex patterns that identify department/service email local parts.
_DEPT_EMAIL_RE = re.compile(
    r'^unhm\.'
    r'|^unh\.'
    r'|\.(?:office|library|advising|services|support|development)@'
    r'|^[a-z]{2,4}@',
    re.IGNORECASE
)

# Keywords that indicate surrounding text belongs to a support service, not an instructor.
# Used to skip emails that appear inside boilerplate sections (e.g. disability, food pantry).
_DEPT_CONTEXT_RE = re.compile(
    r'accessibility|disability|accommodation|student\s+success|dean\s+of\s+student'
    r'|food\s+pantry|sas\s+office|title\s+ix|mental\s+health|counseling'
    r'|academic\s+advising',
    re.IGNORECASE
)

# Heading keywords to look for (will be normalized during search)
HEADING_CLUES = [
    "email", "e-mail", "contact", "contact information",
    "preferred contact method", "instructor", "professor"
]


class EmailDetector:
    def __init__(self):
        self.field_name = 'email'
        self.logger = logging.getLogger('detector.email')

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text for consistent matching.
        Handles:
        - Lowercasing
        - Unicode punctuation (full-width colon, em-dash, etc.)
        - Extra whitespace
        """
        if not text:
            return ""

        # Lowercase first
        normalized = text.lower()

        # Replace Unicode punctuation with ASCII equivalents
        # Full-width colon, em-dash, en-dash, etc.
        normalized = normalized.replace('：', ':')  # Full-width colon
        normalized = normalized.replace('—', '-')  # Em-dash
        normalized = normalized.replace('–', '-')  # En-dash
        normalized = normalized.replace('\u2014', '-')  # Em-dash (unicode)
        normalized = normalized.replace('\u2013', '-')  # En-dash (unicode)

        # Normalize whitespace (multiple spaces -> single space)
        normalized = ' '.join(normalized.split())

        return normalized

    def _is_excluded(self, email: str) -> bool:
        """Return True if the email matches a known department/service pattern."""
        local = email.split("@")[0]
        return bool(_DEPT_EMAIL_RE.search(local + "@"))

    @staticmethod
    def _is_in_dept_context(lines: List[str], line_idx: int) -> bool:
        """Return True if the lines surrounding line_idx indicate a dept/service section."""
        start = max(0, line_idx - 3)
        end = min(len(lines), line_idx + 2)
        window = " ".join(lines[start:end])
        return bool(_DEPT_CONTEXT_RE.search(window))

    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info("Starting detection for field: email")

        if not text:
            return self._not_found()

        # 1) Try: scan all lines for a label/heading near an email.
        #    The _is_label_line guard prevents prose sentences from triggering,
        #    so scanning the full document is safe.
        lines = text.splitlines()
        candidate = self._find_near_heading(lines)
        if candidate:
            email = candidate
            method = "heading_window"
        else:
            # 2) Try: first valid email in header area (with context check)
            email = self._find_any_email(lines, end=50)
            if email:
                method = "header_any"
            else:
                # 3) Fallback: first valid email anywhere in the doc
                email = self._find_any_email(lines)
                if email:
                    method = "fallback_any"
                else:
                    return self._not_found()

        return self._found(email, method=method)

    # ---------------- helpers ----------------

    @staticmethod
    def _is_label_line(normalized_line: str) -> bool:
        """Return True if the line looks like a label/heading rather than prose.

        A label line is short (≤ 80 chars) OR the clue word starts within the
        first 30 characters — catching both standalone headings ("Instructor:")
        and table-style rows ("Email:   prof@unh.edu").  Long prose sentences
        that happen to contain the word "email" are excluded.
        """
        return len(normalized_line) <= 80

    def _find_near_heading(self, lines: List[str]) -> Optional[str]:
        """Find a non-excluded email on a label/heading line or within
        HEADING_LOOKAHEAD_LINES after it."""
        for i, raw in enumerate(lines):
            line = raw.strip()
            normalized_line = self._normalize_text(line)

            clue_match = any(self._normalize_text(clue) in normalized_line for clue in HEADING_CLUES)
            if clue_match and self._is_label_line(normalized_line):
                for j in range(i, min(i + 1 + HEADING_LOOKAHEAD_LINES, len(lines))):
                    m = EMAIL_RX.search(lines[j].strip())
                    if not m or self._is_excluded(m.group(0)):
                        continue
                    if not self._is_in_dept_context(lines, j):
                        return m.group(0)
        return None

    def _find_any_email(self, lines: List[str], end: int = None) -> Optional[str]:
        """Return first non-excluded, non-dept-context email from lines[0:end]."""
        search_lines = lines[:end] if end else lines
        for i, line in enumerate(search_lines):
            m = EMAIL_RX.search(line.strip())
            if m:
                email = m.group(0)
                if not self._is_excluded(email) and not self._is_in_dept_context(lines, i):
                    return email
        return None

    def _found(self, content: str, method: str) -> Dict[str, Any]:
        """Return found result with email as string (consistent with other detectors)."""
        self.logger.info(f"FOUND: email via {method}")
        return {
            "field_name": self.field_name,
            "found": True,
            "content": content,
            "confidence": EMAIL_CONFIDENCE_SCORE,
            "metadata": {"method": method}
        }

    def _not_found(self) -> Dict[str, Any]:
        self.logger.info("NOT_FOUND: email")
        return {
            "field_name": self.field_name,
            "found": False,
            "content": "Missing",
            "confidence": 0.0,
            "metadata": {}
        }


if __name__ == "__main__":
    # Test cases (avoiding Unicode in console output for Windows compatibility)
    test_cases = [
        ("Email: jane.doe@unh.edu", "Standard email with colon"),
        ("E-mail: john.smith@unh.edu", "E-mail variant"),
        ("Contact   :   test@unh.edu", "Extra spaces around colon"),
        ("Instructor\nEmail: prof@unh.edu", "Email on next line"),
    ]

    detector = EmailDetector()
    print("Testing Email Detector:")
    print("=" * 60)
    for test_text, description in test_cases:
        result = detector.detect(test_text)
        print(f"\nTest: {description}")
        print(f"Found: {result.get('found')}")
        print(f"Email: {result.get('content')}")
        print(f"Method: {result.get('metadata', {}).get('method')}")
