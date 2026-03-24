from groq import Groq
import os

client = None
HARDCODED_GROQ_API_KEY = "your key"  # paste key here if env var is not working
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


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

Return ONLY the exact preferred-contact value from the text.
Examples of valid outputs:
- christine.andrews@unh.edu
- Canvas Inbox
- Office hours after class
- (603) 555-1234

If no preferred contact is explicitly stated, return exactly:
Not found

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
        preferred = _normalize_preferred_contact(result)

        return {
            "preferred": preferred,
            "found": preferred is not None,
            "confidence": 0.9 if preferred is not None else 0.0
        }

    except Exception as e:
        return {
            "preferred": None,
            "found": False,
            "confidence": 0.0,
            "error": str(e)
        }