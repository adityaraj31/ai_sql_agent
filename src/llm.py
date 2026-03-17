from langchain_openai import ChatOpenAI
from src.config import OPENROUTER_API_KEY, LLM_MODEL_NAME

_llm_instance = None


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Get or create a singleton LLM instance using OpenRouter."""
    global _llm_instance
    if _llm_instance is None:
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
        _llm_instance = ChatOpenAI(
            model=LLM_MODEL_NAME,
            temperature=temperature,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://ai-sql-agent.local",
                "X-Title": "AI SQL Agent",
            },
        )
    return _llm_instance


def reset_llm():
    """Reset the LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None
