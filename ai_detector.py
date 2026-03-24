from groq import Groq
import os
import json
import re

client = None
HARDCODED_GROQ_API_KEY = "your key"  # paste key here if env var is not working
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
REASONING_DEBUG_FILE = "preferred_contact_reasoning.json"


def _has_strong_preference_signal(text: str) -> bool:
    low = (text or "").lower()
    signals = [
        "preferred contact method", "preferred method", "preferred way",
        "best way to reach", "best way to contact", "primary contact",
        "please contact me via", "contact me at", "email preferred"
    ]
    return any(s in low for s in signals)


def _post_filter_analysis(text: str) -> dict:
    low = (text or "").lower()
    has_email = any(k in low for k in ["email", "e-mail", "@"])
    has_phone = any(k in low for k in ["phone", "sms", "text", "mobile", "call"])
    has_equal_language = any(k in low for k in ["acceptable", "can", "may", "also", "other contact methods"])
    strong_preference_signal = _has_strong_preference_signal(low)

    # If response-time language clearly emphasizes one method, do not mark ambiguous.
    email_emphasis = bool(re.search(r"email[^\n\.]{0,100}(response|within|check)", low) or re.search(r"(response|within)\s+[^\n\.]{0,100}email", low))
    phone_emphasis = bool(re.search(r"(phone|sms|text)[^\n\.]{0,100}(response|within|check)", low) or re.search(r"(response|within)\s+[^\n\.]{0,100}(phone|sms|text)", low))
    response_time_tie_break = bool(email_emphasis ^ phone_emphasis)
    ambiguous_multi_method = (
        has_email and has_phone and has_equal_language and not strong_preference_signal and not response_time_tie_break
    )

    return {
        "has_email": has_email,
        "has_phone_or_sms": has_phone,
        "has_equal_language": has_equal_language,
        "strong_preference_signal": strong_preference_signal,
        "email_emphasis": email_emphasis,
        "phone_emphasis": phone_emphasis,
        "response_time_tie_break": response_time_tie_break,
        "ambiguous_multi_method": ambiguous_multi_method,
    }


def _normalize_preferred_contact(result: str):
    value = (result or "").strip()
    low = value.lower()
    if not value or "not found" in low:
        return None

    # Remove simple wrappers/prefixes from LLM output while keeping actual value
    for prefix in [
        "preferred contact method:",
        "preferred contact:",
        "preferred method:",
        "answer:",
    ]:
        if low.startswith(prefix):
            value = value[len(prefix):].strip()
            break

    value = value.strip("`\"' ")
    return value or None


def _parse_ai_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {
            "explicit_preferred": None,
            "inferred_preferred": None,
            "reasoning": "No model output.",
        }

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return {
        "explicit_preferred": None,
        "inferred_preferred": None,
        "reasoning": "Could not parse model JSON output.",
    }


def _write_reasoning_record(record: dict) -> None:
    try:
        with open(REASONING_DEBUG_FILE, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def detect_preferred_contact_ai(text: str) -> dict:
    try:
        global client
        if client is None:
            api_key = os.getenv("GROQ_API_KEY") or HARDCODED_GROQ_API_KEY
            if not api_key:
                return {
                    "preferred": None,
                    "found": False,
                    "confidence": 0.0,
                    "error": "GROQ_API_KEY not configured (env or HARDCODED_GROQ_API_KEY)"
                }
            client = Groq(api_key=api_key)

        prompt = f"""
    Extract the instructor's preferred contact method from this syllabus.

    Be reasonably generous, but not overly strict.

    Set found=true if ANY of these are true:
    1) A method is explicitly preferred (e.g., preferred, best way, primary method), OR
     2) One or two methods are listed, and one is clearly emphasized as the main channel
         (for example, response-time commitment tied to one method, stronger wording,
         or the other method is only described as acceptable/secondary).

    Set found=false when contact methods are only listed and there is no clear preference/emphasis.

        Important guardrails:
        - Do NOT treat simple contact listing alone (e.g., "Instructor ... email: ...") as preferred.
        - Do NOT treat general response-time policy alone as preferred unless it clearly identifies
            one method as the main/recommended method over others.
                - If email and phone/SMS are both described as acceptable with no clear priority, return found=false.
                - If response-time language is clearly tied to one method (e.g., email checked/responded within 24 hours),
                    you may infer that method as preferred unless another method is equally emphasized.

    When found=true, return the EXACT value from the syllabus (email address, phone number,
    office-hours phrase, Canvas phrase, etc.), not a generic label.

        Return JSON only in this exact shape:
        {{
            "explicit_preferred": "value or null",
            "inferred_preferred": "value or null",
            "reasoning": "One sentence explaining your inference."
        }}

    Text:
    {text[:12000]}
    """

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        result = response.choices[0].message.content.strip()
        parsed = _parse_ai_json(result)
        explicit_preferred = _normalize_preferred_contact(parsed.get("explicit_preferred"))
        inferred_preferred = _normalize_preferred_contact(parsed.get("inferred_preferred"))
        reasoning = (parsed.get("reasoning") or "").strip() or "No reasoning provided."

        preferred = explicit_preferred or inferred_preferred
        found = preferred is not None
        analysis = _post_filter_analysis(text)
        post_filter_applied = False
        post_filter_reason = "Not applied"

        if found and analysis.get("ambiguous_multi_method"):
            preferred = None
            found = False
            post_filter_applied = True
            post_filter_reason = (
                "Rejected as ambiguous: both email and phone/SMS appear acceptable without clear priority."
            )

        _write_reasoning_record(
            {
                "model": MODEL_NAME,
                "llm_output": {
                    "explicit_preferred": explicit_preferred,
                    "inferred_preferred": inferred_preferred,
                    "reasoning": reasoning,
                },
                "post_filter_checks": analysis,
                "post_filter_applied": post_filter_applied,
                "post_filter_reason": post_filter_reason,
                "final_decision": {
                    "preferred": preferred,
                    "found": found,
                    "confidence": 0.9 if found else 0.0,
                },
                "human_summary": (
                    f"Model suggested explicit='{explicit_preferred}' inferred='{inferred_preferred}'. "
                    f"Post-filter applied={post_filter_applied}. Final preferred='{preferred}' found={found}."
                ),
            }
        )

        return {
            "preferred": preferred,
            "found": found,
            "confidence": 0.9 if found else 0.0,
            "reasoning": reasoning,
            "explicit_preferred": explicit_preferred,
            "inferred_preferred": inferred_preferred,
        }

    except Exception as e:
        return {
            "preferred": None,
            "found": False,
            "confidence": 0.0,
            "error": str(e)
        }
