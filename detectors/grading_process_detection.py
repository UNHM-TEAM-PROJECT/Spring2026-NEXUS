"""
Authors: Jackie E, Team Alpha fall 2025
Date 12/1/2025
Grading Process Detector
Detects grading processes in syllabi: percentage breakdowns (Exam 1 - 22%),

This detector handles everything that is NOT canonical A..F letter-range mappings, so how a professor might assign points to assignments.

"""

import re
import logging
from typing import Dict, Any

# Detection Configuration Constants
MAX_HEADING_SCAN_LINES = 8
MAX_HEADING_WORDS_CAPS = 12
MAX_HEADING_WORDS_ANCHOR = 15
MAX_HEADING_WORDS_TITLE = 10
MIN_TITLE_CASE_CAPS = 2
MIN_WINDOW_SCORE = 2
MAX_SHORT_LINE_WORDS = 15
MAX_SHORT_LINE_LENGTH = 120
MAX_NEXT_LINE_WORDS = 20
MAX_UPWARD_SCAN = 7
MAX_DOWNWARD_SCAN = 9
MAX_FORWARD_SCAN = 7
PERCENT_CLUSTER_WINDOW = 3
MAX_DESCRIPTION_SKIP = 15


class GradingProcessDetector:
    """Detector for grading processes in syllabi (not canonical A..F letter-range mappings)."""

    def __init__(self):
        self.field_name = 'grading_process'
        self.logger = logging.getLogger('detector.grading_process')

        # Keywords that suggest a grading scale block
        self.percent_pattern = re.compile(r"\d+\s*%")
        self.points_pattern = re.compile(r"\b\d+\s*(points|pts)\b", re.I)
        # Letter-grade block pattern (A:, B:, C:, D:, F: in same area)
        self.letter_block_pattern = re.compile(
            r"A\s*[:\-].{0,80}B\s*[:\-].{0,80}C\s*[:\-].{0,80}D\s*[:\-].{0,80}F\s*[:\-]",
            re.I | re.S,
        )

        # small list of common labels to help anchor sections
        self.anchor_keywords = [
            'grade', 'grading', 'grades', 'grade breakdown', 'grade scale', 'grading scale', 'course grades',
            'how grades are determined', 'final grade', 'grade distribution', 'assignment', 'exam', 'quiz', 'project',
            'total = 100', 'total=100', 'total 100', 'total: 100', 'total - 100'
        ]

        # Pattern to detect grading scale lines (letter grades with ranges)
        # Examples: "A 100 % to 94 %", "A- < 94 % to 90 %", "A: 93 - 100"
        self.grading_scale_pattern = re.compile(
            r'\b[A-F][+-]?\s*[:<\|]?\s*(<\s*)?\d+\s*%?\s*(to|[-–—])\s*\d+\s*%?'
        )

    def _is_grading_scale_line(self, line: str) -> bool:
        """Return True if line appears to be a grading scale (letter grades with ranges)."""
        if not line:
            return False
        line_lower = line.lower()

        # Check for grading scale patterns like "A 100% to 94%", "A: 93-100"
        if self.grading_scale_pattern.search(line):
            return True

        # Catch "90% to 100% A" / "80-89% B" / "90% to 100% | A" style
        if re.search(r'\d+\s*%?\s*(to|[-–—])\s*\d+\s*%\s*[|]?\s*[A-F][+-]?\b', line):
            return True

        # Catch "< 60% F" / "> 90% A" / "< 60% | F" style
        if re.search(r'[<>]\s*\d+\s*%\s*[|]?\s*[A-F][+-]?\b', line):
            return True

        # Check for table headers typical of grading scales
        if 'letter' in line_lower and ('range' in line_lower or 'grade' in line_lower):
            return True

        # Check for multiple letter grades in one line (e.g., "A | 100%to94% |")
        letter_grades = re.findall(r'\b[A-F][+-]?\b', line)
        if len(letter_grades) >= 2 and '%' in line:
            return True

        # Check for table-formatted grading scales with pipes
        # Example: "A | 100 % to 94 % |" or "A- | < 94 % to 90 % |"
        if '|' in line and re.search(r'\b[A-F][+-]?\s*\|', line):
            # Has letter grade followed by pipe - likely a grading scale table
            if '%' in line or 'to' in line_lower:
                return True

        # Check for "Grade of" patterns (e.g., "Grade of F", "Grade of B")
        if 'grade of' in line_lower:
            if any(f' {letter} ' in line_lower or f' {letter},' in line_lower or f' {letter}.' in line_lower
                   for letter in ['a', 'b', 'c', 'd', 'f']):
                return True

        # Attendance-threshold lines (e.g. "90% attendance required")
        if re.search(r'\d+\s*%\s*attendance\b', line_lower):
            return True

        # Attendance credit/penalty lines (e.g. "80% for being late, 100% for full attendance")
        if re.search(r'(for\s*(being\s*)?late|for\s*full\s*attendance|for\s*absence|for\s*tardy)', line_lower):
            if '%' in line_lower:
                return True

        return False

    def _is_late_policy_line(self, line: str) -> bool:
        """Return True if line appears to be a late submission policy."""
        if not line:
            return False
        line_lower = line.lower()

        # Check for late submission indicators — keep these specific to avoid
        # false positives on assignment deadline reminder sentences
        late_indicators = [
            'days late', 'late submission', 'points subtracted', 'late penalty',
            'will not be graded', 'late work', 'late assignment', 'late deduction',
            'submitted late', 'per day late', 'after the due date and time',
            'lose 10% per day', 'lose points per day',
        ]
        if any(indicator in line_lower for indicator in late_indicators):
            return True

        # "X% per day" late deduction pattern (e.g. "you will lose 10% per day")
        if re.search(r'\d+\s*%\s*per\s*day', line_lower):
            return True

        # "Deduct X%" or "X% deduction" in a line that also mentions lateness
        if re.search(r'\bdeduct\w*\s+\d+(?:\.\d+)?\s*%', line_lower):
            return True
        if re.search(r'\d+(?:\.\d+)?\s*%\s*deduction\b', line_lower):
            return True

        # "decreases by X%" — for lines like "points decreases by 10%"
        if re.search(r'decreas\w*\s+by\s+\d+(?:\.\d+)?\s*%', line_lower):
            return True

        # "weeks late" / "days late" (broader catch)
        if re.search(r'\d+\s*(weeks?|days?)\s+late', line_lower) and re.search(r'\d+\s*%', line_lower):
            return True

        # Check for late policy table patterns
        # Example: "1 | 15%" or "7 or more | Will not be graded"
        if '|' in line and any(word in line_lower for word in ['late', 'penalty', 'deduction']):
            return True

        # Ascending penalty table: single digit | N% (e.g. "1 | 10%", "2 | 20%")
        if re.match(r'^\s*\d+\s*\|\s*\d+\s*%', line):
            return True

        return False

    def _get_heading_before(self, lines, line_index: int, max_scan: int = MAX_HEADING_SCAN_LINES) -> str:
        """Return a nearby short heading above line_index or empty string.

        Scans up to ``max_scan`` non-empty lines looking for short ALL-CAPS
        headings, anchor keywords, or short Title-Case phrases.
        """
        if not lines:
            return ''
        for i in range(line_index - 1, max(-1, line_index - max_scan - 1), -1):
            if i < 0 or i >= len(lines):
                break
            ln = lines[i].strip()
            if not ln:
                continue
            words = ln.split()
            if ln.isupper() and len(words) <= MAX_HEADING_WORDS_CAPS:
                return ln
            low = ln.lower()
            if any(k in low for k in self.anchor_keywords) and len(words) <= MAX_HEADING_WORDS_ANCHOR:
                return ln
            cap_count = sum(1 for w in words if w and w[0].isupper())
            if MIN_TITLE_CASE_CAPS <= cap_count and len(words) <= MAX_HEADING_WORDS_TITLE and '.' not in ln and ',' not in ln:
                return ln
        return ''

    def _is_heading_line(self, s: str) -> bool:
        """Return True if ``s`` looks like a short section heading.

        This is a lightweight heuristic used when extending blocks to
        include nearby headings.
        """
        if not s or not s.strip():
            return False
        s_stripped = s.strip()
        words = [w for w in s_stripped.split() if w]

        # All-caps short headings are strong indicator
        if s_stripped.isupper() and len(words) <= MAX_HEADING_WORDS_CAPS:
            return True

        low = s_stripped.lower()
        # Anchor keywords are useful, but require the line to be reasonably short
        if any(k in low for k in self.anchor_keywords) and len(words) <= MAX_HEADING_WORDS_ANCHOR:
            return True

        # Title-Case heuristic: short lines with multiple capitalized words and no sentence punctuation
        cap_count = sum(1 for w in words if w and w[0].isupper())
        if MIN_TITLE_CASE_CAPS <= cap_count and len(words) <= MAX_HEADING_WORDS_TITLE and '.' not in s_stripped and ',' not in s_stripped:
            return True

        return False

    def _has_more_grading_ahead(self, lines, start_idx: int) -> bool:
        """Return True if a grading item (% or points line) appears within
        MAX_DESCRIPTION_SKIP lines of start_idx, ignoring empty lines and
        late-policy/scale lines along the way.

        Stops immediately at a strong section boundary (all-caps heading or
        anchor keyword heading) that does not itself contain a percentage.
        """
        non_empty_seen = 0
        for j in range(start_idx, min(len(lines), start_idx + MAX_DESCRIPTION_SKIP + 1)):
            ahead = lines[j].strip()
            if not ahead:
                continue  # skip blank lines
            non_empty_seen += 1
            # Strong section heading with no % = new section, stop bridging
            if (ahead.isupper() and len(ahead.split()) <= MAX_HEADING_WORDS_CAPS
                    and not self.percent_pattern.search(ahead)
                    and not self.points_pattern.search(ahead)):
                return False
            if self._is_grading_scale_line(ahead) or self._is_late_policy_line(ahead):
                continue  # skip noise lines
            if (self.percent_pattern.search(ahead)
                    or self.points_pattern.search(ahead)
                    or re.match(
                        r"^[A-Za-z].{0,60}"
                        r"(\d+\s*%|\(\d+%\)|\d+\s*points|\d+\s*pts)",
                        ahead, re.I)):
                return True
            # Non-% non-heading description line — keep looking
        return False

    def _format_grading_output(self, raw_text: str) -> str:
        """
        Extract percentages from grading process context only.

        Rules:
        - Only extracts % values (points-only → missing)
        - Sum of raw percentages must not exceed 200 (sanity check); if it does → missing
        - Returns comma-separated list sorted descending (deduped)
        """
        if not raw_text or not isinstance(raw_text, str):
            return ""

        text = raw_text.lower()
        # Support decimal percentages (e.g. "47.5 %", "12.5%")
        pct_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%')
        matches = list(pct_pattern.finditer(text))

        if not matches:
            return ""

        # Lines that indicate a grand total, scale reference, or course modality —
        # 100% on these lines is not a category weight and should be excluded.
        total_line_pattern = re.compile(
            r'\b(total|online\s*course|asynchronous|hybrid|in.person|'
            r'out\s+of\s+100|scale|counted\s+as)\b'
        )
        # Lines that contain a grade scale context (e.g. "90% attendance required")
        scale_context_pattern = re.compile(
            r'\b(attendance\s*required|must\s*attend|letter\s*grade|earn\s*an?\s*[a-f])\b'
        )
        # Lines describing attendance credit (e.g. "80% for being late, 100% for full attendance")
        attendance_credit_pattern = re.compile(
            r'\b(for\s*(being\s*)?late|for\s*full\s*attendance|for\s*absence|for\s*tardy)\b'
        )
        # Lines with passing-threshold context (e.g. "earn a minimum of 75%", "required to pass")
        threshold_pattern = re.compile(
            r'\b(minimum\s+of\s+\d|required\s+to\s+pass|to\s+pass\s+the\s+course|'
            r'earn\s+at\s+least|pass\s+the\s+course|fail\s+to\s+earn)\b'
        )
        percentages = []
        for match in matches:
            pct_val = float(match.group(1))
            if 1 <= pct_val <= 100:
                line_start = text.rfind('\n', 0, match.start()) + 1
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)
                line_text = text[line_start:line_end]
                # Skip 100% on total/modality lines
                if pct_val == 100 and total_line_pattern.search(line_text):
                    continue
                # Skip percentages on grade-scale context lines
                if scale_context_pattern.search(line_text):
                    continue
                # Skip attendance credit lines
                if attendance_credit_pattern.search(line_text):
                    continue
                # Skip passing-threshold lines
                if threshold_pattern.search(line_text):
                    continue
                # Skip THIS specific % if immediately followed by "or better/above/higher"
                # e.g. "earn 82% or better" — only the threshold value is skipped,
                # not other weights that happen to be on the same line.
                lookahead = text[match.end():min(len(text), match.end() + 20)].lower()
                if re.match(r'\s*or\s+(better|above|higher|more)\b', lookahead):
                    continue
                percentages.append(pct_val)

        if not percentages:
            return ""

        raw_count = len(percentages)  # count before dedup

        # Dedup first — duplicated sections inflate raw sum
        percentages = sorted(set(percentages), reverse=True)

        # If 100 is present and remaining values already sum to 70–130,
        # it's a "TOTAL = 100%" line — remove it as it's not a category weight
        if 100 in percentages and len(percentages) > 1:
            rest_sum = sum(p for p in percentages if p != 100)
            if 70 <= rest_sum <= 130:
                percentages = [p for p in percentages if p != 100]

        # Require at least 2 raw occurrences — allows "Midterm: 50%, Final: 50%"
        # where both have the same value but are genuinely different assignments
        if raw_count < 2:
            return ""

        # Sanity check: sum must not exceed 200
        if sum(percentages) > 200:
            return ""

        # Format: use integer if whole number, one decimal place otherwise
        def fmt(p):
            return f"{int(p)}%" if p == int(p) else f"{p:.1f}%"
        formatted = ", ".join(fmt(pct) for pct in percentages)
        return formatted

    def detect(self, text: str) -> Dict[str, Any]:
        """Detect grading process and return a result dict with keys:
        - 'found': bool
        - 'content': str

        The detector tries (in order):
        1) explicit letter-grade block (A:, B:, C:, D:, F:),
        2) contiguous percent/points windows, and
        3) local percentage clusters near labels.
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        if not text:
            self.logger.info(f"NOT_FOUND: {self.field_name} (empty text)")
            return {'found': False, 'content': ''}

        # Normalize line endings
        lines = [ln.rstrip() for ln in text.split('\n')]
        joined = '\n'.join(lines)

        # DISABLED: Letter-grade block detection (A: ... B: ... C: ... F:)
        # This was detecting grading SCALES (A=90-100%), not grading PROCESS (Homework 30%)
        # The grading scale should be handled by final_grade_scale detector instead

        # 1) Look for contiguous percentage/points lines (window detection)
        windows = []
        current_block = []
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                if current_block:
                    if self._has_more_grading_ahead(lines, i + 1):
                        pass
                    else:
                        windows.append((block_start, current_block))
                        current_block = []
                continue

            has_percent = bool(self.percent_pattern.search(s))
            has_points = bool(self.points_pattern.search(s))
            looks_like_item = bool(re.match(r"^[A-Za-z].{0,60}(\d+\s*%|\(\d+%\)|\d+\s*points|\d+\s*pts)", s, re.I))

            # Skip lines that look like grading scale (letter grades with ranges)
            if self._is_grading_scale_line(s):
                if current_block:
                    if self._has_more_grading_ahead(lines, i + 1):
                        continue
                    windows.append((block_start, current_block))
                    current_block = []
                continue

            # Skip lines that look like late submission policy
            if self._is_late_policy_line(s):
                if current_block:
                    if self._has_more_grading_ahead(lines, i + 1):
                        continue
                    windows.append((block_start, current_block))
                    current_block = []
                continue

            if has_percent or has_points or looks_like_item:
                if not current_block:
                    block_start = i
                current_block.append(s)
            elif current_block:
                # Non-percent line while inside a block (description paragraph or
                # empty line gap between assignments). Bridge over it if more grading
                # items appear within MAX_DESCRIPTION_SKIP lines (skipping empty
                # lines and noise). This handles paragraph-format grading sections
                # where each assignment is separated by blank lines + descriptions.
                if self._has_more_grading_ahead(lines, i + 1):
                    pass  # skip this line, keep block alive
                else:
                    windows.append((block_start, current_block))
                    current_block = []
        if current_block:
            windows.append((block_start, current_block))

        # Score all valid windows and try them in descending order.
        # A window that passes the scale/late filter but whose percentages fail
        # _format_grading_output (e.g. attendance rubric) should not block a
        # lower-scoring window that IS a valid grading breakdown.
        scored_windows = []
        for idx, block in windows:
            # FILTER: Skip windows that are predominantly grading scales or late policies
            grading_scale_lines = sum(1 for ln in block if self._is_grading_scale_line(ln))
            late_policy_lines = sum(1 for ln in block if self._is_late_policy_line(ln))
            total_lines = len(block)

            if total_lines > 0 and (grading_scale_lines + late_policy_lines) / total_lines > 0.5:
                continue

            score = sum(1 for ln in block if self.percent_pattern.search(ln) or self.points_pattern.search(ln))
            # bonus if there is an anchor keyword near the block
            context = ' '.join(lines[max(0, idx-PERCENT_CLUSTER_WINDOW): min(len(lines), idx+len(block)+PERCENT_CLUSTER_WINDOW)])
            if any(k in context.lower() for k in self.anchor_keywords):
                score += 1
            if score >= MIN_WINDOW_SCORE:
                scored_windows.append((score, idx, block))

        # Try windows highest-score first; stop at first that produces valid output
        scored_windows.sort(key=lambda x: x[0], reverse=True)
        for score, idx, block in scored_windows:
            raw_content = '\n'.join(block)
            formatted = self._format_grading_output(raw_content)
            if formatted:
                self.logger.info(f"FOUND: {self.field_name} (percent/points window)")
                return {'found': True, 'content': formatted}

        if scored_windows:
            self.logger.info(f"NOT_FOUND: {self.field_name} (all windows invalid)")
            return {'found': False, 'content': ''}

        # 2) Single-line inline format fallback: one line with 3+ percentage values
        #    that sum roughly to 100 (75–130). Run AFTER window detection so the
        #    multi-line block always wins when present.
        #    e.g. "Participation 10% E-Portfolio 45% Final Drafts 25% Process Grade 20%"
        inline_pct_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%')
        for ln in lines:
            s = ln.strip()
            if not s or self._is_grading_scale_line(s) or self._is_late_policy_line(s):
                continue
            inline_vals = [float(m.group(1)) for m in inline_pct_pattern.finditer(s)
                           if 1 <= float(m.group(1)) <= 100]
            unique_vals = sorted(set(inline_vals))
            if len(unique_vals) >= 3 and 75 <= sum(unique_vals) <= 130:
                formatted = self._format_grading_output(s)
                if formatted:
                    return {'found': True, 'content': formatted}

        # 3) Fallback: group PCT lines that are close to each other (within
        #    PERCENT_CLUSTER_WINDOW lines apart), allowing empty-line gaps.
        #    This catches formats where each item is on its own line/paragraph.
        pct_idxs = [
            i for i, ln in enumerate(lines)
            if (self.percent_pattern.search(ln.strip())
                and not self._is_grading_scale_line(ln.strip())
                and not self._is_late_policy_line(ln.strip()))
        ]

        if len(pct_idxs) >= MIN_WINDOW_SCORE:
            # Group PCT lines that are within PERCENT_CLUSTER_WINDOW * 2 of each other
            gap = PERCENT_CLUSTER_WINDOW * 2
            groups = []
            current_group = [pct_idxs[0]]
            for k in range(1, len(pct_idxs)):
                if pct_idxs[k] - pct_idxs[k - 1] <= gap:
                    current_group.append(pct_idxs[k])
                else:
                    if len(current_group) >= MIN_WINDOW_SCORE:
                        groups.append(current_group)
                    current_group = [pct_idxs[k]]
            if len(current_group) >= MIN_WINDOW_SCORE:
                groups.append(current_group)

            if groups:
                # Score groups: prefer larger groups near anchor keywords
                def group_score(grp):
                    ctx_start = max(0, grp[0] - PERCENT_CLUSTER_WINDOW)
                    ctx_end = min(len(lines), grp[-1] + PERCENT_CLUSTER_WINDOW + 1)
                    ctx = ' '.join(lines[ctx_start:ctx_end]).lower()
                    anchor_bonus = 1 if any(k in ctx for k in self.anchor_keywords) else 0
                    return len(grp) + anchor_bonus

                best_group = max(groups, key=group_score)

                # Require an anchor keyword within 20 lines of the best group —
                # without it we risk picking up late-policy tables or narrative %s
                anchor_window = 20
                ctx_start = max(0, best_group[0] - anchor_window)
                ctx_end = min(len(lines), best_group[-1] + anchor_window + 1)
                ctx = ' '.join(lines[ctx_start:ctx_end]).lower()
                if not any(k in ctx for k in self.anchor_keywords):
                    self.logger.info(f"NOT_FOUND: {self.field_name} (cluster lacks anchor)")
                    return {'found': False, 'content': ''}

                block_lines = [lines[i].strip() for i in best_group]
                raw_content = '\n'.join(block_lines)
                formatted = self._format_grading_output(raw_content)
                if formatted:
                    self.logger.info(f"FOUND: {self.field_name} (percent cluster)")
                    return {'found': True, 'content': formatted}
                self.logger.info(f"NOT_FOUND: {self.field_name} (cluster invalid)")
                return {'found': False, 'content': ''}

        self.logger.info(f"NOT_FOUND: {self.field_name}")
        return {'found': False, 'content': ''}


# Backwards compatibility
def detect_grading_process(text: str) -> str:
    d = GradingProcessDetector()
    res = d.detect(text)
    return res.get('content', '') if res.get('found') else ''


if __name__ == '__main__':
    tests = [
        ("Exam 1 - 22%\nExam 2 - 22%\nExam 3 - 22%\nOnline Quizzes - 10%\nExperiments - 20%\nAttendance - 4%\nTotal = 100%", True),
        ("PROJECTS (70%) 70 Points\nProject #1 - 10 points\nProject #2 - 10 points\nQuiz & Mid-Term (20%) 20 Points\nOTHER (10%) 10 Points\nTOTAL 100%", True),
        ("A: Excellent work B: Good work C: Satisfactory D: Needs improvement F: Failing", True),
        ("This syllabus has no grading info", False),
    ]

    d = GradingProcessDetector()
    for text, expect in tests:
        r = d.detect(text)
        print('FOUND' if r['found'] else 'NO_MATCH', '\n', r['content'])
        print('-' * 40)
