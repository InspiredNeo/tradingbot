import os
import requests as req
from dotenv import load_dotenv
from google import genai
import groq as groq_lib

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = groq_lib.Groq(api_key=os.getenv("GROQ_API_KEY"))
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_ai_text(prompt, max_tokens=1000):
    """Try Gemini -> Groq -> Cerebras -> OpenRouter -> Ollama."""
    # 1. Gemini
    try:
        result = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        if result.text:
            return result.text
    except Exception:
        pass

    # 2. Groq
    try:
        result = groq_client.chat.completions.create(
            model="llama-3.2-3b-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        text = result.choices[0].message.content
        if text:
            return text
    except Exception:
        pass

    # 3. Cerebras
    try:
        resp = req.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_KEY}"},
            json={
                "model": "llama3.1-8b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=30
        )
        text = resp.json()["choices"][0]["message"]["content"]
        if text:
            return text
    except Exception:
        pass

    # 4. OpenRouter
    try:
        resp = req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=30
        )
        text = resp.json()["choices"][0]["message"]["content"]
        if text:
            return text
    except Exception:
        pass

    # 5. Ollama (local)
    try:
        resp = req.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=60
        )
        text = resp.json().get("response", "")
        if text:
            return text
    except Exception:
        pass

    return ""
