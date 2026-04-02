"""
Online Detection - Course Modality Detector

Detects course delivery format from syllabus text.
Returns: Online, Hybrid, or In-Person

How it works:
1. Checks for definitive statements ("100% online", "hybrid course")
2. Analyzes class location sections (separate from office hours)
3. Looks for physical locations (rooms, buildings) or online platforms (Zoom)
4. Uses scoring system for soft signals
5. Returns modality with confidence score

Example:
    Input: "Class meets via Zoom on Tuesdays"
    Output: "Online" (confidence: 0.90)
"""
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Tuple, Optional

__all__ = [
    "detect_course_delivery",
    "detect_modality",
    "format_modality_card",
    "quick_course_metadata",
]

# Detection limits (how far to search in text)
MAX_LINES_LOCATION_SEARCH = 300
MAX_LINES_OFFICE_SEARCH = 400
HEADER_SEARCH_LIMIT_800 = 800
HEADER_SEARCH_LIMIT_1000 = 1000
HEADER_SEARCH_LIMIT_500 = 500
HEADER_SEARCH_LIMIT_600 = 600
HEADER_SEARCH_LIMIT_1500 = 1500
HEADER_SEARCH_LIMIT_400 = 400
CONTEXT_WINDOW_BEFORE = 1
CONTEXT_WINDOW_AFTER = 6
CONTEXT_OFFSET_50 = 50
CONTEXT_OFFSET_60 = 60
CONTEXT_OFFSET_150 = 150
CONTEXT_OFFSET_220 = 220

# Scoring thresholds
MIN_CONFIDENCE_THRESHOLD = 0.60
HYBRID_SCORE_MULTIPLIER = 0.55
INPERSON_PENALTY = 4.0
ONLINE_BOOST = 2.0
MIN_SCORE_THRESHOLD_ONLINE = 1.3
MIN_SCORE_THRESHOLD_INPERSON = 1.3
MIN_SCORE_THRESHOLD_ONLINE_BOOST = 1.0

# Pattern definitions
BUILDING_WORDS = r"(?:rm\.?|room|hall|bldg\.?|building|lab|laboratory|lecture hall|classroom|pandra|pandora)"
DAYS_TOKEN = r"(?:m/w|mw|t/th|tth|tr|mon(?:day)?|tue(?:s)?(?:day)?|wed(?:nesday)?|thu(?:rs)?(?:day)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
TIME_TOKEN = r"(?:\b\d{1,2}:\d{2}\s?(?:am|pm)?\b|\b\d{1,2}\s?(?:am|pm)\b)"

# ===================================================================
# TEXT NORMALIZATION
# ===================================================================

def normalize_syllabus_text(text: str) -> str:
    """Clean up text - normalize unicode, bullets, and whitespace"""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    
    # Replace bullet characters with dashes
    t = (
        t.replace("•", "- ")
        .replace("▪", "- ")
        .replace("‣", "- ")
        .replace("◦", "- ")
        .replace("\u2022", "- ")
    )
    
    # Normalize whitespace
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ===================================================================
# SECTION EXTRACTION
# ===================================================================

def _find_class_location_section(text: str) -> str:
    """Extract class location/meeting section (not office hours)"""
    lines = text.split("\n")
    
    location_patterns = [
        r"(?i)(?:class|course)\s+(?:location|meets?|meeting|time)",
        r"(?i)(?:meeting\s+)?(?:location|place|where)",
        r"(?i)(?:time\s+and\s+)?location",
        r"(?i)(?:class|course)\s+delivery",
        r"(?i)delivery\s+(?:method|format|mode)",
        r"(?i)modality",
        r"(?i)schedule",
    ]
    
    for i, line in enumerate(lines[:MAX_LINES_LOCATION_SEARCH]):
        for pat in location_patterns:
            if re.search(pat, line):
                start = max(0, i - CONTEXT_WINDOW_BEFORE)
                end = min(i + CONTEXT_WINDOW_AFTER, len(lines))
                return "\n".join(lines[start:end]).lower()
    return ""


