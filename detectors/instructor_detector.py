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
        # Lines containing these keywords should be skipped (likely textbook or other info)
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
            'assistant professor', 'associate professor', 'senior lecturer', 'lecturer', 'adjunct professor', 'adjunct instructor', 'adjunct faculty', 'professor', 'prof.', "adjunct"
        ]
        self.dept_keywords = [
            'Department', 'Dept.', 'School of', 'Division of', 'Program', 'College of', 'Department/Program', 'Department and Program'
        ]
        # Known department names for fallback detection (when no explicit label exists)
        # These are searched directly in the text if pattern matching fails
        # Only include specific, unambiguous department names (avoid generic words like "Business")
        self.known_departments = [
            # Full department names (most specific first)
            'Applied Engineering and Sciences Department',
            'Applied Engineering and Sciences',
            'Applied Engineering and Science',
            'Applied Engineering & Sciences',
            'of Applied Engineering & Sciences',
            'of Applied Engineering and Sciences',
            'Division of Science and Technology',
            'Computing Technology, Division of Science and Technology',
            'Computing Technology, Division of Science',
            'Science and Technology, UNH Manchester',
            'Millyard Scholars Program, Dept. of Life Sciences',
            'Dept. of Life Sciences',
            'of Life Sciences, Program in',
            'of Life Sciences',
            'Department of Life Sciences',
            'Mechanical Engineering Technology',
            'Electrical Engineering Technology',
            'Security Studies',
            'Homeland Security',
            'Business & Economics',
            'Division of Social Science',
            'Department of History',
            'of History',
            'Department of Mathematics and Statistics',
            'Mathematics and Statistics',
            'Department of English',
            'Department of Biology',
        ]
        self.name_stopwords = set([
            'of', 'in', 'on', 'for', 'to', 'by', 'with', 'security', 'studies', 'department', 'college', 'school', 'division', 'program', 'phd', 'ph.d', 'professor', 'lecturer', 'assistant', 'associate', 'adjunct', 'mr', 'ms', 'mrs', 'dr'
        ])
        self.name_non_personal = set([
            'internship', 'practice', 'course', 'syllabus', 'description', 'outcomes', 'policy', 'schedule', 'grading', 'assignment', 'exam', 'final', 'midterm', 'attendance', 'office', 'email', 'phone', 'building', 'room', 'hall', 'mill', 'university', 'college', 'school', 'class', 'section', 'semester', 'year', 'hours', 'days', 'spring', 'summer', 'fall', 'winter', 'ta', 'teaching', 'staff', 'master', "master's", 'capstone', 'project', 'thesis', 'dissertation', 'portfolio',
            # Common false positives from course content
            'applied', 'engineering', 'network', 'architecture', 'concepts', 'canvas', 'inbox', 'runestone', 'interactive', 'textbook', 'cybersecurity', 'ethics', 'data', 'mining', 'electronic', 'design', 'automation', 'discrete', 'mathematics', 'managerial', 'accounting', 'electrical', 'wildcat', 'community', 'exceptional', 'circumstances', 'first', 'edition', 'demonstrate', 'knowledge', 'hampshire', 'time', 'end', 'lecture', 'topic', 'administration', 'information',
            # More false positives
            'tech', 'consultancy', 'workroom', 'google', 'drive', 'graduate', 'students', 'introduction', 'career', 'insight', 'develop', 'academic', 'honesty', 'noise', 'figure', 'credit', 'hour', 'networking', 'technology',
            # Even more false positives
            'computing', 'the', 'file', 'system', 'reflect', 'critically', 'classroom', 'behavior', 'fourier', 'transform',
            # Hyphenated false positives
            'after-class', 'check-in', 'mid-term', 'midpoint', 'computer-integrated', 'hands-on', 'self-evaluation',
            'step-by-step', 'face-to-face', 'one-on-one', 'real-world', 'problem-solving', 'decision-making',
            'help', 'session', 'manufacturing', 'learning', 'goals', 'special', 'accommodations', 'user', 'control',
            'openstax', 'rice', 'communicate', 'professionally', 'lathi', 'radar', 'range', 'equation',
            # Course attributes and modality false positives
            'writing', 'intensive', 'laboratory', 'friday', 'projection', 'methods', 'ph', 'first-year'
        ])

    def clean_name_candidate(self, candidate):
        """
        Cleans up a name candidate by removing nicknames, suffixes, and normalizing format.

        Args:
            candidate (str): The raw candidate name string.

        Returns:
            str: The cleaned name string.
        """
        if not candidate:
            return candidate

        # Remove nicknames in parentheses: "Mateusz (Matt) Pacha" -> "Mateusz Pacha"
        candidate = re.sub(r'\s*\([^)]+\)\s*', ' ', candidate)

        # Remove Ph.D., PhD, Ph.D and similar suffixes
        candidate = re.sub(r',?\s*(Ph\.?D\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?)\s*$', '', candidate, flags=re.IGNORECASE)

        # Remove trailing commas (e.g., "Takahide Ohkami," -> "Takahide Ohkami")
        candidate = candidate.rstrip(',').rstrip()

        # Normalize multiple spaces
        candidate = re.sub(r'\s+', ' ', candidate).strip()

        return candidate

    def is_valid_name(self, candidate):
        """
        Checks if a candidate string is a valid instructor name.

        Args:
            candidate (str): The candidate name string.

        Returns:
            bool: True if valid, False otherwise.
        """
        parts = candidate.split()
        if not MIN_NAME_PARTS <= len(parts) <= MAX_NAME_PARTS:
            return False

        # Reject if all parts are identical (e.g., "Due Due", "Test Test")
        if len(set(parts)) == 1 and len(parts) > 1:
            return False

        # Reject if first part is "Ph" (likely from "Ph.D." or "PhD")
        if len(parts) > 0 and parts[0].lower() == 'ph':
            return False

        for part in parts:
            # Allow middle initial with period (e.g., W. or A.)
            if re.match(r'^[A-Z]\.$', part):
                continue
            # Allow single capital letter as initial (e.g., R J Greene -> R, J are valid)
            if re.match(r'^[A-Z]$', part):
                continue
            # Allow initials with periods like K.M. or J.R.
            if re.match(r'^([A-Z]\.)+$', part):
                continue
            # Allow CamelCase names (e.g., TakaHide, McDonald, DeVito) and hyphenated names (Pacha-Sucharzewski)
            # Check if multiple capitals exist
            upper_count = sum(1 for c in part if c.isupper())
            if upper_count > 1:
                # Allow CamelCase personal names (TakaHide, McDonald, etc.)
                # Pattern: Starts with capital, has lowercase, then capital
                is_camelcase = bool(re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', part))
                # Allow hyphenated names like Pacha-Sucharzewski (each part starts with capital)
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

        This method filters out false positives like "Course Name" or "Class Name"
        that might otherwise be mistakenly identified as instructor names.

        Args:
            text (str): The text string to check for non-name keywords.

        Returns:
            bool: True if the text contains a non-name keyword, False otherwise.
        """
        t = text.lower()
        return any(bad.lower() in t for bad in self.non_name_keywords)

    def extract_name(self, lines):
        """
        Extracts the instructor's name from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted name, or None if not found.
        """
        lines_for_name = lines[1:] if len(lines) > 1 else lines
        name = None
        found_keyword = False
        patterns = [
            # Last, First format (check this FIRST to handle comma-separated names)
            r'([A-Z][a-zA-Z\-]+),\s+([A-Z][a-zA-Z\-]+)',  # Added: Last, First
            # Name with nickname in parentheses and hyphenated last name: Mateusz (Matt) Pacha-Sucharzewski
            r'([A-Z][a-zA-Z\-]+\s+\([A-Za-z]+\)\s+[A-Z][a-zA-Z]+(?:-[A-Z][a-zA-Z]+)+)',
            # Name with nickname in parentheses: Mateusz (Matt) Smith
            r'([A-Z][a-zA-Z\-]+\s+\([A-Za-z]+\)\s+[A-Z][a-zA-Z\-]+)',
            # First Last-Last (hyphenated last name without nickname)
            r'([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+(?:-[A-Z][a-zA-Z]+)+)',
            # Initials with periods: K.M. Kilcrease or J.R. Smith
            r'([A-Z]\.[A-Z]\.?\s+[A-Z][a-zA-Z\-]+)',
            # Initials with spaces: K. M. Kilcrease or R J Greene
            r'([A-Z]\.?\s+[A-Z]\.?\s+[A-Z][a-zA-Z\-]+)',
            # First M. Last (with middle initial)
            r'([A-Z][a-zA-Z\-]+\s+[A-Z]\.\s+[A-Z][a-zA-Z\-]+)',
            # First Middle Last (three names)
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)',
            # First Last (simple two-word name)
            r'([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+)',
        ]
        # Search all but the first line
        prevKeyword = ""
        for i, line in enumerate(lines_for_name):
            prevLine = lines_for_name[i-1] if i > 0 else ""
            line_clean = line.lower()
            for keyword in self.name_keywords:
                if keyword.lower() == "name":
                    if any(prefix + " name" in line_clean for prefix in self.non_name_prefixes):
                        continue  # skip this keyword match
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
                    # Clean the candidate (remove nicknames, Ph.D., etc.)
                    candidate = self.clean_name_candidate(candidate)
                    for pattern in patterns:
                        pattern_match = re.search(pattern, candidate)
                        if pattern_match:
                            # Handle "Last, First" format specially - reorder to "First Last"
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
                        # Also allow single capital letter (for initials like R J Greene)
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

        # If no name found, check the first line
        if not name and len(lines) > 0:
            first_line = lines[0]
            for keyword in self.name_keywords:
                if keyword.lower() in first_line.lower():
                    after = re.split(rf'{keyword}[:\-]*', first_line, flags=re.IGNORECASE)
                    candidate = after[1].strip() if len(after) > 1 else ''
                    for pattern in patterns:
                        pattern_match = re.search(pattern, candidate)
                        if pattern_match:
                            # Handle "Last, First" format specially - reorder to "First Last"
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

        # 2. Check for standalone names on early lines (first 20 lines)
        # These are lines that contain ONLY a name-like pattern (no other text)
        # Common in syllabi where instructor name appears alone after course title
        if not name:
            early_lines = lines[:20] if len(lines) >= 20 else lines
            for i, line in enumerate(early_lines):
                line_stripped = line.strip()
                # Skip empty lines or lines that are too long (likely sentences)
                if not line_stripped or len(line_stripped) > 60:
                    continue
                # Skip lines that look like course titles, dates, or other non-name content
                if re.search(r'\b(COMP|ET|BUS|PHYS|HLS|BIOT|course|syllabus|spring|fall|summer|winter|20\d{2}|credits?)\b', line_stripped, re.IGNORECASE):
                    continue
                # Skip lines with email, phone, or URL patterns (but allow simple phone patterns that might be near names)
                if re.search(r'@|http|www\.|\.edu|\.com', line_stripped, re.IGNORECASE):
                    continue
                # Clean the line
                cleaned_line = self.clean_name_candidate(line_stripped)
                # Try to match name patterns
                for pattern in patterns:
                    pattern_match = re.match(rf'^{pattern}[,\s]*$', cleaned_line)
                    if pattern_match:
                        # Handle "Last, First" format specially - reorder to "First Last"
                        if ',' in pattern:
                            possible_name = f"{pattern_match.group(2)} {pattern_match.group(1)}"
                        else:
                            possible_name = self.clean_name_candidate(pattern_match.group(1))
                        if self.is_valid_name(possible_name) and not self.contains_non_name_keyword(possible_name):
                            name = possible_name
                            break
                if name:
                    break

        # 3. Only if NO instructor/name keyword was found at all, fall back to pattern search
        if not name and not found_keyword:
            for pattern in patterns:
                for line in lines_for_name:
                    # Handle "Last, First" pattern specially (it has 2 groups)
                    if ',' in pattern:
                        matches = re.findall(pattern, line.strip())
                        for match in matches:
                            # match is a tuple (Last, First) - reorder
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
                            # Handle "Last, First" pattern specially (it has 2 groups)
                            if ',' in pattern:
                                matches = re.findall(pattern, lines_for_name[j].strip())
                                for match in matches:
                                    # match is a tuple (Last, First) - reorder
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

        # return name if found, else None
        return name

    def extract_title(self, lines):
        """
        Extracts the instructor's title from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted title, or None if not found.
        """
        # Sort title keywords by length (longest first) to match more specific titles first
        # This ensures "Associate Professor" is matched before "Professor"
        sorted_keywords = sorted(self.title_keywords, key=len, reverse=True)

        for line in lines:
            # Skip lines with email addresses to avoid false positives like "meanoleprofessor@comcast.net"
            if '@' in line:
                continue

            line_lower = line.lower()

            # First, check if title is in parentheses like "Takahide Ohkami, Ph.D. (Lecturer)"
            import re
            parentheses_match = re.search(r'\(([^)]+)\)', line)
            if parentheses_match:
                content = parentheses_match.group(1).strip()
                # Check if the content in parentheses is a title keyword
                for keyword in sorted_keywords:
                    if keyword.lower() == content.lower():
                        # Return properly capitalized version
                        return keyword.title() if keyword.islower() else keyword

            # Then check for title keywords in the line
            for keyword in sorted_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in line_lower:
                    # Return properly capitalized version
                    return keyword.title() if keyword.islower() else keyword

        return None


    def extract_department(self, lines):
        """
        Extracts the instructor's department from the given lines of text.

        Args:
            lines (list): The lines of text to search.

        Returns:
            str: The extracted department, or None if not found.
        """
        # First, require a capital D when matching 'Department' or 'Dept.' to avoid
        # lower-case false positives (e.g., 'department' inside sentences).
        dept_pattern_cs = re.compile(r"\b(Department|Dept\.)[\s:,-]*([A-Za-z &\-.,]+)")
        # Fallback patterns (case-insensitive) for School/Division/Program/College
        other_pattern = re.compile(r"\b(School of|Division of|Program in|Program\b|College of|Department and Program|Department/Program)[\s:,-]*([A-Za-z &\-.,]+)", re.IGNORECASE)

        for line in lines:
            # try case-sensitive Department/Dept. first
            dept_match = dept_pattern_cs.search(line)
            if dept_match:
                    # Only treat 'program' as a separate label when it's actually used as a label
                    # (e.g., 'Program: X' or 'Department and Program: X'). If 'program' appears
                    # as a trailing word in the department name (e.g., 'Bio/Biotech program'),
                    # leave it in the captured value.
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

            # cleanup leading punctuation/labels
            value = re.sub(r'^[\s:,-]+', '', value)
            value = re.sub(r'^(Department|Dept\.|Program\b|School of|Division of|College of)[\s:,-]*', '', value, flags=re.IGNORECASE)

            # normalize whitespace and strip trailing punctuation
            value = re.sub(r'\s+', ' ', value).strip().strip('.,;-')

            # Skip very generic or empty values
            low = value.lower()
            if not value or low in ['dept.', 'department', 'department and program', 'school of', 'division of', 'program', 'college of', 'department/program']:
                continue
            if low in self.name_non_personal or low in self.name_stopwords:
                continue

            # Reject obviously invalid department names (false positives)
            invalid_keywords = ['student', 'learning', 'outcomes', 'shares', 'also', 'wider',
                               'community', 'the', 'and', 'with', 'for', 'to', 'from', 'at',
                               'management at', 'cornell', 'university']
            # Check if department contains invalid keywords that don't belong in department names
            if any(keyword in low for keyword in invalid_keywords):
                continue

            # Reject if it starts with lowercase (likely extracted from middle of sentence)
            # UNLESS it's a very specific department name
            if value and value[0].islower():
                # Allow if it's a known department pattern despite lowercase start
                if not any(known.lower() in value.lower() for known in self.known_departments):
                    continue

            # limit returned department to up to MAX_DEPARTMENT_WORDS words
            words = [word for word in re.split(r'\s+', value) if word]
            if len(words) > MAX_DEPARTMENT_WORDS:
                words = words[:MAX_DEPARTMENT_WORDS]
            return ' '.join(words).strip()

        return None

    def _search_known_departments(self, text: str):
        """
        Fallback search for known department names in text.
        Only searches near instructor info (top 40 lines) to avoid false positives
        from program descriptions or footers.

        Args:
            text (str): The full syllabus text.

        Returns:
            str: The department name if found, or None.
        """
        # Search first 40 lines (expanded range for instructor info)
        # This avoids matching department names in course descriptions or footers
        lines = text.split('\n')[:40]
        search_text = '\n'.join(lines).lower()

        # Search for known departments (list is ordered from most specific to least)
        for dept in self.known_departments:
            dept_lower = dept.lower()
            if dept_lower in search_text:
                # Return the matched department, but check if there's additional context
                # Try to find the actual occurrence with proper capitalization
                for line in lines:
                    if dept_lower in line.lower():
                        # Extract the actual text with original capitalization
                        pattern = re.escape(dept).replace(r'\ ', r'\s+')
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            matched_text = match.group(0)
                            # Clean up trailing punctuation
                            matched_text = matched_text.rstrip(',.')
                            return matched_text
                # If not found with capitalization, return the known dept as-is
                return dept

        # Additional fallback: Check for partial matches of key department phrases
        # This catches variations like "Computing Technology, Division of Science"
        key_phrases = [
            'computing technology',
            'applied engineering',
            'life sciences',
            'science and technology',
            'homeland security',
        ]

        for phrase in key_phrases:
            if phrase in search_text:
                # Try to extract the full department name containing this phrase
                for line in lines:
                    if phrase in line.lower():
                        # Use regex to try extracting the full department name
                        dept_pattern = re.compile(r"((?:Computing Technology|Applied Engineering|Life Sciences|Science and Technology|Homeland Security)[^.;]*(?:Department|Division|Program)?)", re.IGNORECASE)
                        dept_match = dept_pattern.search(line)
                        if dept_match:
                            dept_text = dept_match.group(1).strip().rstrip(',.')
                            # Validate it's not too short or too long
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

        # Fallback: if no department found by pattern matching, search for known departments
        if not department:
            department = self._search_known_departments(text)

        # Fallback: if no name was found by the normal logic, scan every
        # PAGE_SIZE-line "page" for a simple "Dr. Lastname" pattern and return
        # the first match. This bypasses the stricter is_valid_name checks
        # because syllabus text often uses the short form 'Dr. Smith'.
        if not name:
            all_lines = text.split('\n')
            dr_pattern = re.compile(r"\bDr\.?\s+([A-Z][a-zA-Z\-]+)\b")
            for i in range(0, len(all_lines), PAGE_SIZE):
                page = all_lines[i:i+PAGE_SIZE]
                for page_line in page:
                    dr_match = dr_pattern.search(page_line)
                    if dr_match:
                        lastname = dr_match.group(1)
                        # Standardize to 'Dr. Lastname'
                        name = f"Dr. {lastname}"
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