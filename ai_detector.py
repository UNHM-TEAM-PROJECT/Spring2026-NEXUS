from groq import Groq
import os

client = None


def detect_preferred_contact_ai(text: str) -> dict:
    try:
        global client
        if client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return {
                    "preferred": None,
                    "found": False,
                    "confidence": 0.0,
                    "error": "GROQ_API_KEY not configured"
                }
            client = Groq(api_key=api_key)

        prompt = f"""
Extract the instructor's preferred contact method from this syllabus.

Return ONLY one of:
- Email
- Canvas
- Office Hours
- Phone
- Not found

Text:
{text[:3000]}
"""

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        result = response.choices[0].message.content.strip()

        return {
            "preferred": None if result.lower() == "not found" else result,
            "found": result.lower() != "not found",
            "confidence": 0.9 if result.lower() != "not found" else 0.0
        }

    except Exception as e:
        return {
            "preferred": None,
            "found": False,
            "confidence": 0.0,
            "error": str(e)
        }