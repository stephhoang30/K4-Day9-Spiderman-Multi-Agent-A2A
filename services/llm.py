import os
import re
from typing import Optional

from openai import OpenAI
import config

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url=config.BASE_URL,
)


def generate_completion(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:

    model = model or config.MODEL_NAME
    temperature = config.TEMPERATURE if temperature is None else temperature
    max_tokens = config.MAX_TOKENS if max_tokens is None else max_tokens

    limit = getattr(config, "MODEL_PARAM_LIMIT_BILLIONS", None)
    if limit is not None:
        m = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]", model)
        if m and float(m.group(1)) > float(limit):
            raise RuntimeError(
                f"{model} exceeds {limit}B parameter limit."
            )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": "You are a deterministic policy engine. Return ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "EC Multi-Agent"
            },
        )

        return response.choices[0].message.content or ""

    except Exception as e:
        print(f"OpenRouter Error: {e}")
        return ""