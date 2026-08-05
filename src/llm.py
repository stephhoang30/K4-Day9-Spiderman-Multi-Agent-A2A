"""Goi model <=10B. Ten model dat trong code de cham duoc (README.md muc 9.4).

Secret (neu dung provider co API key) doc tu .env, va .env khong duoc commit.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Ten model khai o day, KHONG dat trong .env. Phai <= 10B tham so.
MODEL = "qwen3.5:4b"
MODEL_PARAMETER_SIZE = "4.7B"

DEFAULT_TEMPERATURE = 0.0
TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "60"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv():
    """Doc .env neu co. Khong dung thu vien ngoai, khong ghi de bien da co."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")


def _post(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(system: str, user: str, temperature: float = DEFAULT_TEMPERATURE) -> str | None:
    """Tra ve text cua model, hoac None neu goi that bai.

    None la duong lui hop le: agent goi ham nay phai chay tiep bang nhanh xac dinh.
    """
    if os.environ.get("LLM_ENABLED", "1") == "0":
        return None
    try:
        if PROVIDER == "ollama":
            body = _post(
                f"{OLLAMA_HOST}/api/chat",
                {
                    "model": MODEL,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": temperature},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            return (body.get("message") or {}).get("content")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        body = _post(
            f"{OPENAI_BASE_URL}/chat/completions",
            {
                "model": MODEL,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return body["choices"][0]["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, OSError):
        return None


def extract_json(text: str | None):
    """Model <=10B hay tra JSON kem mot cau mo dau. Cat lay phan trong { } hoac [ ]."""
    if not text:
        return None
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _ping():
    reply = chat("Tra loi dung mot tu.", "Tra loi: pong")
    ok = reply is not None
    print(f"provider={PROVIDER} model={MODEL} size={MODEL_PARAMETER_SIZE} ok={ok}")
    if ok:
        print(f"reply={reply.strip()[:60]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_ping() if "--ping" in sys.argv else 0)
