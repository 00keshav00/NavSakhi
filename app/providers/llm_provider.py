from typing import Dict, Any
from app.providers.base import BaseLLMProvider
from app.api.exceptions import ProviderNotConfiguredError

class LLMProvider(BaseLLMProvider):
    """
    LLM Wrapper that interfaces with external AI models (OpenAI, Gemini, etc.).
    Currently acts as an extension point, as per architecture rules, raising ProviderNotConfiguredError.
    """
    def __init__(self, model_name: str = "default_model", temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature

    async def generate(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Executes a prompt against the configured LLM provider.
        """
        # Per strict architectural guidelines, real LLM integrations are NOT present.
        # This wrapper serves as the unified injection point for future phases.
        raise ProviderNotConfiguredError("LLMProvider")
