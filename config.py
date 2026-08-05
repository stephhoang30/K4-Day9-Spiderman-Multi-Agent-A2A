from dotenv import load_dotenv
load_dotenv()

BASE_URL = "https://openrouter.ai/api/v1"

# Có thể dùng model free nếu có sẵn
MODEL_NAME = "nvidia/nemotron-nano-9b-v2:free"
# hoặc model trả phí:
# MODEL_NAME = "qwen/qwen3-8b"

TEMPERATURE = 0.0
MAX_TOKENS = 1024
MODEL_PARAM_LIMIT_BILLIONS = 10