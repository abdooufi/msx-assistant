import httpx
import re
from typing import List, Dict, Optional
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are MSX Smart Assistant for www.msx.om — the Muscat Stock Exchange of Oman.

STRICT RULES — YOU MUST FOLLOW THESE:

1. ONLY use data provided in the context below. NEVER invent or guess numbers.
2. If a specific field (like Non-Omani %, GCC %, Foreign %) is NOT in the context, say:
   "This data is not available in my current data. Please visit https://www.msx.om/snapshot.aspx?s=SYMBOL for the latest ownership details."
3. NEVER say "Insert value" or use placeholder text.
4. NEVER make up percentages, prices, or ownership figures.
5. When price data IS provided, use the EXACT numbers from the context.
6. Support both Arabic and English questions.
7. Be concise and professional.

End every reply with one of:
[CLASSIFICATION: general_inquiry]
[CLASSIFICATION: support]
[CLASSIFICATION: sales]
[CLASSIFICATION: complaint]"""


def _select_model(context: Optional[str], message: str) -> str:
    if context and any(w in context.lower() for w in ['price', 'volume', 'trade', 'market']):
        return settings.localai_model_analysis
    if len(message.split()) <= 5:
        return settings.localai_model_fast
    return settings.localai_model


async def _call_model(model: str, messages: List[Dict]) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 800,
        "stream": False,
        "stop": ["</s>", "<|eot_id|>", "<|end_of_text|>"],
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        r = await client.post(
            f"{settings.localai_base_url}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def query_localai(
    user_message: str,
    history: List[Dict],
    context: Optional[str] = None,
) -> Dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        messages.append({
            "role": "system",
            "content": (
                "=== REAL DATA FROM MSX DATABASE AND WEBSITE ===\n"
                f"{context}\n"
                "=== END OF DATA ===\n\n"
                "IMPORTANT: Use ONLY the numbers above. "
                "If a value is not listed above, say it is not available."
            )
        })
    else:
        messages.append({
            "role": "system",
            "content": (
                "No specific company data was found for this query. "
                "Answer using only general knowledge about MSX.om. "
                "Do NOT invent any specific numbers, percentages, or prices."
            )
        })

    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    model = _select_model(context, user_message)
    print(f"🔄 LocalAI [{model}] | context={'yes' if context else 'no'}")

    try:
        content = await _call_model(model, messages)
        print(f"✅ Reply: {content[:100]}")
        return {"content": content, "model": model}
    except Exception as e:
        print(f"⚠️ [{model}] failed: {e}")
        fallback = settings.localai_model_fallback
        if fallback != model:
            try:
                content = await _call_model(fallback, messages)
                return {"content": content, "model": fallback}
            except Exception as e2:
                print(f"⚠️ Fallback also failed: {e2}")
        raise


async def get_available_models() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{settings.localai_base_url}/models")
            return [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return []


def extract_classification(text: str) -> tuple[str, str]:
    pattern = r'\[CLASSIFICATION:\s*(\w+)\]'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        classification = match.group(1).lower()
        clean = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean, classification
    return text, "general_inquiry"


async def check_localai_health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.localai_base_url}/models")
            return r.status_code == 200
    except Exception:
        return False
