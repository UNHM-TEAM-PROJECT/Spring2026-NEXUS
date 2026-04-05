"""
Assignment Delivery Detector

Finds where students submit assignments in a syllabus.
Examples: Canvas, MyCourses, "Collected in class"

How it works:
1. Searches for platform names (Canvas, MyCourses, etc.)
2. Prefers lines that say "submit" or "upload"
3. Ignores weak phrases like "grades posted on"
4. Scores matches - higher score = more confident
5. Returns best match with confidence percentage

Example:
    Input: "Submit all work via Canvas"
    Output: "Canvas" (confidence: 95%)
"""

import re
from typing import Dict, Any, List, Set


class AssignmentDeliveryDetector:
    """Finds where students submit assignments in syllabi"""
    
    def __init__(self):
        # Platform patterns - checked in order (most specific first)
        # Format: (regex pattern, display name)
        
        self.platform_patterns = [
            # MyCourses variations (check before Canvas)
            (r'(?i)\bunh\s+mycourses\b', 'UNH MyCourses'),
            (r'(?i)\bmycourses\b', 'MyCourses'),
            
            # Canvas with MyCourses
            (r'(?i)\bcanvas\s*\(\s*mycourses\s*\)', 'Canvas (MyCourses)'),
            
            # Plain Canvas
            (r'(?i)\bcanvas\b', 'Canvas'),
            
            # Version control / code submission platforms (specific: "GitHub organization used to submit")
            (r'(?i)\bgithub\s+organization\b.*\bsubmit\b', 'GitHub'),
            (r'(?i)\bsubmit\b.*\bgithub\s+organization\b', 'GitHub'),

            # Assignment platforms
            (r'(?i)\bmyopenmath\b', 'MyOpenMath'),
            (r'(?i)\bmastering\s*(?:a\s*&\s*p|anatomy\s*(?:and|&)\s*physiology)', 'Mastering A&P'),
            (r'(?i)\bmasteringphysics\b', 'MasteringPhysics'),
            (r'(?i)\bmastering\s+physics\b', 'MasteringPhysics'),
            (r'\bCONNECT\b', 'CONNECT'),
            
            # Other LMS platforms
            (r'(?i)\bblackboard\b', 'Blackboard'),
            (r'(?i)\bgoogle\s+classroom\b', 'Google Classroom'),
            (r'(?i)\bmoodle\b', 'Moodle'),
            (r'(?i)\bturnitin\b', 'Turnitin'),
            
            # Physical delivery
            (r'(?i)\bwritten\s+assignments?\s+collected\s+in\s+class\b', 'Written assignments collected in class'),
            (r'(?i)\bcollected\s+in\s+class\b', 'Collected in class'),
            (r'(?i)\bin\s*-?\s*person\s+submission\b', 'In-person submission'),
            (r'(?i)\bhanded?\s+in\b', 'Handed in'),
            # "turn in ... hard copy" — explicit physical submission instruction
            (r'(?i)\bturn\s+in\b.*\bhard\s+cop\w+\b', 'Handed in'),
            (r'(?i)\bhard\s+cop\w+\b.*\bturn\s+in\b', 'Handed in'),
        ]
        
        # Noise phrases to remove
        self.noise_patterns = [
            r'\(embedded\s+in\s+[^)]+\)',
            r'\([^)]*grades?[^)]*\)',
            r'\bembedded\s+in\b',
            r'\bfor\s+grades?\b',
        ]
        
        # Section headers (strong signals)
        self.section_indicators = [
            r'(?i)^\s*assignment\s+(?:delivery|submission|platform)\s*:?',
            r'(?i)^\s*submission\s+(?:method|platform|process)\s*:?',
            r'(?i)^\s*how\s+to\s+submit\s*:?',
            r'(?i)^\s*where\s+to\s+submit\s*:?',
            r'(?i)^\s*(?:course|class)\s+(?:platform|management\s+system)\s*:?',
        ]
        
        # Delivery context (words about submitting)
        self.context_patterns = [
            r'(?i)assignments?\s+(?:are\s+)?(?:submitted|uploaded|turned\s+in|posted|delivered)\s+(?:via|on|to|through|using|in)',
            r'(?i)submit\s+(?:all\s+)?(?:your\s+)?(?:assignments?|work|papers?|homework)\s+(?:via|on|to|through|using|in)',
            r'(?i)(?:upload|post|turn\s+in)\s+(?:your\s+)?(?:assignments?|work|homework)\s+(?:via|on|to|through|in)',
            r'(?i)all\s+(?:assignments?|work|homework)\s+(?:will\s+be\s+)?(?:submitted|posted|uploaded)\s+(?:via|on|to|in)',
            r'(?i)(?:assignments?|homework)\s+(?:should|must)\s+be\s+(?:submitted|uploaded|posted|turned\s+in)\s+(?:via|on|to|in)',
            r'(?i)submit\s+them\s+in\s+a\s+single\s+file\b.*(?:canvas|mycourses)',
            r'(?i)all\s+assignments?\s+must\s+be\s+submitted\s+by\s+the\s+due\s+date',
        ]
        
        # Weak signals to ignore (grades, materials)
        self.weak_signal_patterns = [
            # --- Original patterns ---
            r'(?i)\bgrades?\s+(?:are\s+)?(?:posted|available|viewable)\s+(?:on|in)',
            r'(?i)\bcourse\s+materials?\s+(?:are\s+)?(?:on|in|available\s+(?:on|in))',
            r'(?i)\bsyllabus\s+(?:is\s+)?(?:posted\s+)?(?:on|in)',
            r'(?i)\bresources?\s+(?:are\s+)?(?:on|in)',

            # Canvas/MyCourses as gradebook / grade recording
            r'(?i)\bcanvas\s+grades?\b',
            r'(?i)\bentered\s+in\s+(?:the\s+)?canvas\b',
            r'(?i)\bgrade\s+will\s+be\s+entered\b',
            r'(?i)\blisted\s+in\s+(?:canvas|mycourses)\b',
            r'(?i)\bdate\s+and\s+time\s+listed\s+in\b',

            # Canvas/MyCourses as communication / Inbox tool
            r'(?i)\bcanvas\s+inbox\b',
            r'(?i)\bmycourses\s+(?:course\s+)?(?:email|inbox|message|messaging)\b',
            r'(?i)\busing\s+(?:the\s+)?(?:canvas|mycourses)\s+(?:email|inbox)\b',
            r'(?i)\bvia\s+mycourses\s+(?:email|messages?|messaging)\b',

            # Canvas/MyCourses as announcement platform
            r'(?i)\bannouncements?\s+(?:and\s+emails?\s+)?(?:in|on)\s+(?:canvas|mycourses)\b',
            r'(?i)\bpost\s+an?\s+announcement\s+(?:on|in)\s+(?:canvas|mycourses)\b',
            r'(?i)\bcheck\s+(?:the\s+)?course\s+announcements?\s+(?:and\s+emails?\s+)?(?:in|on)\s+(?:canvas|mycourses)\b',

            # Canvas/MyCourses as resource/material hub
            r'(?i)\b(?:canvas|mycourses)\s*/?s?\s*(?:mycourses|canvas)?\s+(?:at\s+https?://\S+\s+)?for\s+announcements?\b',
            r'(?i)\b(?:canvas|mycourses)\s+for\s+(?:announcements?|links?|course\s+materials?|classmates?|gradebook)\b',

            # Canvas/MyCourses as course website URL only
            r'(?i)\bcourse\s+(?:web\s+)?site\s*:\s*https?://mycourses\b',
            r'(?i)^https?://mycourses\.unh\.edu\S*\s*$',
            r'(?i)\bmycourses\.unh\.edu/courses/\d+',
            r'(?i)^\s*canvas\s+site\s*:?\s*$',

            # Canvas as App Inventor drawing surface (schedule lines)
            r'(?i)\bcanvas\s*,\s*sprites?\b',
            r'(?i)\bsprites?\s+and\s+(?:the\s+)?canvas\b',
            r'(?i)\banimations?\s+with\s+(?:the\s+)?canvas\b',

            # MyCourses as contact method
            r'(?i)\busing\s+mycourses\.unh\.edu\s+course\s+email\b',
            r'(?i)\bclass\s+forum\s+on\s+my\s+courses?\b',

            # "in Canvas/MyCourses" — materials, grades, solutions
            r'(?i)\bavailable\s+(?:through|via|on|in)\s+(?:canvas|mycourses)\b',

            # "See Canvas" / "See schedule on Canvas" / "Posted in Canvas."
            r'(?i)^\s*see\s+(?:schedule\s+(?:on|in)\s+)?(?:canvas|mycourses)\b',

            # mycourses.unh.edu URL (without /courses/ suffix)
            r'(?i)\bmycourses\.unh\.edu\b',

            # CAE tutoring reference — "through the CAE myCourses Canvas site"
            r'(?i)\bcae\s+(?:my\s+courses?|mycourses)\s*(?:canvas\s+)?site\b',
            r'(?i)\bmy\s+courses?\s+site\s+on\s+(?:your\s+)?canvas\b',

            # Canvas site as section header or description block
            r'(?i)^\s*canvas\s+site\s*$',
            r'(?i)\bcanvas\s+site\s+has\b',
            r'(?i)\bcanvas\s+site\s+for\s+this\s+course\b',

            # Canvas as communication/notification tool
            r'(?i)\bcanvas\s+(?:messages?|dashboard|announcements?|gradebook|calendar|mail)\b',
            r'(?i)\bdiscussion\s+(?:on|in)\s+canvas\b',
            r'(?i)\bcanvas\s+announcements?\b',
            r'(?i)\bcanvas\s+here\s*:',

            # "handed in late" / "turn in late" — late penalty context, not submission method
            r'(?i)\bhanded?\s+in\s+late\b',
            r'(?i)\bturn\s+in\b.*\b(?:late|after\s+(?:solutions?|the\s+due))\b',

            # MyCourses/Canvas as LMS description
            r'(?i)\b(?:canvas|mycourses)\s+(?:is\s+)?(?:unh[\'s]*\s+)?course\s+management\s+system\b',
            r'(?i)\buse\s+(?:unh\s+)?mycourses\s+to\s+access\b',
            r'(?i)\buse\s+(?:unh[\'s]*\s+)?(?:implementation\s+of\s+)?canvas\s+for\s+(?:use\s+in\s+)?(?:teaching|this\s+course)\b',
            r'(?i)\buse\s+canvas\s*[™®]?\s+system\b',

            # Course materials available through MyCourses
            r'(?i)\bcourse\s+materials?\s+(?:are\s+)?available\s+through\b',
            r'(?i)\ball\s+course\s+(?:information|materials?)\s+will\s+be\s+posted\b',

            # Canvas as attendance/access platform
            r'(?i)\bresponsible\s+for\s+all\s+material\s+(?:covered\s+in\s+class\s+and\s+)?posted\s+on\s+canvas\b',

            # Canvas as link to textbook/resources
            r'(?i)\bcanvas\s+(?:web)?site\s+for\s+this\s+course\s+has\s+a\s+link\b',

            # Canvas site section header / tool listing
            r'(?i)^\s*canvas\s+site\s+and\b',
            r'(?i)\bcanvas\s+site\s*,\s*(?:github|discord|course\s+website)\b',

            # Login on Canvas
            r'(?i)\b(?:login|log\s+in)\s+on\s+canvas\b',

            # "See Canvas" for office hours / schedule
            r'(?i)^\s*(?:office\s+hours?\s*:.*)?see\s+canvas\s*\.?\s*$',

            # Canvas as LMS description
            r'(?i)\bcanvas\s+learning\s+management\s+system\b',
            r'(?i)\b(?:canvas|mycourses)\s+is\s+the\s+learning\s+management\s+system\b',

            # MyCourses late penalty
            r'(?i)\bmycourses\s+will\s+automatically\s+subtract\b',

            # Access class via Canvas/MyCourses
            r'(?i)\buse\s+(?:mycourses|canvas)\b.*\baccessible\s+through\b',

            # Changes/announcements on Canvas
            r'(?i)\bwatch\s+for\s+(?:revisions?|updates?)\s+in\s+(?:canvas|mycourses)\b',
            r'(?i)\b(?:changes?|updates?|cancellation)\b.*\bannounced\b.*\b(?:canvas|mycourses)\b',

            # Contact through Canvas (office hours context)
            r'(?i)\bcontact\s+(?:through|via)\s+canvas\b',

            # Course platform description block
            r'(?i)\bcourse\s+platform\s*:\s*information\s+on\s+(?:canvas|mycourses)\b',

            # Canvas for accessing pre-lecture/module materials
            r'(?i)\bpublished\s+(?:prior\s+to\s+class\s+)?in\s+canvas\b',
            r'(?i)\breviewing\s+any\s+pre-?lecture\b',

            # Turnitin Use Policy section header (not a submission instruction)
            r'(?i)^\s*turnitin\s+use\s+policy\s*$',

            # "MyCourses and this course syllabus" bullet
            r'(?i)^\s*[●•\-\*]?\s*mycourses\s+and\s+this\s+course\s+syllabus\s*\.?\s*$',

            # Canvas course page for calendar/schedule
            r'(?i)\bcourse\s+canvas\s+page\s+for\s+the\s+most\s+up-to-date\b',

            # "available through our MyCourses site" — materials, not submission
            r'(?i)\bwill\s+be\s+available\s+through\s+(?:our\s+)?(?:canvas|mycourses)\s+site\b',

            # "emails in MyCourses for up-to-date information"
            r'(?i)\b(?:canvas|mycourses)\s+for\s+up-to-date\s+information\b',

            # "Email me...using MyCourses" — truncated contact line
            r'(?i)\bemail\s+(?:me|the\s+instructor|course\s+instructor)\b.*\busing\s+mycourses\b',

            # Schedule line: "Variables, Conditionals, and the Canvas Videos"
            r'(?i)\band\s+the\s+canvas\s+videos?\b',

            # "Canvas about possible remote class meeting"
            r'(?i)\bcanvas\s+about\s+possible\s+remote\b',

            # "MyCourses will" — late penalty / grade automation
            r'(?i)\bmycourses\s+will\s+(?:automatically\s+)?subtract\b',
            r'(?i)\bmycourses\s+will\b',

            # "myCourses (Canvas):" section header
            r'(?i)^\s*mycourses\s*\(\s*canvas\s*\)\s*:?\s*$',

            # IT/access help context
            r'(?i)\bissues?\s+with\s+access\s+to\s+(?:canvas|mycourses)\b',
            r'(?i)\btools?\s+for\s+accessing\s+(?:canvas|mycourses)\b',
            r'(?i)\bmobile\s+device\s+apps?\s+for\s+(?:canvas|mycourses)\b',
            r'(?i)\bhelp\s+button\b.*\bcanvas\b',
            r'(?i)\btechnical\s+assistance\s+related\s+to\b',

            # "check your email account and the Canvas course sites" — COVID/news context
            r'(?i)\bcheck\s+your\b.*\bcanvas\s+course\s+sites?\b',

            # "Canvas at least once a day" — check Canvas regularly
            r'(?i)\bcanvas\s+at\s+least\s+once\s+a\s+day\b',

            # "email/Canvas" — contact method shorthand
            r'(?i)\bemail\s*/\s*canvas\b',

            # "updates in Canvas" — short announcement line
            r'(?i)\bupdates?\s+in\s+(?:canvas|mycourses)\b',

            # "available via any myCourses course" — media/resource fragment
            r'(?i)\bvia\s+any\s+mycourses\s+course\b',

            # "While we use myCourses (aka Canvas) for our online course"
            r'(?i)\bwhile\s+we\s+use\s+(?:canvas|mycourses)\b',

            # "All lecture notes are on this canvas site"
            r'(?i)\blecture\s+notes\s+are\s+on\s+this\s+canvas\s+site\b',

            # "topical modules, as shown in our Canvas website"
            r'(?i)\bmodules?\b.*\bshown\s+in\s+(?:our\s+)?canvas\b',

            # Schedule table line: "Variables, Conditionals, and the Canvas |"
            r'(?i)variables,\s*conditionals,\s*and\s*the\s*canvas\b',

            # "Email me...using MyCourses" — truncated at end of line
            r'(?i)^[\d\.\s]*email\s+me\b.*\busing\s+mycourses\s*$',

            # "MyCourses Canvas Inbox tool" — contact/communication
            r'(?i)\bmycourses\s+canvas\s+inbox\s*tool\b',

            # "Canvas NameCoach" and "new tool in Canvas, NameCoach"
            r'(?i)^\s*canvas\s+namecoach\s*$',
            r'(?i)\bnew\s+tool\s+in\s+canvas,?\s+namecoach\b',

            # Turnitin policy paragraph
            r'(?i)\bturnitin\.com\b',
            r'(?i)\bchecks?\s+students\W+work\s+for\s+(?:improper\s+citation|potential\s+plagiarism)\b',

            # "MyCourses (also called Canvas) is the learning management system"
            r'(?i)\bmycourses\s*\(also\s+called\s+canvas\)\b',

            # "Help button in the left-hand column of your Canvas course page"
            r'(?i)\bleft-hand\s+column\s+of\s+your\s+canvas\b',

            # "weekly online quiz will be provided through Canvas (UNH MyCourses)"
            r'(?i)\bweekly\s+online\s+quiz\s+will\s+be\s+provided\s+through\b',

            # "MyCourses])" — fragment from a parenthetical reference
            r'(?i)^mycourses\]\)',

            # "Email me...using MyCourses" — any variation ending with MyCourses
            r'(?i)\bemail\s+me\b.*\busing\s+mycourses\s*$',

            # "make an appointment using MyCourses Canvas Inbox tool" (with or without space)
            r'(?i)\bmake\s+an\s+appointment\s+using\s*mycourses\b',

            # "myCourses is UNH's course management system"
            r'(?i)\bmycourses\s+is\s+unh\b',

            # "MyCourses (also called Canvas) is the learning management system"
            r'(?i)\bmycourses\s*\(also\s+called\s+canvas\)\s+is\b',

            # "will be posted in Canvas/MyCourses" — materials made available, not submission
            r'(?i)\bwill\s+be\s+posted\s+(?:in|on)\s+(?:canvas|mycourses)\b',

            # Standalone "Posted in Canvas." — schedule/materials line
            r'(?i)^\s*posted\s+in\s+(?:canvas|mycourses)\b',

            # "syllabus will be posted" — administrative, not submission
            r'(?i)\bsyllabus\b.*\bwill\s+be\s+posted\b',

            # "assignment information will be posted on Canvas" — availability, not submission
            r'(?i)\bassignment\s+information\b.*\bposted\b',
            r'(?i)\bassignment\s+(?:information\s+)?(?:will\s+be\s+)?posted\s+(?:on|in)\s+(?:canvas|mycourses)\b',

            # "absence/missing the class ... using MyCourses" — contact for absences
            r'(?i)\b(?:absence|missing\s+(?:the\s+)?class)\b.*\busing\s+mycourses\b',

            # "turned in late/after" — late penalty context, not submission method
            r'(?i)\bturned?\s+in\s+(?:late|after|past)\b',

            # "homework/assignments will be posted in Canvas" — posting for viewing, not submission
            r'(?i)(?:homework|assignments?)\s+will\s+be\s+posted\s+(?:in|on)\s+(?:canvas|mycourses)\b',

            # "Canvas is the learning management tool" (not just system)
            r'(?i)\b(?:canvas|mycourses)\s+is\s+the\s+learning\s+management\s+tool\b',

            # "check Canvas/MyCourses regularly" — monitoring reminder, not submission
            r'(?i)\bcheck\s+(?:your\s+)?(?:canvas|mycourses)\s+(?:regularly|frequently|often)\b',

            # "check Canvas/MyCourses for details/updates" — materials/info context
            r'(?i)\bcheck\s+(?:canvas|mycourses)\s+for\s+(?:details|updates?|more\s+information|relevant)\b',

            # "active in the canvas page" — instructor presence, not submission
            r'(?i)\bactive\s+in\s+(?:the\s+)?canvas\s+(?:page|site|course)\b',

            # "canvas. Otherwise" / "canvas, please" — sentence fragment from OCR/extraction
            r'(?i)^canvas[.,]\s+(?:otherwise|please|feel)\b',

            # "course is administered using Canvas/MyCourses" — LMS description, not submission
            r'(?i)\bcourse\s+is\s+administered\s+using\b',

            # "curated through Canvas" — course materials context, not submission
            r'(?i)\bcurated\s+through\s+(?:canvas|mycourses)\b',

            # "referenced from the Canvas site" — materials location, not submission
            r'(?i)\breferenced\s+from\s+(?:the\s+)?(?:canvas|mycourses)\s+site\b',

            # "via email/Canvas" or "via email/MyCourses" — communication, not submission
            r'(?i)\bvia\s+email\s*/\s*(?:canvas|mycourses)\b',

            # "check MyCourses/Canvas" — material access, not submission
            r'(?i)\bcheck\s+(?:mycourses|canvas)\s*/\s*(?:canvas|mycourses)\b',

        ]
    
    def _clean_line_for_extraction(self, line: str) -> str:
        """Remove noise phrases like '(embedded in Canvas)' from line"""
        cleaned = line
        
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _extract_platforms_from_text(self, text: str) -> Set[str]:
        """Find all platform names in text (e.g., {'Canvas', 'MyOpenMath'})"""
        platforms = set()
        cleaned = self._clean_line_for_extraction(text)
        
        for pattern, platform_name in self.platform_patterns:
            if re.search(pattern, cleaned):
                platforms.add(platform_name)
        
        return platforms
    
    def _has_section_indicator(self, line: str) -> bool:
        """Check if line is a section header like 'Assignment Submission:'"""
        return any(re.search(p, line) for p in self.section_indicators)
    
    def _has_delivery_context(self, line: str) -> bool:
        """Check if line talks about submitting (e.g., 'Submit work via Canvas')"""
        return any(re.search(p, line) for p in self.context_patterns)
    
    def _is_tool_listing(self, line: str) -> bool:
        """
        Catches lines listing Canvas/MyCourses as a multi-purpose hub.
        e.g. "Canvas/MyCourses for announcements, links, gradebook, Discord..."
        Fires if Canvas/MyCourses is mentioned + 2 or more non-submission tool keywords.
        """
        l = line.lower()
        if not re.search(r'(?i)\b(?:canvas|mycourses)\b', l):
            return False
        tool_keywords = [
            'announcement', 'gradebook', 'classmates', 'discord', 'runestone',
            'google drive', 'links to', 'weekly slides', 'instructional materials',
            'inbox tool', 'namecoach', 'onedrive', 'rave', 'zotero',
        ]
        hits = sum(1 for kw in tool_keywords if kw in l)
        return hits >= 2

    def _is_weak_signal(self, line: str) -> bool:
        """Check if line is about grades/materials/tools, not submission"""
        if self._is_tool_listing(line):
            return True
        return any(re.search(p, line) for p in self.weak_signal_patterns)
    
    def _is_definite_submission(self, line: str) -> bool:
        """Lines that are unambiguously submission instructions — always override weak signals."""
        patterns = [
            r'(?i)\bsubmissions?\s+must\s+be\s+completed\s+through\s+(?:canvas|mycourses)\b',
            r'(?i)\ball\s+assignments?\s+should\s+be\s+posted\s+(?:on|in)\s+(?:canvas|mycourses)\b',
            r'(?i)\ball\s+homework\s+will\s+be\s+uploaded\b.*\bcanvas\b',
            r'(?i)\bsubmit\s+them\s+in\s+a\s+single\s+file\b',
            r'(?i)\bin\s+order\s+to\s+receive\s+credits?\b',
        ]
        return any(re.search(p, line) for p in patterns)
    
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Find assignment delivery platform in syllabus.
        
        Returns dict with 'found' (bool), 'content' (str), 'confidence' (float)
        Example: {'found': True, 'content': 'Canvas', 'confidence': 95.5}
        """
        if not text or not text.strip():
            return {"found": False, "content": "", "confidence": 0.0}
        
        lines = text.split('\n')
        candidates = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped or len(line_stripped) < 5 or len(line_stripped) > 1500:
                continue
            
            if self._is_weak_signal(line_stripped) and not self._is_definite_submission(line_stripped):
                continue
            
            is_section = self._has_section_indicator(line_stripped)
            has_context = self._has_delivery_context(line_stripped)
            platforms = self._extract_platforms_from_text(line_stripped)
            
            if not platforms:
                continue
            
            # Calculate score
            score = 50
            if is_section:
                score += 40
            if has_context:
                score += 35
            
            position_ratio = i / max(len(lines), 1)
            if position_ratio < 0.15:
                score += 25
            elif position_ratio < 0.35:
                score += 18
            elif position_ratio < 0.55:
                score += 10
            elif position_ratio < 0.75:
                score += 5
            
            if len(platforms) > 1:
                score += 12
            
            platform_list = sorted(list(platforms), key=lambda x: x.lower())
            content = '; '.join(platform_list)
            
            candidates.append({
                'content': content,
                'score': score,
                'line': i,
                'has_context': has_context,
                'is_section': is_section,
                'platform_count': len(platforms)
            })
        
        # Select best match
        if candidates:
            best = max(candidates, key=lambda x: (
                x['score'], x['is_section'], x['has_context'], 
                x['platform_count'], -x['line']
            ))
            
            confidence = min(100.0, (best['score'] / 162.0) * 100)
            if confidence < 45:
                confidence = 45
            
            return {'found': True, 'content': best['content'], 'confidence': round(confidence, 2)}
        
        return {'found': False, 'content': '', 'confidence': 0.0}


def detect_assignment_delivery(text: str) -> str:
    """Simple wrapper - returns platform name or empty string"""
    detector = AssignmentDeliveryDetector()
    result = detector.detect(text)
    return result.get('content', '') if result.get('found') else ''


if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("Assignments are submitted via myCourses.", "MyCourses"),
        ("Submit all work through Canvas.", "Canvas"),
        ("MyOpenMath (embedded in Canvas); Written Assignments collected in class", 
         "Canvas; MyOpenMath; Written assignments collected in class"),
        ("Use MasteringPhysics for homework.", "MasteringPhysics"),
        ("Assignments delivered through UNH MyCourses", "UNH MyCourses"),
        ("Upload assignments to Canvas (myCourses)", "Canvas (MyCourses)"),
        ("Grades are posted on Canvas. Submit work via MyCourses and Mastering A&P", 
         "Mastering A&P; MyCourses"),
        ("All assignments submitted via Canvas (MyCourses)", "Canvas (MyCourses)"),
        ("Submit homework on MyCourses; Mastering A&P", "Mastering A&P; MyCourses"),
    ]
    
    detector = AssignmentDeliveryDetector()
    
    print("Testing Assignment Delivery Detector:")
    print("=" * 70)
    
    for text, expected in test_cases:
        result = detector.detect(text)
        found = result.get('content', '')
        confidence = result.get('confidence', 0)
        
        found_norm = {p.strip().lower() for p in found.split(';') if p.strip()}
        expected_norm = {p.strip().lower() for p in expected.split(';') if p.strip()}
        
        match = found_norm == expected_norm
        status = "✓" if match else "✗"
        
        print(f"\n{status} Test case:")
        print(f"  Input: {text}")
        print(f"  Expected: {expected}")
        print(f"  Got: {found} (confidence: {confidence}%)")
        if not match:
            print(f"  Expected set: {expected_norm}")
            print(f"  Got set: {found_norm}")