"""
Assignment Types Title Detector

Finds section headers about assignment types in syllabi.
Examples: "Homework Assignments", "Course Activities", "Assignments & Grading"

How it works:
1. Searches for assignment-related headers (homework, assignments, etc.)
2. Uses scoring system - more specific titles get higher scores
3. Skips grading policy headers (those belong to grading_procedures_title)
4. Skips schedule sections (weekly homework lists)
5. Returns highest-scoring match

Example:
    Input: "Homework Assignments (10%): Complete weekly problem sets"
    Output: "Homework Assignments:" (confidence: high)
"""
import re
from typing import Dict, Any


class AssignmentTypesDetector:
    """Finds assignment types section titles in syllabi"""

    def __init__(self):
        # Exact patterns - complete phrases that must be standalone
        # Format: (pattern, score)
        self.exact_patterns = [
            (r"(?i)^\s*grading\s+scheme\s*:?\s*$", 149),
            (r"(?i)^\s*grading\s+rubric\s*:?\s*$", 148),
            (r"(?i)^\s*assignment\s+and\s+grading\s*:?\s*$", 147),
            (r"(?i)^\s*course\s+assessments?\s*:?\s*$", 146),
            (r"(?i)^\s*types\s+of\s+assessments?\s+used\s*:?\s*$", 146),
            (r"(?i)^\s*weekly\s+homework\s+questions\s*/\s*in-?class\s+assignments?\s*:?\s*$", 146),
            (r"(?i)^\s*homework\s+quizzes\s*:\s*literature-?based\s+assignments?\s*:?\s*$", 146),
            (r"(?i)^\s*weekly\s+homework\s*\(online\)\s*:?\s*$", 146),
            (r"(?i)^\s*course\s+schedule\s+and\s+assignments?\s*:?\s*$", 145),
            (r"(?i)^\s*independent\s+study\.\s*$", 147),
            (r"(?i)^\s*lab\s+work\s*:?\s*$", 145),
            (r"(?i)^\s*programming\s+homework\s*\(40%\)\s*:?\s*$", 145),
            (r"(?i)^\s*homework\s+and\s+reading\s+for\s+class\s*:?\s*$", 145),
            (r"(?i)^\s*selected\s+readings\s*/\s*assignments?\s*:?\s*$", 145),
            (r"(?i)^\s*participation\s+assignments?\s*:?\s*$", 145),
            (r"(?i)^\s*course\s+text\s*&\s*resources\s*:?\s*$", 145),
            (r"(?i)^\s*method\s+of\s+evaluation\s*:?\s*$", 145),
            (r"(?i)^\s*weekly\s+learning\s+plans?\.?\s*$", 145),
            (r"(?i)^\s*grading\s+explanations?\(%values?\s+are\s+out\s+of\s+100%\)\s*:?\s*$", 145),
            (r"(?i)^\s*homework\s*:\s*25%\s*$", 145),
            (r"(?i)^\s*homework\s*\(25%\)\s*,\s*labs\s*\(25%\)\s*:?\s*$", 145),
            (r"(?i)^\s*labs?\s*-\s*\(assigned\s+weekly:\s*25%\s+of\s+total\s+grade\)\s*,\s*homework\s*-\s*\(assigned\s+weekly:\s*25%\s+of\s+total\s+grade\)\s*:?\s*$", 145),
            (r"(?i)^\s*quizzes\.\s*$", 145),
            (r"(?i)^\s*although\s+i\s+do\s+not\s+subtract\s+grade\s+points\s+for\s+late\s+work,\s*it\s+is\s+in\s+your\s+interest\s+to\s+keep\s+up\s+with\s+the\s+deadlines\.?\s*$", 145),
            (r"(?i)^\s*assignments?\s*&\s*grades?\s*:?\s*$", 150),
            (r"(?i)^\s*assignments?\s*&\s*grading\s*:?\s*$", 150),
            (r"(?i)^\s*textbook\s+chapter\s+quizzes\s*,?\s*discussions", 140),
            (r"(?i)^\s*methods\s+of\s+testing\s+/\s+evaluation\s*:?\s*$", 135),
            (r"(?i)^\s*course\s+requirements?\s+and\s+assessments?\s+overview\s*:?\s*$", 135),
            (r"(?i)^\s*required\s+paperwork\s+and\s+submissions?\s*\.?\s*$", 130),
            (r"(?i)^\s*assignments?\s+and\s+course\s+specific\s+policies\s*:?\s*$", 130),
            (r"(?i)^\s*assignment\s+and\s+grading\s+details?\s+lab\s*:?\s*$", 125),
            (r"(?i)^\s*summary\s+of\s+student\s+evaluation\s*:?\s*$", 120),
            (r"(?i)^\s*methods\s*,\s*grade\s+components", 115),
        ]

        # Multiword standalone - phrases on their own line (higher scores)
        # Can include weight info like "(10%)" which we'll remove later
        self.multiword_standalone = [
            (r"(?i)^\s*homework\s+assignments?\s+and\s+projects?\s*(?:\([^)]+\))?\s*:?\s*$", 112),
            (r"(?i)^\s*reading\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 110),
            (r"(?i)^\s*laboratory\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 110),
            (r"(?i)^\s*lab\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 110),
            (r"(?i)^\s*homework\s+problems\s*(?:\([^)]+\))?\s*:?\s*$", 110),
            (r"(?i)^\s*homework\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 110),
            (r"(?i)^\s*course\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 108),
            (r"(?i)^\s*class\s+assignments?\s*(?:\([^)]+\))?\s*:?\s*$", 108),
            (r"(?i)^\s*assessment\s+overview\s*:?\s*$", 106),
            (r"(?i)^\s*major\s+projects?\s*:?\s*$", 105),
            (r"(?i)^\s*course\s+activities\s*:?\s*$", 105),
            (r"(?i)^\s*assignment\s+details?\s*:?\s*$", 102),
            (r"(?i)^\s*quizzes\s+and\s+exams?\s*:?\s*$", 100),
            (r"(?i)^\s*assignments?\s+and\s+grading\s*:?\s*$", 98),
            (r"(?i)^\s*student\s+evaluation\s*:?\s*$", 90),
            (r"(?i)^\s*assessment\s*,\s*participation\s+assignments?\s*:?\s*$", 88),
        ]

        # Multiword with content - header followed by text on same line (lower scores)
        # We extract just the header part using capture group
        self.multiword_with_content = [
            (r"(?i)^\s*(assignment\s+and\s+grading)\s*:", 138),
            (r"(?i)^\s*(weekly\s+homework\s+questions\s*/\s*in-?class\s+assignments?)\s*:", 144),
            (r"(?i)^\s*(homework\s+quizzes\s*:\s*literature-?based\s+assignments?)\s*:", 144),
            (r"(?i)^\s*(weekly\s+homework\s*\(online\))\s*:", 140),
            (r"(?i)^\s*(homework\s+quizzes?)\s*:", 136),
            (r"(?i)^\s*(independent\s+study)\.\s+", 144),
            (r"(?i)^\s*(homework\s+assignments?\s+and\s+projects?)\s*(?:\([^)]+\))?\s*:", 87),
            (r"(?i)^\s*(reading\s+assignments?)\s*(?:\([^)]+\))?\s*:", 85),
            (r"(?i)^\s*(laboratory\s+assignments?)\s*(?:\([^)]+\))?\s*:", 85),
            (r"(?i)^\s*(lab\s+assignments?)\s*(?:\([^)]+\))?\s*:", 85),
            (r"(?i)^\s*(homework\s+problems)\s*(?:\([^)]+\))?\s*:", 85),
            (r"(?i)^\s*(homework\s+assignments?)\s*(?:\([^)]+\))?\s*:", 85),
            (r"(?i)^\s*(course\s+assignments?)\s*:", 83),
            (r"(?i)^\s*(class\s+assignments?)\s*:", 83),
            (r"(?i)^\s*(assessment\s+overview)\s*:", 81),
            (r"(?i)^\s*(major\s+projects?)\s*:", 80),
            (r"(?i)^\s*(course\s+activities)\s*:", 80),
            (r"(?i)^\s*(assignment\s+details?)\s*:", 77),
            (r"(?i)^\s*(quizzes\s+and\s+exams?)\s*:", 75),
            (r"(?i)^\s*(assignments?\s+and\s+grading)\s*:", 73),
            (r"(?i)^\s*(methods\s+of\s+testing\s*/\s*evaluation)\s*:", 130),
        ]

        # Singleword standalone - one word on its own line (higher scores)
        self.singleword_standalone = [
            (r"(?i)^\s*assessment\s*:?\s*$", 70),
            (r"(?i)^\s*homework\s*(?:\([^)]+\))?\s*:?\s*$", 65),
            (r"(?i)^\s*assignments?\s*:?\s*$", 60),
            (r"(?i)^\s*evaluation\s*:?\s*$", 50),
        ]

        # Singleword with content - one word followed by text (lower scores)
        self.singleword_with_content = [
            (r"(?i)^\s*(quizzes)\.\s+", 60),
            (r"(?i)^\s*(assessment)\s*:", 55),
            (r"(?i)^\s*(homework)\s*(?:\([^)]+\))?\s*:", 50),
            (r"(?i)^\s*(assignments?)\s*:", 45),
        ]

        self.broad_header_patterns = [
            r"(?i)^\s*grading\s+scheme\s*:?\s*$",
            r"(?i)^\s*grading\s+rubric\s*:?\s*$",
            r"(?i)^\s*course\s+requirements?\s*:?\s*$",
            r"(?i)^\s*course\s+assessments?\s*:?\s*$",
            r"(?i)^\s*independent\s+study\.\s*$",
            r"(?i)^\s*methods\s+of\s+testing\s*/\s*evaluation\s*:?\s*$",
            r"(?i)^\s*methods\s+of\s+testing\s+/\s+evaluation\s*:?\s*$",
        ]
        self.specific_header_patterns = [
            r"(?i)^\s*homework\s*:?\s*$",
            r"(?i)^\s*homework\s*:\s*\d",
            r"(?i)^\s*homework\s+assignments?\s*:?\s*$",
            r"(?i)^\s*homework\s+problems\s*:?\s*$",
            r"(?i)^\s*lab\s+assignments?\s*:?\s*$",
            r"(?i)^\s*laboratory\s+assignments?\s*:?\s*$",
            r"(?i)^\s*course\s+assignments?\s*:?\s*$",
            r"(?i)^\s*class\s+assignments?\s*:?\s*$",
            r"(?i)^\s*quizzes\s+and\s+exams?\s*:?\s*$",
            r"(?i)^\s*major\s+projects?\s*:?\s*$",
            r"(?i)^\s*lab\s+work\s*:?\s*$",
            r"(?i)^\s*programming\s+homework",
            r"(?i)^\s*selected\s+readings\s*/\s*assignments?",
            r"(?i)^\s*participation\s+assignments?",
            r"(?i)^\s*weekly\s+homework\s+questions\s*/\s*in-?class\s+assignments?",
            r"(?i)^\s*homework\s+quizzes\s*:\s*literature-?based\s+assignments?",
            r"(?i)^\s*homework\s+quizzes?\s*:",
        ]

        # Schedule indicators - patterns that suggest this is a weekly schedule, not a section header
        self.schedule_patterns = [
            r"(?i)week\s*#?\d+",
            r"(?i)homework\s*:\s*(reading|complete|work\s+on|finish|continue|start)",
            r"(?i)due\s+(by\s+)?next\s+week",
            r"(?i)lecture\s*[-â€“]\s*review",
        ]

        # Exclude patterns - these belong to grading_procedures_title, NOT assignment_types_title
        # Important: Skip anything about grading policies/procedures/scales
        self.exclude_patterns = [
            r"(?i)grading\s+and\s+evaluation\s+of\s+student\s+work",
            r"(?i)evaluation\s+of\s+student\s+work",
            r"(?i)grading\s+policy",
            r"(?i)grading\s+procedure",
            r"(?i)grading\s+distribution",
            r"(?i)grading\s+scale",
            r"(?i)grade\s+distribution",
            r"(?i)final\s+grade\s+(calculation|scale)",
            r"(?i)course\s+grading",
            r"(?i)rubric\s+and\s+evaluation",
        ]

    def _is_in_schedule(self, line: str, context: str) -> bool:
        """Check if line is part of a weekly schedule section"""
        for p in self.schedule_patterns:
            if re.search(p, line):
                return True
        context_lower = context.lower()
        for kw in ["week #", "homework: reading", "due by next week"]:
            if kw in context_lower:
                return True
        return False

    def _should_exclude(self, line: str) -> bool:
        """
        Check if line is a grading section header (should be excluded).
        These belong to grading_procedures_title, not assignment_types_title.
        """
        line_lower = line.lower().strip()

        for pattern in self.exclude_patterns:
            if re.search(pattern, line_lower):
                return True

        # If contains both "grading" and "evaluation", likely a grading procedures header
        if "grading" in line_lower and "evaluation" in line_lower:
            return True

        return False

    def _normalize_title(self, line: str) -> str:
        """
        Remove weight/percentage info from title.
        Example: "Homework Problems (10%)" -> "Homework Problems"
        """
        line = re.sub(r"\s*\([^)]+\)\s*", " ", line)
        line = " ".join(line.split())
        return line.strip()

    def _clean_line(self, line: str) -> str:
        """Normalize bullets and simple leading numbering before matching."""
        line = re.sub(r"^\s*[•●▪◦■□\-–—]+\s*", "", line)
        line = re.sub(r"^\s*\(?[A-Za-z0-9]+\)?[.)]\s+", "", line)
        return line.strip()

    def _is_valid_with_content(self, line: str) -> bool:
        """Check if line with content after header is valid (not schedule-like)"""
        if len(line) > 500:
            return False
        if re.search(r"(?i)(complete|work\s+on|due|week\s+\d+)", line):
            return False
        return True

    def _has_specific_header_ahead(self, lines, idx: int) -> bool:
        """Check whether a broad header is followed by a stronger, more specific title."""
        for j in range(idx + 1, min(len(lines), idx + 8)):
            candidate = self._clean_line(lines[j])
            if not candidate:
                continue
            for pattern in self.specific_header_patterns:
                if re.match(pattern, candidate):
                    return True
        return False

    def _find_split_weighted_pair(self, lines, idx: int):
        """
        Some syllabi split the expected title across two nearby lines, e.g.
        "Labs (25%)" and later "Homework (25%)".
        """
        current = self._clean_line(lines[idx])
        if not re.match(r"(?i)^(labs?|homework)\s*\(25%\)\s*$", current):
            return None

        window = [self._clean_line(lines[j]) for j in range(idx, min(len(lines), idx + 40))]
        joined = " | ".join(part for part in window if part)

        if "labs (25%)" in joined.lower() and "homework (25%)" in joined.lower():
            return "Homework (25%), Labs (25%)"

        return None

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Find assignment types section title in syllabus.

        Returns dict with 'found' (bool) and 'content' (str)
        Example: {'found': True, 'content': 'Homework Assignments:'}
        """
        if not text:
            return {"found": False, "content": ""}

        lines = text.split("\n")
        candidates = []

        for i, line in enumerate(lines):
            l = self._clean_line(line)

            if len(l) < 2 or len(l) > 500:
                continue

            # CRITICAL: Skip grading-related headers first
            if self._should_exclude(l):
                continue

            # Get surrounding context to check for schedules
            start, end = max(0, i - 5), min(len(lines), i + 6)
            context = " ".join(lines[start:end])

            if self._is_in_schedule(l, context):
                continue

            split_pair = self._find_split_weighted_pair(lines, i)
            if split_pair:
                candidates.append({"content": split_pair, "score": 151, "line": i})

            # Try patterns in order of specificity
            # 1. Exact patterns (highest scores)
            for pat, score in self.exact_patterns:
                if re.match(pat, l):
                    adjusted_score = score
                    for broad_pattern in self.broad_header_patterns:
                        if re.match(broad_pattern, l) and self._has_specific_header_ahead(lines, i):
                            adjusted_score -= 55
                            break
                    candidates.append({"content": l, "score": adjusted_score, "line": i})
                    break
            else:
                # 2. Multiword standalone
                for pat, score in self.multiword_standalone:
                    if re.match(pat, l):
                        normalized = self._normalize_title(l)
                        candidates.append({"content": normalized, "score": score, "line": i})
                        break
                else:
                    # 3. Multiword with content
                    matched = False
                    for pat, score in self.multiword_with_content:
                        match = re.match(pat, l)
                        if match and (score >= 140 or self._is_valid_with_content(l)):
                            header = match.group(1) + ":"
                            if match.group(1).lower() == "independent study":
                                header = "Independent Study."
                            candidates.append({"content": header, "score": score, "line": i})
                            matched = True
                            break

                    if not matched:
                        # 4. Singleword standalone
                        for pat, score in self.singleword_standalone:
                            if re.match(pat, l):
                                normalized = self._normalize_title(l)
                                candidates.append({"content": normalized, "score": score, "line": i})
                                matched = True
                                break

                        if not matched:
                            # 5. Singleword with content
                            for pat, score in self.singleword_with_content:
                                match = re.match(pat, l)
                                if match and self._is_valid_with_content(l):
                                    header = match.group(1) + ":"
                                    candidates.append({"content": header, "score": score, "line": i})
                                    break

        if candidates:
            # Return highest scoring candidate (earlier line breaks ties)
            best = max(candidates, key=lambda x: (x["score"], -x["line"]))
            return {"found": True, "content": best["content"]}

        return {"found": False, "content": ""}


def detect_assignment_types_title(text: str) -> str:
    """Simple wrapper - returns title or 'Missing'"""
    detector = AssignmentTypesDetector()
    result = detector.detect(text)
    return result.get("content", "") if result.get("found") else "Missing"