def _find_office_hours_section(text: str) -> str:
    """Extract office hours section to avoid confusion with class location"""
    lines = text.split("\n")
    for i, line in enumerate(lines[:MAX_LINES_OFFICE_SEARCH]):
        if re.search(r"(?i)\boffice\s+hours?\b", line):
            start = max(0, i - CONTEXT_WINDOW_BEFORE)
            end = min(i + CONTEXT_WINDOW_AFTER, len(lines))
            return "\n".join(lines[start:end]).lower()
    return ""

# ===================================================================
# PATTERN CHECKERS
# ===================================================================

def _has_zoom_class_phrase(s: str) -> bool:
    """Check if Zoom/Teams/Webex mentioned for class meetings (not office hours)"""
    if not s:
        return False
    # Exclude contingency language (Zoom only as backup/emergency option)
    if re.search(r'(?i)(in\s+case|if\s+needed|contingency|backup|may\s+need\s+to\s+move|need\s+to\s+move\s+to\s+online)', s):
        return False
    # Exclude appointment/office hours lines before checking
    lines = s.split('\n')
    filtered = [l for l in lines if not re.search(r'(?i)(appointment|office\s+hours?|book\s+a|book\s+an|calendly)', l)]
    s_filtered = '\n'.join(filtered)
    # Require class/course/lecture context — not just any "meeting...Zoom"
    # Pattern 2 removed: "\b(meeting)\b.*\bzoom\b.*\bclass\b" was too broad (matched "class support")
    _vc = r"zoom|microsoft\s*teams|teams|webex"
    return bool(
        re.search(
            rf"(?i)\b(class|course|lecture|section)\b.*\b(meets?|held|delivered|offered)\b.*\b({_vc})\b"
            rf"|\b({_vc})\b[:\s]*\b(class|course|lecture)\b.*\b(meets?|meeting|session)\b"
            rf"|\blocation\s*:.*\b({_vc})\b"
            rf"|\bdelivered\s+(?:via|through|on|using)\s+({_vc})\b",
            s_filtered,
            re.IGNORECASE
        )
    )


def _has_physical_room_phrase(s: str) -> bool:
    """Check if physical room mentioned for classes (filter out support services)"""
    if not s:
        return False
    
    # Filter out support service contexts
    support_contexts = [
        "accessibility services", "student accessibility", "counseling services",
        "tutoring", "writing center", "library", "financial aid", "registrar",
        "dean's office", "advisement", "student services"
    ]
    s_lower = s.lower()
    if any(ctx in s_lower for ctx in support_contexts):
        return False
    
    if re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", s):
        return True
    if re.search(rf"(?i)\b(meets?|meeting)\s+in\b.*\b({BUILDING_WORDS})\b", s):
        return True
    return False

# ===================================================================
# MAIN DETECTION FUNCTION
# ===================================================================

