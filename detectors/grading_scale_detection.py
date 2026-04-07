"""
Authors: Jackie E, Team Alpha fall 2025
Date 12/1/2025

Grading scale detection module.

This module provides the GradingScaleDetector class for extracting letter-based grading scales 
from syllabus text by finding A-F grade patterns.

we literally just look for A-F grading scales. They need to have all 12 letters (A, A-, B+, B, etc...) to be considered

"""

from typing import Dict, Any, List, Set
import re
import logging

# Required grade letters - must have all 12
REQUIRED_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'}
# Optional grade letter
OPTIONAL_GRADES = {'A+'}
# All valid grades
ALL_VALID_GRADES = REQUIRED_GRADES | OPTIONAL_GRADES

class GradingScaleDetector:
    """
    Simple grading scale detector that looks for A-F grade patterns.
    
    Searches through the document to find all 12 required grades (A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F)
    and optionally A+. Returns the complete block when found.
    """
    
    def __init__(self):
        """Initialize the detector."""
        self.field_name = 'grading_scale'
        self.logger = logging.getLogger('detector.grading_scale')
        
        # Pattern to match grade letters with optional + or -
        # More flexible pattern that handles various contexts
        # Allow table separators and punctuation after grades (| % , ) < > etc.) (TeamNexus)
        # Lookbehind prevents matching letters inside words (e.g. 'd' in "and") (TeamNexus)
        self.grade_pattern = re.compile(r'(?<![A-Za-z])([ABCDF][+-]?)(?=[\s:=\d\|\%\)\(\],\.;<>≤≥/-]|$)', re.IGNORECASE) #TeamNexus
    
    def find_grades_in_text(self, text: str) -> List[str]:
        """Find all grade letters in a piece of text."""
        matches = []
        
        # Pattern 1: Standard format (A:, A , A-, etc)
        standard_matches = self.grade_pattern.findall(text)
        matches.extend(standard_matches)
        
        # Pattern 2: After equals sign (90-100=A)
        equals_pattern = re.compile(r'[:=]\s*([ABCDF][+-]?)', re.IGNORECASE) #TeamNexus
        equals_matches = equals_pattern.findall(text)
        matches.extend(equals_matches)

        # Pattern 3: Trailing grades (90-100 A)
        trailing_grade_pattern = re.compile(r'\d{1,3}\s*%?\s*[-–—−]\s*\d{1,3}\s*%?\s*(?:=|:)?\s*([ABCDF][+-]?)\b',re.IGNORECASE) #TeamNexus
        matches.extend(trailing_grade_pattern.findall(text))

        # Pattern 4: Grades with ranges (A 90-100)
        #TeamNexus - this is a common format where the grade letter is followed by a range of percentages, we want to capture the grade letter in this case
        range_pattern = re.compile(r'([ABCDF][+-]?)\s*[:=\-]?\s*\d{1,3}\s*[%]?\s*[-–—−]\s*\d{1,3}\s*[%]?',re.IGNORECASE)
        to_range_pattern = re.compile(r'([ABCDF][+-]?)\s*[:=\-]?\s*\d{1,3}\s*%?\s*(?:to|through)\s*\d{1,3}\s*%?',re.IGNORECASE) #TeamNexus
        matches.extend(to_range_pattern.findall(text))
        range_matches = range_pattern.findall(text)
        matches.extend(range_matches)

        # Pattern 5: Inequality/Score format (A: 94 ≤ Score, B+: 87 ≤ Score < 90) (TeamNexus)
        inequality_pattern = re.compile(
            r'([ABCDF][+-]?)\s*[:=]?\s*\d{1,3}\s*%?\s*[≤≥<>]',
            re.IGNORECASE
        )
        matches.extend(inequality_pattern.findall(text))

        # Pattern 6: Compact range with no spaces (%to94, %to90) (TeamNexus)
        compact_range_pattern = re.compile(
            r'([ABCDF][+-]?)\s*[:=<]?\s*\d{1,3}\s*%?\s*to\d{1,3}',
            re.IGNORECASE
        )
        matches.extend(compact_range_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 7: "range TO range | Grade"  (e.g., "90% to 100% | A")  (GT)
        # ------------------------------------------------------------------
        range_to_trailing_grade_pattern = re.compile(
            r'\b\d{1,3}(?:\.\d+)?\s*%?\s*(?:to|through)\s*'
            r'\d{1,3}(?:\.\d+)?\s*%?\s*(?:[\|\:,\s]+)?\s*'
            r'([ABCDF][+-]?)\b',
            re.IGNORECASE
        )
        matches.extend(range_to_trailing_grade_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 8: "inequality THEN grade"  (e.g., "< 60% | F", "≤ 59.9 = F")
        # ------------------------------------------------------------------
        inequality_then_grade_pattern = re.compile(
            r'(?:(?:<|≤|>=|≥|>|<\s*=|>\s*=)\s*)\d{1,3}(?:\.\d+)?\s*%?\s*'
            r'(?:[\|\:=,\s]+)?\s*([ABCDF][+-]?)\b',
            re.IGNORECASE
        )
        matches.extend(inequality_then_grade_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 9: "number - below/and below/and above ... Grade" (GT variants)
        # e.g., "59-Below F", "59.9 or below F", "90 and above earns A-"
        # ------------------------------------------------------------------
        below_above_trailing_grade_pattern = re.compile(
            r'\b\d{1,3}(?:\.\d+)?\s*%?\s*(?:[-–—]\s*)?'
            r'(?:or\s+)?(?:and\s+)?(?:below|under|less\s+than)\s*'
            r'(?:\d{1,3}(?:\.\d+)?\s*%?\s*)?'
            r'(?:=|:)?\s*([ABCDF][+-]?)\b',
            re.IGNORECASE
        )
        matches.extend(below_above_trailing_grade_pattern.findall(text))

        above_trailing_grade_pattern = re.compile(
            r'\b\d{1,3}(?:\.\d+)?\s*%?\s*(?:or\s+)?(?:and\s+)?(?:above|higher|greater\s+than)\s*'
            r'(?:earns?|gets?|is|=|:)?\s*([ABCDF][+-]?)\b',
            re.IGNORECASE
        )
        matches.extend(above_trailing_grade_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 10: "Grade starts at number" / "Grade minimum number" (GT)
        # e.g., "A starts at 92.5", "B- minimum 79.5"
        # ------------------------------------------------------------------
        starts_at_pattern = re.compile(
            r'\b([ABCDF][+-]?)\b\s*(?:starts?\s+at|begin(?:s)?\s+at|minimum|cutoff|cut[-\s]*off)\s*'
            r'\d{1,3}(?:\.\d+)?\s*%?\b',
            re.IGNORECASE
        )
        matches.extend(starts_at_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 11: "Grade ... below number" (grade first)
        # e.g., "F below 59.5", "F under 60"
        # ------------------------------------------------------------------
        grade_then_below_number_pattern = re.compile(
            r'\b([ABCDF][+-]?)\b\s*(?:is\s*)?(?:below|under|less\s+than)\s*'
            r'\d{1,3}(?:\.\d+)?\s*%?\b',
            re.IGNORECASE
        )
        matches.extend(grade_then_below_number_pattern.findall(text))

        # ------------------------------------------------------------------
        # Pattern 12: "Grade range = N to M" (e.g., "A range = 90 to 100 percent") (TeamNexus)
        # Handles simplified grade scales that use "range" keyword
        # ------------------------------------------------------------------
        range_keyword_pattern = re.compile(
            r'(?<![A-Za-z])([ABCDF][+-]?)\s+range\s*=?\s*\d{1,3}',
            re.IGNORECASE
        )
        matches.extend(range_keyword_pattern.findall(text))

        # Normalize to uppercase and filter to valid grades only
        valid_grades = []
        for match in matches:
            normalized = match.upper()
            if normalized in ALL_VALID_GRADES:
                valid_grades.append(normalized)
        
        return valid_grades
    
    def has_all_required_grades(self, found_grades: Set[str]) -> bool:
        """Check if we found all 12 required grades."""
        return REQUIRED_GRADES.issubset(found_grades)
    
    
    def is_scale_header(self, line: str) -> bool:    #TeamNexus
        """Return True if line looks like a grading scale header."""
        return bool(re.search(
            r'\b(grading\s*scale|grade\s*scale|letter\s*grades?|final\s*grade\s*scale)\b',
            line,
            flags=re.IGNORECASE
        ))
    
    def has_scale_grade(self, line: str) -> bool:
        """Check if line has a grade letter actually paired with a number."""
        return bool(re.search(
            r'(?<![A-Za-z])[ABCDF][+-]?\s*[:=≤≥<>|]\s*\d'
            r'|\d\s*[-–—]\s*\d+\s*[^\n]*?(?<![A-Za-z])[ABCDF][+-]?\b'
            r'|(?<![A-Za-z])[ABCDF][+-]?\s+\d{2,3}'
            r'|(?<![A-Za-z])[ABCDF][+-]?\s+(?:starts?\s+at|begins?\s+at|minimum|cutoff)\s*\d',
            line, re.IGNORECASE
        ))
     
    def extract_block(self, lines: List[str], start_idx: int) -> str:
        """Extract a block of text that contains the grading scale."""
        found_grades = set()
        block_lines = []
        gap_count = 0
        max_gap_lines = 5   # allow a few non-grade lines inside tables (TeamNexus)
        
        # Look through lines starting from start_idx
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            # Find grades in this line
            line_grades = self.find_grades_in_text(line)
            
            if line_grades:
                # This line has grades, add it to our block
                gap_count = 0 # reset gap count when we find a grade line (TeamNexus)
                block_lines.append(line)
                found_grades.update(line_grades)
                
                # Check if we have all required grades (or near-complete with ≥5 modifiers)
                grade_check = (
                    self.has_all_required_grades(found_grades)
                    or self.has_near_all_required_grades_strict(found_grades)
                )
                if grade_check:
                    # We found a complete (or near-complete) scale! (TeamNexus)
                    block_text = " ".join(block_lines)

                    # Clean the block text to remove extra content
                    cleaned_block = self.clean_grading_scale_block(block_text)

                    # Limit output length (higher to avoid cutting off grades) (TeamNexus)
                    max_chars = 1500
                    if len(cleaned_block) <= max_chars:
                        return cleaned_block
                    else:
                        # Try to truncate at a reasonable point
                        truncated = cleaned_block[:max_chars] #TeamNexus
                        # If we still have near-complete grades in the truncated version
                        if self.has_near_all_required_grades_strict(set(self.find_grades_in_text(truncated))):
                            return truncated
                
                # If block is getting too long without finding all grades, give up
                if len(" ".join(block_lines)) > 2500: #TeamNexus
                    break
            else:
                    if found_grades:
                        # We are inside a grading scale block; keep a few non-grade lines (TeamNexus)
                        # (table headers/separators) instead of stopping immediately.
                        gap_count += 1
                        if gap_count <= max_gap_lines:
                            block_lines.append(line)  # keep context
                            continue
                        break
                    else:
                        break
        
        return ""
    
    def clean_grading_scale_block(self, text: str) -> str:
        """Clean the grading scale block to remove extra text and keep only the scale."""
        import re
        
        # Remove common prefixes that aren't part of the scale
        prefixes_to_remove = [
            r'^.*?guidelines using this schema:\s*',
            r'^.*?grading scale:\s*',
            r'^.*?final grades.*?scale:\s*',
            r'^.*?letter grades?\s*are\s*as\s*follows?:\s*',
            r'^.*?grading\s*criteria:?\s*',
            r'^.*?scale\s*is:?\s*',
        ]
        
        for prefix in prefixes_to_remove:
            text = re.sub(prefix, '', text, flags=re.IGNORECASE)
        
        # Remove assignment percentages and other non-scale content
        # Pattern to match things like "E-Portfolio 20%" or "Assignment 30%"
        # Remove assignment percentages like "Homework 20%" but NOT grades like "A 95%" (TeamNexus)
        text = re.sub(r'\b[A-Z][A-Z\w\-]{3,}\s+\d+%\b', '', text)  #TeamNexus
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # If the text starts with a grade letter, we're good
        # Use [ABCDF] not [A-F] to avoid matching 'E' which is not a valid grade (TeamNexus)
        if re.match(r'^[ABCDF][+-]?', text.strip()):
            return text.strip()

        # Try to find where the actual scale starts
        # Handles formats: "A:" "A=" "A 93" "A |" "A-:" etc. (TeamNexus)
        grade_start = re.search(r'(?<![A-Za-z])([ABCDF][+-]?)\s*[:=<>≤≥\d]', text)
        if grade_start:
            return text[grade_start.start():].strip()
        
        return text.strip()
    
    def has_near_all_required_grades(self, found_grades: Set[str]) -> bool:
        """Check if we found at least 11 of 12 required grades (allows one PDF-extraction miss). (TeamNexus)"""
        missing = REQUIRED_GRADES - found_grades
        return len(missing) <= 1

    def has_near_all_required_grades_strict(self, found_grades: Set[str]) -> bool:
        """11/12 required grades AND at least 5 modified grades (A-, B+, etc.).
        Prevents false positives from non-scale content that only has plain A/B/C/D/F. (TeamNexus)"""
        missing = REQUIRED_GRADES - found_grades
        if len(missing) > 1:
            return False
        modified = {g for g in found_grades if len(g) > 1}
        return len(modified) >= 5

    def has_scale_lines(self, block: str) -> bool:
        """Check if a block contains actual grade-number pairs (not just random letters). (TeamNexus)
        Also returns True if the block has all 12 required grades (e.g. two-row tables where
        grade letters and scores appear on separate rows). (TeamNexus)"""
        # If all 12 grades are present it's almost certainly a real scale
        if self.has_all_required_grades(set(self.find_grades_in_text(block))):
            return True
        count = sum(1 for line in block.split('\n') if self.has_scale_grade(line))
        return count >= 1 or self.has_scale_grade(block)

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect grading scale in the text.

        Args:
            text (str): The syllabus text to search.

        Returns:
            Dict[str, Any]: Dictionary with 'found', 'content', and 'grades_found'.
        """
        self.logger.info(f"Starting detection for field: {self.field_name}") #TeamNexus

        lines = text.split('\n')

        # Compile rubric pattern once for reuse below
        rubric_pattern = re.compile(
            r'(?is)\b(grading\s+breakdown|letter\s+grade|grading\s+criteria|final\s+grade)\b.*?'
            r'(?<![A-Za-z])A\s*=\s*[^.\n]{3,}.*?'
            r'(?<![A-Za-z])B\s*=\s*[^.\n]{3,}.*?'
            r'(?<![A-Za-z])C\s*=\s*[^.\n]{3,}.*?'
            r'(?<![A-Za-z])D\s*=\s*[^.\n]{3,}.*?'
            r'(?<![A-Za-z])F\s*=\s*[^.\n]{3,}',
        )

        # --------------------------------------------------
        # Pass 1: Scan ALL lines for scale headers and try extraction from each.
        # This ensures "Articulated Grade Scale" / "Grading Scale" headers are
        # processed before the fallback grade-letter scan below, preventing
        # spurious matches from earlier lines with random grade letters. (TeamNexus)
        # --------------------------------------------------
        for i, line in enumerate(lines):
            if self.is_scale_header(line):
                line_grades = self.find_grades_in_text(line)
                if not line_grades:
                    # Header with no grades on it — try the next few lines
                    for offset in range(1, 6):
                        if i + offset < len(lines):
                            block = self.extract_block(lines, i + offset)
                            if block:
                                block_grades = set(self.find_grades_in_text(block))
                                # A recognized header gives strong context — also accept near-complete (TeamNexus)
                                if (self.has_all_required_grades(block_grades)
                                        or self.has_near_all_required_grades_strict(block_grades)):
                                    self.logger.info(f"FOUND: {self.field_name} - Grades: {sorted(block_grades)}")
                                    return {
                                        'found': True,
                                        'content': block,
                                        'grades_found': sorted(list(block_grades))
                                    }
                else:
                    # Header line itself contains grade letters
                    block = self.extract_block(lines, i)
                    if block:
                        block_grades = set(self.find_grades_in_text(block))
                        if (self.has_all_required_grades(block_grades)
                                or self.has_near_all_required_grades_strict(block_grades)):
                            self.logger.info(f"FOUND: {self.field_name} - Grades: {sorted(block_grades)}")
                            return {
                                'found': True,
                                'content': block,
                                'grades_found': sorted(list(block_grades))
                            }

        # --------------------------------------------------
        # Pass 1.5: rubric-style letter grade descriptions (A = Excellent, etc.)
        # Runs AFTER Pass 1 so numeric scales under a recognized header take priority.
        # (Fixes Klenotic: Pass 1 finds the numeric scale; rubric never fires.) (TeamNexus)
        # --------------------------------------------------
        m = rubric_pattern.search(text)
        if m:
            full_match = m.group(0)
            # Extract from the first "A = ..." occurrence so we don't include
            # unrelated preamble (e.g. assignment percentages before the rubric). (TeamNexus)
            rubric_start = re.search(r'(?<![A-Za-z])A\s*=\s*', full_match, re.IGNORECASE)
            rubric_content = full_match[rubric_start.start():] if rubric_start else full_match
            block = " ".join(rubric_content.split())
            block = block[:1500] if len(block) > 1500 else block
            self.logger.info(f"FOUND: {self.field_name} - Rubric-style grading")
            return {
                "found": True,
                "content": block,
                "grades_found": ["A", "B", "C", "D", "F"]
            }

        # --------------------------------------------------
        # Pass 2: Grade-letter scan — only accept blocks that also contain
        # grade-number pairs (has_scale_lines), reducing false positives from
        # regular prose that happens to contain the letters A-F. (TeamNexus)
        # --------------------------------------------------
        for i, line in enumerate(lines):
            line_grades = self.find_grades_in_text(line)
            if line_grades:
                block = self.extract_block(lines, i)
                if block:
                    block_grades = set(self.find_grades_in_text(block))
                    if self.has_all_required_grades(block_grades) and self.has_scale_lines(block):
                        self.logger.info(f"FOUND: {self.field_name} - Grades: {sorted(block_grades)}")
                        return {
                            'found': True,
                            'content': block,
                            'grades_found': sorted(list(block_grades))
                        }

        # --------------------------------------------------
        # Pass 3: Relaxed grade requirement — accept 11/12 grades to handle
        # PDF extraction issues (e.g. "B-" extracted as "-"). (TeamNexus)
        # --------------------------------------------------
        for i, line in enumerate(lines):
            line_grades = self.find_grades_in_text(line)
            if line_grades:
                block = self.extract_block(lines, i)
                if block:
                    block_grades = set(self.find_grades_in_text(block))
                    if self.has_near_all_required_grades(block_grades) and self.has_scale_lines(block):
                        self.logger.info(f"FOUND: {self.field_name} - Near-complete grades: {sorted(block_grades)}")
                        return {
                            'found': True,
                            'content': block,
                            'grades_found': sorted(list(block_grades))
                        }

        # Fallback: look for abbreviated scales (e.g. "90% and above earns A-") (TeamNexus)
        abbreviated_pattern = re.compile(
            r'(\d{1,3})\s*%?\s*(?:and\s+above|or\s+higher|or\s+better|and\s+up)\s*'
            r'(?:\w+\s+)?(?:earns?|gets?|is|=|:)?\s*([ABCDF][+-]?)',
            re.IGNORECASE
        )
        abbrev_matches = abbreviated_pattern.findall(text)
        abbrev_grades = set()
        for _, grade in abbrev_matches:
            normalized = grade.upper()
            if normalized in ALL_VALID_GRADES:
                abbrev_grades.add(normalized)

        # Need at least one grade from each of the A, B, C, D tiers
        tiers_covered = {g[0] for g in abbrev_grades}
        if {'A', 'B', 'C', 'D'}.issubset(tiers_covered):
            content = ' '.join(m.group(0) for m in abbreviated_pattern.finditer(text))
            self.logger.info(f"FOUND: {self.field_name} - Abbreviated scale")
            return {
                'found': True,
                'content': content,
                'grades_found': sorted(list(abbrev_grades))
            }

        # --------------------------------------------------
        # Fallback: simplified grade scale with only A, B, C, D (and optionally F)
        # e.g. "90% to 100% A", "A range = 90 to 100 percent", "< 60% F"
        # Handles courses that use a 4- or 5-letter scale without +/- modifiers. (TeamNexus)
        # --------------------------------------------------
        simple_range_patterns = [
            # "N to N Grade" or "N-N Grade"
            re.compile(
                r'\d{1,3}\s*%?\s*(?:to|-|through)\s*\d{1,3}\s*%?\s*(?:[\|\:,\s]+)?\s*([ABCDF])\b',
                re.IGNORECASE
            ),
            # "< N Grade" or "> N Grade"
            re.compile(
                r'(?:<|≤|>|≥)\s*\d{1,3}\s*%?\s*(?:[\|\:=,\s]+)?\s*([ABCDF])\b',
                re.IGNORECASE
            ),
            # "Grade range = N to M" or "Grade N to M"
            re.compile(
                r'(?<![A-Za-z])([ABCDF])\s*(?:range\s*=?\s*)?\d{1,3}\s*(?:to|-|through)\s*\d{1,3}',
                re.IGNORECASE
            ),
        ]
        simple_grades = set()
        for pat in simple_range_patterns:
            for m in pat.finditer(text):
                grade = m.group(1).upper()
                if grade in ALL_VALID_GRADES:
                    simple_grades.add(grade)

        simple_tiers = {g[0] for g in simple_grades}
        if {'A', 'B', 'C', 'D'}.issubset(simple_tiers) and len(simple_grades) >= 4:
            content_parts = []
            for pat in simple_range_patterns:
                content_parts.extend(m.group(0) for m in pat.finditer(text))
            content = ' '.join(content_parts)
            self.logger.info(f"FOUND: {self.field_name} - Simplified scale (tiers: {sorted(simple_tiers)})")
            return {
                'found': True,
                'content': content,
                'grades_found': sorted(list(simple_grades))
            }

        # Fallback: pass/fail only if no letter scale found anywhere above
        non_letter_pattern = re.compile(
            r'\b(pass[/\s]fail|credit[/\s]no\s*credit|credit[/\s]fail|'
            r'satisfactory[/\s]unsatisfactory|s[/\s]u\s+grading|pass[/\s]no\s*pass)\b',
            re.IGNORECASE
        )
        pf_match = non_letter_pattern.search(text)
        if pf_match:
            # Only return pass/fail if it appears near a grading-related section
            context_start = max(0, pf_match.start() - 200)
            context = text[context_start:pf_match.end() + 200]
            if re.search(r'\b(grade|grading|evaluation|assessment|credit)\b', context, re.IGNORECASE):
                self.logger.info(f"FOUND: {self.field_name} - Pass/Fail type scale")
                return {
                    'found': True,
                    'content': pf_match.group(0),
                    'grades_found': []
                }

        # No valid grading scale found
        self.logger.info(f"NOT_FOUND: {self.field_name}")
        return {
            'found': False,
            'content': 'Missing',
            'grades_found': []
        }
