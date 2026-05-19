import httpx
import re
import time
from typing import List, Dict, Optional, Any
from config import get_settings

settings = get_settings()

# ─── Provider config cache (invalidated after 30s) ───────────────
_provider_cache: Dict[str, Any] = {"config": None, "expires": 0.0}

def invalidate_provider_cache():
    _provider_cache["expires"] = 0.0

async def _load_provider_config() -> Dict:
    """Read active AI provider config from system_settings table (cached 30s)."""
    if _provider_cache["config"] and time.monotonic() < _provider_cache["expires"]:
        return _provider_cache["config"]
    try:
        from database import AsyncSessionLocal
        from models import SystemSetting
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            keys = ["ai_provider", "deepseek_api_key", "deepseek_model", "deepseek_base_url"]
            rows = (await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))).scalars().all()
            kv = {r.key: r.value for r in rows}
    except Exception:
        kv = {}
    config = {
        "provider":          kv.get("ai_provider",        "ollama"),
        "deepseek_api_key":  kv.get("deepseek_api_key",   ""),
        "deepseek_model":    kv.get("deepseek_model",     "deepseek-chat"),
        "deepseek_base_url": kv.get("deepseek_base_url",  "https://api.deepseek.com/v1"),
    }
    _provider_cache["config"]  = config
    _provider_cache["expires"] = time.monotonic() + 30
    return config

SYSTEM_PROMPT = """You are MSX Smart Assistant for www.msx.om — the Muscat Stock Exchange of Oman.

STRICT RULES — YOU MUST FOLLOW THESE:

1. ONLY use data provided in the context below. NEVER invent or guess numbers.
2. If a specific numeric field (like Non-Omani %, GCC %, Foreign %, price) is NOT in the context, say it is not available and suggest visiting the MSX website for the latest data.
3. For board/management information (Chairman, Directors, Secretary, Members): if names appear anywhere in the context, report them directly — do NOT say this data is unavailable.
4. NEVER say "Insert value" or use placeholder text.
5. NEVER make up percentages, prices, ownership figures, or names.
6. When data IS provided in the context, use the EXACT values — do not paraphrase names.
7. Support both Arabic and English questions.
8. Be concise and professional.

End every reply with one of:
[CLASSIFICATION: general_inquiry]
[CLASSIFICATION: support]
[CLASSIFICATION: sales]
[CLASSIFICATION: complaint]"""


def _select_model(context: Optional[str], message: str, provider_cfg: Optional[Dict] = None) -> str:
    if provider_cfg and provider_cfg.get("provider") == "deepseek":
        return provider_cfg.get("deepseek_model", "deepseek-chat")
    if context and any(w in context.lower() for w in ['price', 'volume', 'trade', 'market']):
        return settings.localai_model_analysis
    if len(message.split()) <= 5:
        return settings.localai_model_fast
    return settings.localai_model


_MAX_CONTEXT_CHARS = 6000  # keep prompt manageable for the 7b model


def _truncate_context(context: str) -> str:
    if len(context) <= _MAX_CONTEXT_CHARS:
        return context
    truncated = context[:_MAX_CONTEXT_CHARS]
    # cut at last newline to avoid mid-sentence truncation
    last_nl = truncated.rfind("\n")
    if last_nl > _MAX_CONTEXT_CHARS // 2:
        truncated = truncated[:last_nl]
    return truncated + "\n\n[... context truncated for length ...]"


async def _call_model(model: str, messages: List[Dict], provider_cfg: Optional[Dict] = None) -> str:
    cfg     = provider_cfg or {}
    use_ds  = cfg.get("provider") == "deepseek"
    base_url = cfg.get("deepseek_base_url", "https://api.deepseek.com/v1") if use_ds else settings.localai_base_url
    api_key  = cfg.get("deepseek_api_key", "") if use_ds else ""

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 600,
        "stream": False,
    }
    if not use_ds:
        payload["stop"] = ["</s>", "<|eot_id|>", "<|end_of_text|>"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = httpx.Timeout(float(settings.localai_timeout), connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
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
                f"{_truncate_context(context)}\n"
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

    provider_cfg = await _load_provider_config()
    model        = _select_model(context, user_message, provider_cfg)
    provider     = provider_cfg.get("provider", "ollama")
    print(f"🔄 [{provider}:{model}] | context={'yes' if context else 'no'}")

    try:
        content = await _call_model(model, messages, provider_cfg)
        print(f"✅ Reply: {content[:100]}")
        return {"content": content, "model": model, "provider": provider}
    except Exception as e:
        print(f"⚠️ [{model}] failed: {e}")
        # Fallback only makes sense for Ollama (DeepSeek has one model endpoint)
        if provider == "ollama":
            fallback = settings.localai_model_fallback
            if fallback != model:
                try:
                    content = await _call_model(fallback, messages, provider_cfg)
                    return {"content": content, "model": fallback, "provider": provider}
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