def detect_course_delivery(text: str) -> Dict[str, object]:
    """
    Detect course modality using multi-phase rule-based approach.
    
    Returns dict with:
        - 'modality': "Online", "Hybrid", "In-Person", or "Unknown"
        - 'confidence': 0.0-1.0
        - 'evidence': list of detection reasons
    
    Detection phases:
        1. Explicit statements ("100% online", "hybrid course")
        2. Class location section analysis
        3. Header patterns
        4. Scoring for soft signals
    """
    if not text:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": []}
    
    t = normalize_syllabus_text(text)
    t_lower = t.lower()
    
    class_section = _find_class_location_section(t)
    office_section = _find_office_hours_section(t)
    evidence = []
    
    # ================================================================
    # PHASE 1: Definitive statements (highest confidence)
    # ================================================================
    
    online_definitive = [
        "100% online", "fully online", "completely online", "entirely online",
        "online only", "course is online", "this course is online",
        "delivered entirely online", "offered online",
        "synchronous online", "meets online", "meets on zoom", "meets via zoom",
        "asynchronous online", "fully asynchronous", "entirely asynchronous",
        "this course meets synchronously online",
        "no scheduled class times", "no scheduled class meeting times",
        "there are no scheduled class times", "there are no scheduled meeting times",
        "this course is an online",
        "course is an online",
        "as an online class",
        "online, asynchronous course",
        "online asynchronous course",
        "remote through zoom",
    ]
    for phrase in online_definitive:
        if phrase in t_lower:
            return {"modality": "Online", "confidence": 0.95, "evidence": [phrase]}

    # "location: online" — but if it also lists a physical room, it's Hybrid
    for loc_pat in [r"(?i)^location\s*:?\s*online\b", r"(?i)location:\s*online\b"]:
        loc_m = re.search(loc_pat, t_lower, re.MULTILINE)
        if loc_m:
            loc_ctx = t_lower[loc_m.start():min(loc_m.start() + 200, len(t_lower))]
            if re.search(rf"(?i)\b(room|rm\.?|pandora|pandra|hall|building)\b", loc_ctx):
                return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["location states online and physical room"]}
            return {"modality": "Online", "confidence": 0.93, "evidence": ["location field states online"]}

    # "Class meetings: ... (ONLINE)" in header
    if re.search(r"(?i)class\s+meetings?\s*:.*\(online\)", t_lower[:HEADER_SEARCH_LIMIT_1000]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["class meetings listed as online"]}

    # Hybrid checks (before online-only)
    hybrid_definitive = [
        "hybrid course", "hy-flex", "hyflex", "blended course",
        "hybrid format", "blended format", "hybrid delivery",
        "hybrid accelerated",
        "both in-person and remote modality",
        "in-person and remote modality",
        "face-to-face every other week",
        "every other week and online",
        "in-person and online via asynchronous",
        "f2f/ol", "ol/f2f", "f2f/online", "online/f2f",
    ]
    for phrase in hybrid_definitive:
        if phrase in t_lower:
            idx = t_lower.find(phrase)
            context_before = t_lower[max(0, idx - 100):idx]
            phrase_with_after = t_lower[idx:idx + len(phrase) + 20]
            # Skip if negated: "not a hybrid course", "is NOT a hybrid format"
            if re.search(r'\b(not|no|never|isn\'t|isnt)\b', context_before + phrase_with_after, re.IGNORECASE):
                continue
            # Skip if contingency: "require a change to hybrid format" (more specific)
            if re.search(r'\b(require\s+a\s+change\s+to|move\s+to\s+(?:a\s+)?hybrid)\b', context_before, re.IGNORECASE):
                continue
            return {"modality": "Hybrid", "confidence": 0.95, "evidence": [phrase]}
    
    # Pattern: online AND physical location
    if re.search(r"(?i)\b(online|zoom|teams|webex).*\b(and also in|also in)\b.*\b(room|rm\.?|pandora|pandra|hall|building)\b", t_lower[:HEADER_SEARCH_LIMIT_1000]):
        return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["online and also in physical location"]}
    
    if re.search(r"(?i)\blocation.*:.*\bonline\b.*\band\b.*\b(room|rm\.?|pandora|pandra)\b", t_lower[:HEADER_SEARCH_LIMIT_1000]):
        return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["location shows both online and room"]}
    
    # Location: Online (but not if also mentions room)
    location_online_match = re.search(r"(?i)(?:time\s+and\s+)?location[:\s]+.*\bonline\b", t_lower[:HEADER_SEARCH_LIMIT_800])
    if location_online_match:
        location_text = t_lower[location_online_match.start():min(location_online_match.end() + 100, len(t_lower))]
        if not any(word in location_text for word in ["room", "rm", "hall", "building", "pandora", "pandra"]):
            return {"modality": "Online", "confidence": 0.93, "evidence": ["location states online"]}
    # ADD after location_online_match block:
    if re.search(r"(?i)location\s*:.*\bhybrid\b", t_lower[:HEADER_SEARCH_LIMIT_1500]):
        return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["location states hybrid"]}
    
    # Day/time with online
    if re.search(r"(?i)(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*[,\s]+[\d:\-]+(?:am|pm)?.*\bonline\b", t_lower[:HEADER_SEARCH_LIMIT_800]):
        return {"modality": "Online", "confidence": 0.93, "evidence": ["class time shows online"]}
    
    # Face-to-face + async/online
    if re.search(r"(?i)face[-\s]?to[-\s]?face\s+(?:weekly|sessions?).*(?:async|online)", t_lower):
        return {"modality": "Hybrid", "confidence": 0.92, "evidence": ["face-to-face + async/online components"]}
    
    # ================================================================
    # PHASE 2: Class location section takes precedence
    # ================================================================
    
    header_1500 = t_lower[:HEADER_SEARCH_LIMIT_1500]
    if "hybrid" in header_1500:
        for _hw in ["hybrid delivery", "hybrid course", "hybrid format", "hybrid modality",
                    "online with some campus", "hybrid accelerated", "in-person and remote modality"]:
            if _hw in header_1500:
                _hi = header_1500.find(_hw)
                _hctx = header_1500[max(0, _hi - 40):_hi + len(_hw) + 10]
                if not re.search(r'\b(not|no|never|isn\'t|isnt)\b', _hctx, re.IGNORECASE):
                    return {"modality": "Hybrid", "confidence": 0.95, "evidence": ["header explicitly states hybrid"]}

    # Helper: only treat "hybrid" as a delivery mode if it's in a course-delivery context
    # (not "hybrid approach", "hybrid of case studies", etc.)
    _hybrid_delivery_re = re.compile(
        r'(?i)\bhybrid\b\s*(?:course|class|delivery|format|modality|accelerated|section)\b'
        r'|\b(?:hybrid\s+delivery|hybrid\s+course|hybrid\s+format|hybrid\s+modality)\b',
    )
    _hybrid_in_header = bool(_hybrid_delivery_re.search(header_1500))
    # Also block In-Person if a delivery-context "hybrid" + Zoom both appear in first 2000 chars
    # Requires "hybrid course/class/delivery/..." context — not "hybrid of case studies" etc.
    _header_2000 = t_lower[:2000]
    _hybrid_zoom_in_header = bool(_hybrid_delivery_re.search(_header_2000)) and bool(re.search(r'\bzoom\b', _header_2000))

    if class_section:
        if _has_zoom_class_phrase(class_section):
            return {"modality": "Online", "confidence": 0.90, "evidence": ["class meets on Zoom/Teams/Webex"]}
        if _has_physical_room_phrase(class_section):
            return {"modality": "In-Person", "confidence": 0.90, "evidence": ["class meets in physical room"]}
        # "face to face" in class section: In-Person if no strong online cues (asynchronous alone is not enough)
        if re.search(r"(?i)\bface[-\s]?to[-\s]?face\b", class_section) and not re.search(r"(?i)\b(online|zoom|remote)\b", class_section):
            return {"modality": "In-Person", "confidence": 0.88, "evidence": ["class meets face to face"]}

    # Delivery method in header
    header_1000 = t_lower[:HEADER_SEARCH_LIMIT_1000]
    if re.search(r"(?i)(?:delivery|modality|format|mode)\s*[:\-]?\s*(?:online|asynchronous|synchronous online)", header_1000):
        return {"modality": "Online", "confidence": 0.92, "evidence": ["delivery method states online"]}

    # Physical meeting room in header
    header_600 = t_lower[:HEADER_SEARCH_LIMIT_600]
    meeting_match = re.search(rf"(?i)\b(meets?|meeting)\b.*\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", header_600)
    if meeting_match:
        office_in_header = "office" in header_600[max(0, meeting_match.start() - CONTEXT_OFFSET_50) : meeting_match.end() + CONTEXT_OFFSET_150]
        if not office_in_header and not _hybrid_in_header:
            return {"modality": "In-Person", "confidence": 0.92, "evidence": ["header shows physical meeting room"]}

    # In-person in header
    if re.search(r"(?i)\bin[ -]?person\b", header_600) and "office" not in header_600 and not _hybrid_in_header:
        return {"modality": "In-Person", "confidence": 0.90, "evidence": ["header says in person"]}

    # Physical room outside office hours
    non_office = t_lower.replace(office_section, "") if office_section else t_lower
    if (re.search(rf"\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", non_office)
            and not _hybrid_in_header and not _hybrid_zoom_in_header):
        # Exclude "office location/address/room" context and year-like numbers (e.g. "Lab Summer 2025")
        match = re.search(rf"\b({BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", non_office)
        if match:
            matched_text = match.group(0)
            ctx = non_office[max(0, match.start()-60):match.end()+30]
            is_office_ctx = bool(re.search(r'(?i)office\s+(?:location|address|room)\b', ctx))
            is_year = bool(re.search(r'\b(?:19|20)\d{2}\b', matched_text))
            if not is_office_ctx and not is_year:
                return {"modality": "In-Person", "confidence": 0.90, "evidence": ["physical room outside office hours"]}
    
    # Day/time schedule without online cues
    if re.search(DAYS_TOKEN, non_office) and re.search(TIME_TOKEN, non_office) and not re.search(
        r"\b(online|zoom|microsoft\s*teams|webex|remote)\b", non_office
    ) and "hybrid" not in header_1500:
        return {"modality": "In-Person", "confidence": 0.86, "evidence": ["day/time schedule with no online cues"]}
    
    # ================================================================
    # PHASE 3: Asynchronous detection
    # ================================================================
    
    if "asynchronous" in t_lower:
        async_position = t_lower.find("asynchronous")
        snippet = t_lower[max(0, async_position - CONTEXT_OFFSET_220) : async_position + CONTEXT_OFFSET_220]
        
        # Filter out bad contexts
        bad_context = [
            "tutoring", "writing lab", "writing center", "owl",
            "support service", "recorded lectures", "temporary",
            "accommodations", "miss class",
        ]
        if not any(b in snippet for b in bad_context):
            if any(w in snippet for w in [
                "online", "remote", "delivered", "format", "course is",
                "meets online", "delivery",
                "ol classes", "ol discussion",  # "OL" abbreviation for Online
            ]):
                if not any(w in snippet for w in ["meets in", "classroom", "in person", "on campus"]):
                    return {"modality": "Online", "confidence": 0.88, "evidence": ["asynchronous online delivery"]}
    
    # ================================================================
    # PHASE 4: Scoring system (soft signals)
    # ================================================================
    
    score_online = 0.0
    score_hybrid = 0.0
    score_inperson = 0.0
    
    # Online patterns with weights
    online_patterns = [
        (r"(?i)\bcourse\s+(?:is\s+)?(?:delivered|offered|taught)\s+online\b", 3.5),
        (r"(?i)\bonline\s+(?:course|format|delivery|instruction|modality)\b", 3.0),
        (r"(?i)\bsynchronous\s+online\b", 3.2),
        (r"(?i)\basynchronous\s+(?:course|format|delivery)\b", 3.2),
        (r"(?i)\bremote\s+(?:course|instruction|learning)\b", 2.5),
        (r"(?i)\bvirtual\s+course\b", 2.5),
        (r"(?i)\bclass\s+meets?\s+(?:on|via)\s+(?:zoom|microsoft\s*teams|teams|webex)\b", 3.5),
        (r"(?i)\bdelivered\s+(?:entirely\s+)?(?:online|remotely|asynchronously)\b", 3.5),
    ]
    
    # Irrelevant contexts to ignore
    irrelevant_online_contexts = [
        "textbook online", "materials online", "resources online",
        "available online", "posted online", "submit online", "canvas online"
    ]
    
    for pat, w in online_patterns:
        match = re.search(pat, t_lower)
        if match:
            match_start = match.start()
            match_context = t_lower[max(0, match_start - 30):match.end() + 30]
            if not any(ctx in match_context for ctx in irrelevant_online_contexts):
                score_online += w
                evidence.append("online_pattern_match")
    
    # Zoom in header (skip zoom occurrences that are just URLs / contact info links)
    first_1500 = t_lower[:HEADER_SEARCH_LIMIT_1500]
    zoom_position = first_1500.find("zoom")
    if zoom_position != -1:
        near = first_1500[max(0, zoom_position - CONTEXT_OFFSET_60) : zoom_position + CONTEXT_OFFSET_60]
        is_url_zoom = bool(re.search(r'https?://[^\s]*zoom', near))
        is_contact_zoom = bool(re.search(r'(?i)(join\s+from|personal\s+meeting\s+room|zoom\s*:\s*https?)', near))
        if "office" not in near and "counseling" not in near and "support" not in near:
            if not is_url_zoom and not is_contact_zoom:
                if any(ctx in near for ctx in ["meet", "class", "course", "location", "delivery"]):
                    score_online += 2.0
    
    # In-person patterns with weights
    inperson_patterns = [
        (rf"(?i)\b(?:class|course|lecture)\s+(?:meets?|is held|location).*(?:{BUILDING_WORDS})\b", 3.0),
        (rf"(?i)\b(?:location|where)\b.*\b(?:{BUILDING_WORDS})\b.*\b[A-Za-z]?\d{{2,4}}\b", 2.7),
        (r"(?i)\bin[-\s]?person\s+(?:class|course|instruction)\b", 2.5),
        (r"(?i)\bon\s+campus\s+(?:course|class)\b", 2.0),
        (r"(?i)\bclassroom\s+instruction\b", 2.0),
        (rf"(?i)\b[A-Z][a-zA-Z]+(?:\s+(?:Hall|Building|Lab))?\s+[A-Za-z]?\d{{2,4}}\b", 2.1),
        (r"(?i)\btaking\s+attendance\b", 1.5),
        (r"(?i)\barrive\s+late\s+to\s+class\b", 1.3),
        (r"(?i)\bleave\s+early\s+from\s+class\b", 1.3),
        (r"(?i)\bneed\s+to\s+be\s+here\b", 1.5),
        (r"(?i)\bin[ -]?person\b", 2.0),
        (r"(?i)\bon[- ]site\b", 1.8),
        (r"(?i)face[- ]to[- ]face\b", 2.0),
        (r"(?i)\b(outdoor|field)\s+(meetings?|sessions?|labs?)\b", 2.0),
        (r"(?i)\battendance\s+(?:is\s+)?required\b", 2.0),
        (r"(?i)\bbring\s+(?:your\s+)?textbook\s+to\s+class\b", 1.5),
        (r"(?i)\btake\s+notes\s+(?:in|during)\s+class\b", 1.2),
    ]
    
    # Filter out support services and course codes
    support_service_contexts = [
        "accessibility", "counseling", "tutoring", "writing center",
        "library", "financial aid", "registrar", "advisement", "student services",
        "wellness", "health services"
    ]
    
    course_code_patterns = [
        r"\bcomp\s*\d", r"\bmath\s*\d", r"\bbms\s*\d", r"\bphys\s*\d",
        r"\banth\s*\d", r"\bpsyc\s*\d", r"\bbiol\s*\d", r"\bcmn\s*\d",
        r"\bnsia\s*\d", r"\bcredit", r"\bcrn\s*:",
        # Subject / course codes (2-5 uppercase letters + digits)
        r"\b[A-Z]{2,5}\s*\d{3,}\b",
        # Month names (dates like "June 23", "February 10")
        r"\b(?:january|february|march|april|june|july|august|september|october|november|december)\b",
        # Week labels ("Week 10", "Week 11")
        r"\bweek\s*\d",
        # Instructor office context ("Office Location: Room X")
        r"office\s+(?:location|address|room)\b",
    ]
    
    for pat, w in inperson_patterns:
        match = re.search(pat, t_lower)
        if match:
            match_start = match.start()
            match_context = t_lower[max(0, match_start - 50):match.end() + 50]
            wider_context = t_lower[max(0, match_start - 200):match_start]

            is_course_code = any(re.search(code_pat, match_context) for code_pat in course_code_patterns)
            # Exclude "in person/in-person" that's about office hours, not class meetings
            is_office_hours_ctx = bool(re.search(r'office\s+hours?', wider_context, re.IGNORECASE))

            if (not any(ctx in match_context for ctx in support_service_contexts)
                    and not is_course_code and not is_office_hours_ctx):
                score_inperson += w
                evidence.append("inperson_pattern_match")
    
    # Check for hybrid (both online and in-person signals)
    if score_online > MIN_SCORE_THRESHOLD_ONLINE and score_inperson > MIN_SCORE_THRESHOLD_INPERSON:
        score_hybrid = max(score_hybrid, (score_online + score_inperson) * HYBRID_SCORE_MULTIPLIER)
    
    # Adjust scores if office hours but no class location
    if office_section and score_inperson > 0:
        room_in_class = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", class_section))
        room_in_office = bool(re.search(rf"(?i)\b{BUILDING_WORDS}\b.*\b[A-Za-z]?\d{{2,4}}\b", office_section))
        if room_in_office and not room_in_class:
            score_inperson = max(0.0, score_inperson - INPERSON_PENALTY)
            evidence.append("reduced_inperson_office_hours_only")
            if score_online > MIN_SCORE_THRESHOLD_ONLINE_BOOST:
                score_online += ONLINE_BOOST
                evidence.append("boosted_online_no_class_location")
    
    # ================================================================
    # FINAL DECISION
    # ================================================================
    
    scores = {"Online": score_online, "Hybrid": score_hybrid, "In-Person": score_inperson}
    max_score = max(scores.values())
    
    # Return Unknown if no significant evidence
    if max_score < 2.0:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["no clear modality indicators"]}
    
    modality = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(max_score / total, 2) if total > 0 else MIN_CONFIDENCE_THRESHOLD
    confidence = max(confidence, MIN_CONFIDENCE_THRESHOLD)
    
    # Return Unknown if confidence too low
    if confidence < 0.60:
        return {"modality": "Unknown", "confidence": 0.0, "evidence": ["weak or ambiguous modality signals"]}
    
    return {
        "modality": modality,
        "confidence": confidence,
        "evidence": evidence[:4] if evidence else [f"{modality.lower()} indicators found"],
    }

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def quick_course_metadata(text: str) -> Dict[str, str]:
    """Extract basic course info (course, instructor, email) from syllabus"""
    t = normalize_syllabus_text(text)
    
    # Extract email
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t)
    email = email_match.group(0) if email_match else ""
    
    # Extract instructor
    instructor_match = re.search(r"(?im)^(?:instructor|professor|lecturer)[:\s-]+(.{3,80})$", t)
    instructor = (instructor_match.group(1).strip() if instructor_match else "")
    if not instructor:
        by_match = re.search(r"(?im)^(?:by)[:\s-]+(.{3,80})$", t)
        instructor = by_match.group(1).strip() if by_match else ""
    
    # Extract course
    course_match = re.search(r"(?im)^(?:course|class)\s*(?:title|name|code)?[:\s-]+(.{3,80})$", t)
    course = (course_match.group(1).strip() if course_match else "")
    if not course:
        code_match = re.search(r"\b[A-Z]{2,}\s?\d{3,}[A-Z-]*\b", t[:HEADER_SEARCH_LIMIT_400])
        course = code_match.group(0) if code_match else ""
    
    return {"course": course, "instructor": instructor, "email": email}


def format_modality_card(result: Dict[str, object], meta: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Format detection result for API/UI display"""
    meta = meta or {}
    label = str(result.get("modality", "Unknown"))
    conf = float(result.get("confidence") or 0.0)
    evidence = result.get("evidence") or []
    
    status = "PASS" if label != "Unknown" else "FAIL"
    message = f"{label} modality detected" if label != "Unknown" else "Detected delivery"
    
    return {
        "status": status,
        "heading": "Course Delivery",
        "message": message,
        "label": label,
        "confidence": round(conf, 2),
        "evidence": list(evidence)[:5],
    }


def detect_modality(text: str) -> Tuple[str, str]:
    """Simple wrapper - returns (label, evidence_string) for test runner compatibility"""
    res = detect_course_delivery(text)
    label = res.get("modality", "Unknown")
    ev = res.get("evidence") or []
    return label, " | ".join(ev[:3])