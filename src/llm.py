from langchain_groq import ChatGroq
from src.config import GROQ_API_KEY, LLM_MODEL_NAME

_llm_instance = None


def get_llm(temperature: float = 0) -> ChatGroq:
    """Get or create a singleton LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set")
        _llm_instance = ChatGroq(
            temperature=temperature,
            model=LLM_MODEL_NAME,
            api_key=GROQ_API_KEY,
        )
    return _llm_instance


def reset_llm():
    """Reset the LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None
