"""Shared helpers for the bonus pipeline: env loading, Gemini REST calls (embedding, generation, vision), pgvector.

Real APIs only: any failure raises (no mock/random fallback). Standard library + psycopg.
"""
import base64
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bonus" / "data"
DAY6_ENV = Path("E:/VinUni/K5-L3B-DAY06-TrinhNgocNinh-2A202603996-DataIngestion/starter/.env")
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
DEFAULT_DB = "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab"
CORPUS = "who-whs-2023"
RETRY_STATUS = {429, 500, 502, 503, 504}


class ApiError(RuntimeError):
    pass


def load_env():
    """Load KEY=VALUE pairs from the Day 7 .env, else the Day 6 starter .env (never printed)."""
    for path in (ROOT / ".env", DAY6_ENV):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    v = v.strip().strip("'\"")
                    if v and not os.environ.get(k.strip()):
                        os.environ[k.strip()] = v
    if not os.environ.get("GEMINI_API_KEY"):  # embeddings always use Gemini (the index was built with gemini-embedding-001)
        raise ApiError("GEMINI_API_KEY trống: điền vào .env (Day 7) hoặc starter/.env (Day 6).")
    if provider() == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        raise ApiError("LLM_PROVIDER=openrouter nhưng OPENROUTER_API_KEY trống: điền vào .env của Day 7.")


def provider():
    """Which service answers generate(): 'gemini' (default) or 'openrouter' (LLM_PROVIDER=openrouter). Embeddings stay on Gemini."""
    return os.environ.get("LLM_PROVIDER", "gemini").strip().lower()


def default_model():
    return "google/gemini-3.5-flash-lite" if provider() == "openrouter" else "gemini-3.5-flash-lite"


STATS = {"api_calls": 0, "retries": 0, "errors": [], "prompt_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
_last_call = {"t": 0.0}
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _post(url, body, timeout=120, min_interval=None, max_retries=6, headers=None):
    if min_interval is None:  # free-tier keys are limited per minute; GEMINI_MIN_INTERVAL spaces the calls out
        min_interval = float(os.environ.get("GEMINI_MIN_INTERVAL", "0.7"))
    data = json.dumps(body).encode("utf-8")
    last = "unknown"
    for attempt in range(max_retries + 1):
        wait = min_interval - (time.monotonic() - _last_call["t"])
        if wait > 0:
            time.sleep(wait)
        _last_call["t"] = time.monotonic()
        req = urllib.request.Request(url, data=data, method="POST", headers=headers or {
            "Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            STATS["api_calls"] += 1
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            last = f"HTTP {e.code}: {detail}"
            if e.code not in RETRY_STATUS:
                break
            delay = min(2 ** attempt * 4, 65)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"{type(e).__name__}: {e}"
            delay = min(2 ** attempt * 4, 65)
        STATS["retries"] += 1
        STATS["errors"].append(last[:200])
        if attempt < max_retries:
            time.sleep(delay)
    raise ApiError(f"Gemini API lỗi: {last}")


def embed(text, task):
    """task = RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY. Returns an L2-normalised 768-dim vector."""
    if not text.strip():
        raise ApiError("Không embed chuỗi rỗng")
    data = _post(f"{API_ROOT}/models/{EMBED_MODEL}:embedContent", {
        "model": f"models/{EMBED_MODEL}", "content": {"parts": [{"text": text}]},
        "taskType": task, "outputDimensionality": EMBED_DIM})
    values = data.get("embedding", {}).get("values")
    if not values or len(values) != EMBED_DIM:
        raise ApiError(f"Embedding không hợp lệ: {str(data)[:200]}")
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm == 0:
        raise ApiError("Vector norm = 0")
    return [v / norm for v in values]


def generate(model, prompt, image_path=None, json_mode=False, temperature=0.0, max_tokens=2048, thinking_budget=None):
    """One text-generation call (optionally with one PNG). Returns the text of the first candidate.
    LLM_PROVIDER=openrouter sends text-only prompts to OpenRouter; vision (image_path) always goes to Gemini."""
    if provider() == "openrouter" and image_path is None:
        return _generate_openrouter(model, prompt, json_mode, temperature, max_tokens, thinking_budget)
    parts = []
    if image_path is not None:
        parts.append({"inline_data": {"mime_type": "image/png",
                                      "data": base64.b64encode(Path(image_path).read_bytes()).decode("ascii")}})
    parts.append({"text": prompt})
    cfg = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if json_mode:
        cfg["responseMimeType"] = "application/json"
    if thinking_budget is not None:
        # 2.x models take a token budget; 3.x models reject it (HTTP 400) and take a level instead
        if model.startswith("gemini-2"):
            cfg["thinkingConfig"] = {"thinkingBudget": thinking_budget}
        else:
            cfg["thinkingConfig"] = {"thinkingLevel": "minimal" if thinking_budget == 0 else "low"}
    data = _post(f"{API_ROOT}/models/{model}:generateContent", {"contents": [{"parts": parts}], "generationConfig": cfg})
    usage = data.get("usageMetadata", {})
    STATS["prompt_tokens"] += usage.get("promptTokenCount", 0)
    STATS["output_tokens"] += usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    try:
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
    except (KeyError, IndexError) as e:
        raise ApiError(f"Phản hồi không có nội dung: {str(data)[:300]}") from e


def _generate_openrouter(model, prompt, json_mode, temperature, max_tokens, thinking_budget):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature,
            "max_tokens": max_tokens, "usage": {"include": True}}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if thinking_budget is not None:
        body["reasoning"] = {"effort": "minimal" if thinking_budget == 0 else "low"}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"],
               "X-Title": "Day7 agentic RAG lab"}
    data = _post(OPENROUTER_URL, body, headers=headers)
    if "error" in data:  # OpenRouter can answer HTTP 200 with an error object
        raise ApiError(f"OpenRouter lỗi: {str(data['error'])[:300]}")
    usage = data.get("usage") or {}
    STATS["prompt_tokens"] += usage.get("prompt_tokens", 0)
    STATS["output_tokens"] += usage.get("completion_tokens", 0)
    STATS["cost_usd"] += float(usage.get("cost") or 0)
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ApiError(f"Phản hồi OpenRouter không có nội dung: {str(data)[:300]}") from e
    if not isinstance(text, str) or not text.strip():
        raise ApiError(f"OpenRouter trả nội dung rỗng (finish_reason={data['choices'][0].get('finish_reason')})")
    return text.strip()


def parse_order(raw, n):
    """Parse a rerank reply {"order": [...]}. Models sometimes wrap it in a one-element list: [{"order": [...]}]."""
    try:
        data = json.loads(raw)
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            data = data[0]
        return [int(i) for i in data["order"] if 0 <= int(i) < n]
    except (ValueError, KeyError, TypeError) as e:
        raise ApiError(f"rerank trả JSON không hợp lệ: {raw[:200]}") from e


def list_models():
    req = urllib.request.Request(f"{API_ROOT}/models?pageSize=200", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp).get("models", [])


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vec_literal(v):
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def connect():
    import psycopg
    return psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB))
