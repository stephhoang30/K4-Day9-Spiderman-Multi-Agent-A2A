"""Client LLM dùng chung cho các agent có gọi LLM, với fallback qua nhiều provider.

Mỗi provider dùng model OpenAI-compatible ≤10B tham số (README mục 9). Thử lần
lượt theo PROVIDERS: tối đa 3 lần/provider (tenacity retry), nếu hết attempt mà
vẫn lỗi mới chuyển sang provider kế tiếp — không bao giờ raise ra ngoài để 1
provider sập không làm hỏng cả case (narrate() luôn trả về string).

LLM chỉ tạo note diễn giải cho trace — không bao giờ được dùng để quyết định
số liệu/ID (xem core/policy_rules.py).
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

PROVIDERS = [
    # 3 model OpenRouter xếp theo độ mạnh giảm dần (đã test gọi API thật, không
    # dựa vào trang catalog vì nhiều model liệt kê trên web nhưng trả 404 khi gọi
    # thật — VD google/gemma-2-9b-it, mistralai/mistral-7b-instruct-v0.3,
    # qwen/qwen3.5-9b bị treo vô hạn). Hết cả 3 mới rớt sang provider khác.
    {
        "name": "openrouter-qwen2.5-7b",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "qwen/qwen-2.5-7b-instruct",
        "param_size": "7B",
    },
    {
        "name": "openrouter-llama3.1-8b",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.1-8b-instruct",
        "param_size": "8B",
    },
    {
        "name": "openrouter-llama3.2-3b",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.2-3b-instruct",
        "param_size": "3B",
    },
    {
        "name": "nvidia_nim-llama3.1-8b",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_NIM_API_KEY",
        "model": "meta/llama-3.1-8b-instruct",
        "param_size": "8B",
    },
    {
        "name": "groq-llama3.1-8b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
        "param_size": "8B",
    },
]

MAX_ATTEMPTS_PER_PROVIDER = 3
REQUEST_TIMEOUT_SECONDS = 15  # tránh treo vô thời hạn nếu 1 provider không phản hồi

_clients: dict[str, ChatOpenAI] = {}


def _get_client(provider: dict, temperature: float) -> ChatOpenAI | None:
    api_key = os.getenv(provider["api_key_env"])
    if not api_key:
        return None
    cache_key = f"{provider['name']}:{temperature}"
    if cache_key not in _clients:
        _clients[cache_key] = ChatOpenAI(
            model=provider["model"],
            base_url=provider["base_url"],
            api_key=api_key,
            temperature=temperature,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    return _clients[cache_key]


@retry(
    stop=stop_after_attempt(MAX_ATTEMPTS_PER_PROVIDER),
    wait=wait_exponential(multiplier=1, min=1, max=8),
)
def _invoke(client: ChatOpenAI, system_prompt: str, user_prompt: str) -> str:
    response = client.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )
    return response.content.strip()


def narrate(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    errors = []
    for provider in PROVIDERS:
        client = _get_client(provider, temperature)
        if client is None:
            continue
        try:
            return _invoke(client, system_prompt, user_prompt)
        except Exception as exc:
            errors.append(f"{provider['name']}: {exc}")
            continue
    return f"[llm_unavailable: {' | '.join(errors) if errors else 'no provider API key configured'}]"
