import os
from dotenv import load_dotenv
from google import genai
import groq as groq_lib

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = groq_lib.Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_ai_text(prompt, max_tokens=1000):
    """Try Gemini -> Groq -> Ollama. Returns text or empty string."""
    try:
        result = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        return result.text
    except Exception:
        pass
    try:
        result = groq_client.chat.completions.create(
            model="llama-3.2-3b-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return result.choices[0].message.content
    except Exception:
        pass
    try:
        import requests as req
        resp = req.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=60
        )
        return resp.json().get("response", "")
    except Exception:
        pass
    return ""
