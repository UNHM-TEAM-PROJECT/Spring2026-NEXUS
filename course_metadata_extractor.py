"""Helpers for extracting course metadata from syllabus text."""

from __future__ import annotations

import re


def extract_course_title(text: str) -> tuple[str, str, str]:
    """Extract course title, code, and name from early syllabus lines."""
    if not text:
        return "", "", ""

    lines = [line.strip() for line in text.splitlines()[:20] if line.strip()]

    # Subject can be a short code (ET) or a word (English).
    code_body = r'(?P<subject>[A-Z][A-Za-z]{1,15})\s*(?:-\s*)?(?P<number>\d{3})'

    def normalize_code(raw_code: str) -> str:
        match = re.search(code_body, raw_code)
        if not match:
            return re.sub(r'\s+', '', raw_code).upper()
        return f"{match.group('subject').upper()}{match.group('number')}"

    # Pattern 1: CODE + NAME on same line.
    for line in lines:
        match = re.match(
            rf'^(?P<code>{code_body})\s*[:\-]?\s*(?P<name>.+)$',
            line,
        )
        if match:
            code = normalize_code(match.group('code'))
            name = match.group('name').strip(' -:\t')
            if name:
                return f"{code} {name}", code, name

    # Pattern 2: CODE on one line and NAME on the next non-empty line.
    code_only = re.compile(rf'^(?P<code>{code_body})\s*[:\-]?\s*$')
    heading_like = re.compile(r'^[A-Z\s]{3,}:?$')
    for idx, line in enumerate(lines):
        match = code_only.match(line)
        if not match:
            continue

        code = normalize_code(match.group('code'))
        for j in range(idx + 1, min(idx + 4, len(lines))):
            candidate = lines[j].strip(' -:\t')
            if not candidate:
                continue
            if code_only.match(candidate):
                break
            if heading_like.match(candidate):
                continue
            return f"{code} {candidate}", code, candidate

        return code, code, ""

    # Pattern 3: CODE exists somewhere; name unknown.
    for line in lines:
        match = re.search(rf'\b(?P<code>{code_body})\b', line)
        if match:
            code = normalize_code(match.group('code'))
            return code, code, ""

    return "", "", ""


def extract_semester_year(text: str, filename: str = "") -> str:
    """Extract semester/year (Fall/Spring/Summer YYYY), checking filename before text."""
    full_term_pattern = re.compile(
        r'\b(?P<term>fall|spring|summer)\s*[-_/]?\s*(?P<year>\d{2}|20\d{2})(?!\d)',
        re.IGNORECASE,
    )
    reversed_pattern = re.compile(
        r'\b(?P<year>\d{2}|20\d{2})(?!\d)\s*[-_/]?\s*(?P<term>fall|spring|summer)\b',
        re.IGNORECASE,
    )
    abbr_pattern = re.compile(
        r'\b(?P<term>fa|f|sp|spr|su|sum)\s*[-_/]?\s*(?P<year>\d{2}|20\d{2})(?!\d)',
        re.IGNORECASE,
    )
    abbr_reversed_pattern = re.compile(
        r'\b(?P<year>\d{2}|20\d{2})(?!\d)\s*[-_/]?\s*(?P<term>fa|f|sp|spr|su|sum)\b',
        re.IGNORECASE,
    )

    def _normalize_year(raw_year: str) -> str:
        year = (raw_year or "").strip()
        if len(year) == 2:
            return f"20{year}"
        return year

    def _normalize_term(raw_term: str) -> str:
        term = (raw_term or "").strip().lower()
        if term in ("fa", "f", "fall"):
            return "Fall"
        if term in ("sp", "spr", "spring"):
            return "Spring"
        if term in ("su", "sum", "summer"):
            return "Summer"
        return term.capitalize()

    def _extract_with_patterns(source: str) -> str:
        for pattern in (full_term_pattern, reversed_pattern, abbr_pattern, abbr_reversed_pattern):
            match = pattern.search(source)
            if not match:
                continue
            term = _normalize_term(match.group("term"))
            year = _normalize_year(match.group("year"))
            if term and year:
                return f"{term} {year}"
        return ""

    # 1) Search in filename first (most reliable for your dataset naming scheme).
    if filename:
        normalized_name = re.sub(r'[._]+', ' ', filename)
        from_name = _extract_with_patterns(normalized_name)
        if from_name:
            return from_name

    # 2) Fallback to text content.
    if not text:
        return ""

    early_text = "\n".join(text.splitlines()[:40])
    from_early_text = _extract_with_patterns(early_text)
    if from_early_text:
        return from_early_text
    from_text = _extract_with_patterns(text)
    if from_text:
        return from_text

    return ""
