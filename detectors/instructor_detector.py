"""
Instructor information extraction module.

This module provides the InstructorDetector class for extracting instructor name, title, and department from syllabus text using regex and context-aware logic.

Typical usage example:
    detector = InstructorDetector()
    result = detector.detect(syllabus_text)
    print(result)
"""

from typing import Dict, Any
import re
import logging

# Detection Configuration Constants
MIN_NAME_PARTS = 2
MAX_NAME_PARTS = 4
MIN_NAME_CANDIDATE_LENGTH = 2
MAX_NAME_CANDIDATE_LENGTH = 3
MAX_DEPARTMENT_WORDS = 5
LINES_TO_SCAN = 50
PAGE_SIZE = 30
CONTEXT_OFFSET_RANGE = 2
NEXT_LINE_OFFSET = 2

class InstructorDetector:
    """
    Regex-based instructor info detector.

    Attributes:
        name_keywords (list): Keywords to identify instructor name lines.
        title_keywords (list): Keywords to identify instructor title lines.
        dept_keywords (list): Keywords to identify department lines.
        name_stopwords (set): Words to exclude from valid names.
        name_non_personal (set): Non-personal words to exclude from names.
    """
    def __init__(self):
        """
        Initializes the InstructorDetector with keyword lists and stopword sets.
        Loads common last names for confidence scoring and fallback extraction.
        """
        self.field_name = 'instructor'
        self.logger = logging.getLogger('detector.instructor')

        self.name_keywords = [
            'instructor', 'Instructor Name', 'Instructor Name:', 'Professor', 'Professor:', 'Instructor name:', 'Ms', 'Mr', 'Mrs', 'name', 'Name', 'Adjunct Instructor:', 'Contact Information', 'Dr', 'Dr.', 'Faculty', 'Faculty:', 'instructor:', 'faculty member'
        ]
        self.non_name = [
            "contact information", "office hours", "office location", "office:", "office", "email", "phone", "building", "room"
        ]
        self.skip_line_keywords = [
            "textbook", "text:", "published by", "isbn", "edition", "pearson", "mcgraw", "wiley",
            "o'reilly", "openstax", "cengage"
        ]
        self.name_prev_keywords = [
            'INSTRUCTOR INFORMATION', "instructor information"
        ]
        self.non_name_prefixes = [
            "course", "class", "program", "degree", "assignment"
        ]
        self.non_name_keywords = [
            'Course Name', 'Course Name:', 'class name', 'class name:'
        ]
        self.title_keywords = [
            # Most specific first so longer matches win over substrings
            'principal lecturer',       # FIX: added — was missing, caused Troy Fall 2025 failure
            'assistant professor',
            'associate professor',
            'senior lecturer',
            'adjunct professor',
            'adjunct instructor',
            'adjunct faculty',
            'lecturer',
            'professor',
            'prof.',
            'adjunct',
        ]
        self.dept_keywords = [
            'Department', 'Dept.', 'School of', 'Division of', 'Program', 'College of', 'Department/Program', 'Department and Program'
        ]

        # Ordered most-specific-first.
        # Bare 'Division of Science and Technology' intentionally REMOVED to prevent
        # it shadowing 'Computing Technology, Division of Science'.
        self.known_departments = [
            # ── Applied Engineering ──────────────────────────────────────────────
            'Applied Engineering and Sciences Department',
            'Applied Engineering and Sciences',
            'Applied Engineering and Science',
            'Applied Engineering & Sciences',
            'of Applied Engineering & Sciences',
            'of Applied Engineering and Sciences',
            # ── Computing Technology (must precede bare Division of Science) ─────
            'Computing Technology, Division of Science and Technology',
            'Computing Technology, Division of Science',
            # ── Science & Technology ─────────────────────────────────────────────
            'Science and Technology, UNH Manchester',
            # ── Life Sciences ────────────────────────────────────────────────────
            'Millyard Scholars Program, Dept. of Life Sciences',
            'Dept. of Life Sciences',
            'of Life Sciences, Program in',
            'of Life Sciences',
            'Department of Life Sciences',
            # ── Engineering Technology ───────────────────────────────────────────
            'Mechanical Engineering Technology',
            'Electrical Engineering Technology',
            # ── Security / Homeland ──────────────────────────────────────────────
            'Security Studies',
            'Homeland Security',
            # ── Business ─────────────────────────────────────────────────────────
            'Business & Economics',
            'Business and Public Affairs',
            'Personal Finance',
            # ── Social Sciences ──────────────────────────────────────────────────
            'Division of Social Science',
            # ── History ──────────────────────────────────────────────────────────
            'Department of History',
            'of History',
            # ── Mathematics ──────────────────────────────────────────────────────
            'Department of Mathematics and Statistics',
            'Mathematics and Statistics',
            'of Mathematics',
            # ── Other ────────────────────────────────────────────────────────────
            'Department of English',
            'Department of Biology',
        ]

        self.name_stopwords = set([
            'of', 'in', 'on', 'for', 'to', 'by', 'with', 'security', 'studies', 'department', 'college', 'school', 'division', 'program', 'phd', 'ph.d', 'professor', 'lecturer', 'assistant', 'associate', 'adjunct', 'mr', 'ms', 'mrs', 'dr'
        ])
        self.name_non_personal = set([
            'internship', 'practice', 'course', 'syllabus', 'description', 'outcomes', 'policy', 'schedule', 'grading', 'assignment', 'exam', 'final', 'midterm', 'attendance', 'office', 'email', 'phone', 'building', 'room', 'hall', 'mill', 'university', 'college', 'school', 'class', 'section', 'semester', 'year', 'hours', 'days', 'spring', 'summer', 'fall', 'winter', 'ta', 'teaching', 'staff', 'master', "master's", 'capstone', 'project', 'thesis', 'dissertation', 'portfolio',
            'applied', 'engineering', 'network', 'architecture', 'concepts', 'canvas', 'inbox', 'runestone', 'interactive', 'textbook', 'cybersecurity', 'ethics', 'data', 'mining', 'electronic', 'design', 'automation', 'discrete', 'mathematics', 'managerial', 'accounting', 'electrical', 'wildcat', 'community', 'exceptional', 'circumstances', 'first', 'edition', 'demonstrate', 'knowledge', 'hampshire', 'time', 'end', 'lecture', 'topic', 'administration', 'information',
            'tech', 'consultancy', 'workroom', 'google', 'drive', 'graduate', 'students', 'introduction', 'career', 'insight', 'develop', 'academic', 'honesty', 'noise', 'figure', 'credit', 'hour', 'networking', 'technology',
            'computing', 'the', 'file', 'system', 'reflect', 'critically', 'classroom', 'behavior', 'fourier', 'transform',
            'after-class', 'check-in', 'mid-term', 'midpoint', 'computer-integrated', 'hands-on', 'self-evaluation',
            'step-by-step', 'face-to-face', 'one-on-one', 'real-world', 'problem-solving', 'decision-making',
            'help', 'session', 'manufacturing', 'learning', 'goals', 'special', 'accommodations', 'user', 'control',
            'openstax', 'rice', 'communicate', 'professionally', 'lathi', 'radar', 'range', 'equation',
            'writing', 'intensive', 'laboratory', 'friday', 'projection', 'methods', 'ph', 'first-year'
        ])

    def clean_name_candidate(self, candidate):
        """
        Cleans up a name candidate by removing nicknames, suffixes, and normalizing format.
        """
        if not candidate:
            return candidate
        candidate = re.sub(r'\s*\([^)]+\)\s*', ' ', candidate)
        candidate = re.sub(r',?\s*(Ph\.?D\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?)\s*$', '', candidate, flags=re.IGNORECASE)
        candidate = candidate.rstrip(',').rstrip()
        candidate = re.sub(r'\s+', ' ', candidate).strip()
        return candidate

    def is_valid_name(self, candidate):
        """
        Checks if a candidate string is a valid instructor name.
        """
        parts = candidate.split()
        if not MIN_NAME_PARTS <= len(parts) <= MAX_NAME_PARTS:
            return False
        if len(set(parts)) == 1 and len(parts) > 1:
            return False
        if len(parts) > 0 and parts[0].lower() == 'ph':
            return False
        for part in parts:
            if re.match(r'^[A-Z]\.$', part):
                continue
            if re.match(r'^[A-Z]$', part):
                continue
            if re.match(r'^([A-Z]\.)+$', part):
                continue
            upper_count = sum(1 for c in part if c.isupper())
            if upper_count > 1:
                is_camelcase = bool(re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', part))
                is_hyphenated = bool(re.match(r'^[A-Z][a-z]+(-[A-Z][a-z]+)+$', part))
                if not is_camelcase and not is_hyphenated:
                    return False
            if len(part) < 2 or not re.match(r"^[A-Z][a-zA-Z\-\.]+$", part) or part.isupper() or part.lower() in self.name_stopwords | self.name_non_personal or "'" in part:
                return False
        if any(word.lower() in self.name_non_personal or word.lower() in ['course', 'syllabus', 'outline', 'schedule', 'description', "computer", "Computer", "Contact", "contact", "Using", "using", "New", "Wildcat", 'due', 'homework', 'activity'] for word in parts):
            return False
        return True

    def contains_non_name_keyword(self, text: str) -> bool:
        """
        Checks if the text contains keywords that indicate it's not a personal name.
        """
        t = text.lower()
        return any(bad.lower() in t for bad in self.non_name_keywords)

    def extract_name(self, lines):
        """
        Extracts the instructor's name from the given lines of text.
        """
        lines_for_name = lines[1:] if len(lines) > 1 else lines
        name = None
        found_keyword = False
        patterns = [
            r'([A-Z][a-zA-Z\-]+),\s+([A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+\([A-Za-z]+\)\s+[A-Z][a-zA-Z]+(?:-[A-Z][a-zA-Z]+)+)',
            r'([A-Z][a-zA-Z\-]+\s+\([A-Za-z]+\)\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+(?:-[A-Z][a-zA-Z]+)+)',
            r'([A-Z]\.[A-Z]\.?\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z]\.?\s+[A-Z]\.?\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+[A-Z]\.\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)',
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)',
        ]
        prevKeyword = ""
        for i, line in enumerate(lines_for_name):
            prevLine = lines_for_name[i-1] if i > 0 else ""
            line_clean = line.lower()
            for keyword in self.name_keywords:
                if keyword.lower() == "name":
                    if any(prefix + " name" in line_clean for prefix in self.non_name_prefixes):
                        continue
                    if prevLine.lower() in self.non_name_prefixes:
                        continue
                if keyword.lower() in line_clean:
                    found_keyword = True
                    after = re.split(rf'{keyword}[:\-]*', line, flags=re.IGNORECASE)
                    if after in self.non_name:
                        continue
                    else:
                        candidate = after[1].strip() if len(after) > 1 else ''
                    if not candidate:
                        if i + NEXT_LINE_OFFSET < len(lines):
                            candidate = lines[i + NEXT_LINE_OFFSET].strip()
                    candidate = self.clean_name_candidate(candidate)
                    for pattern in patterns:
                        pattern_match = re.search(pattern, candidate)
                        if pattern_match:
                            if ',' in pattern:
                                possible_name = f"{pattern_match.group(2)} {pattern_match.group(1)}"
                            else:
                                possible_name = self.clean_name_candidate(pattern_match.group(1))
                            if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                                name = possible_name
                                break
                    if name:
                        break
                    words = candidate.split()
                    name_candidate = []
                    for word in words:
                        if re.match(r'^[A-Z][a-zA-Z\-\.]*$', word) or re.match(r'^[A-Z]\.$', word) or re.match(r'^[A-Z]$', word):
                            name_candidate.append(word)
                            if len(name_candidate) == MAX_NAME_CANDIDATE_LENGTH:
                                break
                        else:
                            break
                    if MIN_NAME_CANDIDATE_LENGTH <= len(name_candidate) <= MAX_NAME_CANDIDATE_LENGTH:
                        possible_name = ' '.join(name_candidate)
                        if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                            name = possible_name
                            break
                prevKeyword = keyword
            if name:
                break

        if not name and len(lines) > 0:
            first_line = lines[0]
            for keyword in self.name_keywords:
                if keyword.lower() in first_line.lower():
                    after = re.split(rf'{keyword}[:\-]*', first_line, flags=re.IGNORECASE)
                    candidate = after[1].strip() if len(after) > 1 else ''
                    for pattern in patterns:
                        pattern_match = re.search(pattern, candidate)
                        if pattern_match:
                            if ',' in pattern:
                                possible_name = f"{pattern_match.group(2)} {pattern_match.group(1)}"
                            else:
                                possible_name = pattern_match.group(1)
                            if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                                name = possible_name
                                break
                    if name:
                        break
                    words = candidate.split()
                    name_candidate = []
                    for word in words:
                        if re.match(r'^[A-Z][a-zA-Z\-\.]*$', word) or re.match(r'^[A-Z]\.$', word):
                            name_candidate.append(word)
                            if len(name_candidate) == MAX_NAME_CANDIDATE_LENGTH:
                                break
                        else:
                            break
                    if MIN_NAME_CANDIDATE_LENGTH <= len(name_candidate) <= MAX_NAME_CANDIDATE_LENGTH:
                        possible_name = ' '.join(name_candidate)
                        if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                            name = possible_name
                            break

        if not name:
            early_lines = lines[:20] if len(lines) >= 20 else lines
            for i, line in enumerate(early_lines):
                line_stripped = line.strip()
                if not line_stripped or len(line_stripped) > 60:
                    continue
                if re.search(r'\b(COMP|ET|BUS|PHYS|HLS|BIOT|course|syllabus|spring|fall|summer|winter|20\d{2}|credits?)\b', line_stripped, re.IGNORECASE):
                    continue
                if re.search(r'@|http|www\.|\.edu|\.com', line_stripped, re.IGNORECASE):
                    continue
                cleaned_line = self.clean_name_candidate(line_stripped)
                for pattern in patterns:
                    pattern_match = re.match(rf'^{pattern}[,\s]*$', cleaned_line)
                    if pattern_match:
                        if ',' in pattern:
                            possible_name = f"{pattern_match.group(2)} {pattern_match.group(1)}"
                        else:
                            possible_name = self.clean_name_candidate(pattern_match.group(1))
                        if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                            name = possible_name
                            break
                if name:
                    break

        if not name and not found_keyword:
            for pattern in patterns:
                for line in lines_for_name:
                    if ',' in pattern:
                        matches = re.findall(pattern, line.strip())
                        for match in matches:
                            possible_name = f"{match[1]} {match[0]}"
                            if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                                name = possible_name
                                break
                    else:
                        for possible_name in re.findall(pattern, line.strip()):
                            cleaned_name = self.clean_name_candidate(possible_name)
                            if self.is_valid_name(cleaned_name) and not self.contains_non_name_keyword(cleaned_name):
                                name = cleaned_name
                                break
                    if name:
                        break
                if name:
                    break

        if not name:
            indices = [i for i, line in enumerate(lines_for_name) if re.search(r'@|office|room|building', line, re.IGNORECASE)]
            checked = set()
            for idx in indices:
                for offset in range(-CONTEXT_OFFSET_RANGE, CONTEXT_OFFSET_RANGE + 1):
                    j = idx + offset
                    if 0 <= j < len(lines_for_name) and j not in checked:
                        checked.add(j)
                        for pattern in patterns:
                            if ',' in pattern:
                                matches = re.findall(pattern, lines_for_name[j].strip())
                                for match in matches:
                                    possible_name = f"{match[1]} {match[0]}"
                                    if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                                        name = possible_name
                                        break
                            else:
                                for possible_name in re.findall(pattern, lines_for_name[j].strip()):
                                    if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                                        name = possible_name
                                        break
                            if name:
                                break
                    if name:
                        break
                if name:
                    break

        return name

    def extract_title(self, lines):
        """
        Extracts the instructor's title from the given lines of text.

        Scans all LINES_TO_SCAN lines but filters out false positives using:
          1. Word count > 15 → skip (sentence, not a label).
             Raised from 12 to 15 to catch slightly longer label lines like
             'Adjunct Faculty, Department of X' without re-opening body-text FPs.
          2. Body-text pattern matching → skip lines where the keyword appears
             in a non-label context (e.g. "contact the professor").
        """
        # Longest keywords first so "Principal Lecturer" beats "Lecturer", etc.
        sorted_keywords = sorted(self.title_keywords, key=len, reverse=True)

        # Patterns where the keyword is body text, NOT a title label
        body_text_patterns = [
            r'\bcontact\b.{0,40}\b(professor|instructor|lecturer|adjunct)\b',
            r'\b(email|reach|ask|see|notify|inform)\b.{0,40}\b(professor|instructor|lecturer)\b',
            r'\bthe\s+(professor|instructor|lecturer)\b',
            r'\bwith\s+(the\s+)?(professor|instructor|lecturer)\b',
            r'\ba\s+(professor|instructor|lecturer)\b',
            r'\bfrom\s+(the\s+)?(professor|instructor|lecturer)\b',
            r'\bby\s+(the\s+)?(professor|instructor|lecturer)\b',
            r'\bour\s+(professor|instructor|lecturer)\b',
            r'\byour\s+(professor|instructor|lecturer)\b',
        ]

        for line in lines:
            if '@' in line:
                continue

            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if not line_stripped:
                continue

            # FIX: raised from 12 → 15 to stop filtering out legitimate label lines
            # like "Adjunct Faculty, Dept of X" that have slightly more words
            if len(line_stripped.split()) > 15:
                continue

            # Skip lines where the keyword is clearly body text, not a label
            if any(re.search(p, line_lower) for p in body_text_patterns):
                continue

            # Check title in parentheses first: e.g. "Ohkami, Ph.D. (Lecturer)"
            parentheses_match = re.search(r'\(([^)]+)\)', line)
            if parentheses_match:
                content = parentheses_match.group(1).strip()
                for keyword in sorted_keywords:
                    if keyword.lower() == content.lower():
                        return keyword.title() if keyword.islower() else keyword

            # Plain line check
            for keyword in sorted_keywords:
                if keyword.lower() in line_lower:
                    return keyword.title() if keyword.islower() else keyword

        return None

    def extract_department(self, lines):
        """
        Extracts the instructor's department from the given lines of text.
        """
        dept_pattern_cs = re.compile(r"\b(Department|Dept\.)[\s:,-]*([A-Za-z &\-.,]+)")
        other_pattern = re.compile(
            r"\b(School of|Division of|Program in|Program\b|College of|Department and Program|Department/Program)[\s:,-]*([A-Za-z &\-.,]+)",
            re.IGNORECASE
        )

        for line in lines:
            dept_match = dept_pattern_cs.search(line)
            if dept_match:
                dept_and_prog = re.search(r'Department\s*(?:and|/)\s*Program\s*[:\-]', line, re.IGNORECASE)
                prog_label = re.search(r'\bprogram\b\s*[:\-]', line, re.IGNORECASE)
                if dept_and_prog:
                    value = line[dept_and_prog.end():].strip()
                elif prog_label:
                    value = line[prog_label.end():].strip()
                else:
                    value = dept_match.group(2).strip()
            else:
                other_match = other_pattern.search(line)
                if other_match:
                    value = other_match.group(2).strip()
                else:
                    continue

            value = re.sub(r'^[\s:,-]+', '', value)
            value = re.sub(r'^(Department|Dept\.|Program\b|School of|Division of|College of)[\s:,-]*', '', value, flags=re.IGNORECASE)
            value = re.sub(r'\s+', ' ', value).strip().strip('.,;-')

            low = value.lower()
            if not value or low in [
                'dept.', 'department', 'department and program', 'school of',
                'division of', 'program', 'college of', 'department/program'
            ]:
                continue
            if low in self.name_non_personal or low in self.name_stopwords:
                continue

            invalid_keywords = [
                'student', 'learning', 'outcomes', 'shares', 'also', 'wider',
                'community', 'the', 'and', 'with', 'for', 'to', 'from', 'at',
                'management at', 'cornell', 'university',
                'grading scale', 'grading', 'completion of', 'completion',
                'unh manchester', 'unh', 'professional studies grading',
            ]
            if any(kw in low for kw in invalid_keywords):
                continue

            if value and value[0].islower():
                if not any(known.lower() in value.lower() for known in self.known_departments):
                    continue

            words = [w for w in re.split(r'\s+', value) if w]
            if len(words) > MAX_DEPARTMENT_WORDS:
                words = words[:MAX_DEPARTMENT_WORDS]
            return ' '.join(words).strip()

        return None

    def _search_known_departments(self, text: str):
        """
        Fallback search for known department names in the top 40 lines of text.
        """
        lines = text.split('\n')[:40]
        search_text = '\n'.join(lines).lower()

        for dept in self.known_departments:
            dept_lower = dept.lower()
            if dept_lower in search_text:
                for line in lines:
                    if dept_lower in line.lower():
                        pattern = re.escape(dept).replace(r'\ ', r'\s+')
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            return match.group(0).rstrip(',.')
                return dept

        key_phrases = [
            'computing technology',
            'applied engineering',
            'life sciences',
            'science and technology',
            'homeland security',
        ]

        for phrase in key_phrases:
            if phrase in search_text:
                for line in lines:
                    if phrase in line.lower():
                        dept_pattern = re.compile(
                            r"((?:Computing Technology|Applied Engineering|Life Sciences|"
                            r"Science and Technology|Homeland Security)[^.;]*(?:Department|Division|Program)?)",
                            re.IGNORECASE
                        )
                        dept_match = dept_pattern.search(line)
                        if dept_match:
                            dept_text = dept_match.group(1).strip().rstrip(',.')
                            if 10 < len(dept_text) < 100:
                                return dept_text

        return None

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detects instructor name, title, and department from syllabus text.

        Args:
            text (str): The syllabus text to search.

        Returns:
            Dict[str, Any]: Dictionary with keys 'found', 'name', 'title', 'department'.
        """
        self.logger.info(f"Starting detection for field: {self.field_name}")

        lines = text.split('\n')[:LINES_TO_SCAN]
        name = self.extract_name(lines)
        title = self.extract_title(lines)
        department = self.extract_department(lines)

        if not department:
            department = self._search_known_departments(text)

        if not name:
            all_lines = text.split('\n')
            dr_pattern = re.compile(r"\bDr\.?\s+([A-Z][a-zA-Z\-]+)\b")
            for i in range(0, len(all_lines), PAGE_SIZE):
                page = all_lines[i:i+PAGE_SIZE]
                for page_line in page:
                    dr_match = dr_pattern.search(page_line)
                    if dr_match:
                        name = f"Dr. {dr_match.group(1)}"
                        break
                if name:
                    break

        found = bool(name and name != 'Missing' and name != 'N/A')

        if found:
            self.logger.info(f"FOUND: {self.field_name} - Name: {name}, Title: {title}, Dept: {department}")
        else:
            if not name:
                name = 'Missing'
            if not title:
                title = 'Missing'
            if not department:
                department = 'Missing'
            self.logger.info(f"NOT_FOUND: {self.field_name} - Name: {name}, Title: {title}, Dept: {department}")

        return {'found': found, 'name': name, 'title': title, 'department': department}