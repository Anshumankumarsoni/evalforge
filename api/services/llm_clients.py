"""LLM client wrappers for OpenAI, Anthropic Claude, and Google Gemini"""

import time
from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI, OpenAIError
from anthropic import AsyncAnthropic, APIError as AnthropicAPIError

from api.config import settings


# ============================================================
# BASE LLM CLIENT
# ============================================================

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    async def generate(self, prompt: str, model: Optional[str] = None) -> tuple[str, int]:
        """
        Generate text from the LLM.

        Args:
            prompt: The prompt to send
            model: Optional model override

        Returns:
            Tuple of (generated_text, latency_ms)

        Raises:
            LLMException on error
        """
        pass


class LLMException(Exception):
    """Base exception for LLM operations"""
    pass


# ============================================================
# OPENAI CLIENT
# ============================================================

class OpenAIClient(BaseLLMClient):
    """Wrapper for OpenAI API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model_default

        if not self.api_key:
            raise LLMException("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(self, prompt: str, model: Optional[str] = None) -> tuple[str, int]:
        model = model or self.model
        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return response.choices[0].message.content, latency_ms

        except OpenAIError as e:
            raise LLMException(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise LLMException(f"Unexpected error in OpenAI client: {str(e)}")


# ============================================================
# ANTHROPIC CLAUDE CLIENT
# ============================================================

class ClaudeClient(BaseLLMClient):
    """Wrapper for Anthropic Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model_default

        if not self.api_key:
            raise LLMException("ANTHROPIC_API_KEY not configured")

        self.client = AsyncAnthropic(api_key=self.api_key)

    async def generate(self, prompt: str, model: Optional[str] = None) -> tuple[str, int]:
        model = model or self.model
        start_time = time.time()

        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return message.content[0].text, latency_ms

        except AnthropicAPIError as e:
            raise LLMException(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise LLMException(f"Unexpected error in Claude client: {str(e)}")


# ============================================================
# GOOGLE GEMINI CLIENT  (uses the new google-genai SDK)
# ============================================================

class GeminiClient(BaseLLMClient):
    """Wrapper for Google Gemini API (google-genai SDK)"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.google_api_key
        self.model = model or settings.gemini_model_default

        if not self.api_key:
            raise LLMException("GOOGLE_API_KEY not configured")

        # Lazy import so tests that don't use Gemini don't need the package
        from google import genai  # type: ignore
        self._genai = genai
        self._client = genai.Client(api_key=self.api_key)

    async def generate(self, prompt: str, model: Optional[str] = None) -> tuple[str, int]:
        model = model or self.model
        start_time = time.time()

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return response.text, latency_ms

        except Exception as e:
            raise LLMException(f"Google Gemini API error: {str(e)}")


# ============================================================
# LLM CLIENT FACTORY
# ============================================================

class LLMClientFactory:
    """Factory for creating appropriate LLM client based on model name"""

    @staticmethod
    def get_client(model: str) -> BaseLLMClient:
        """
        Get appropriate LLM client for model.

        Args:
            model: Model name (e.g., "gpt-4o", "claude-opus-4-1", "gemini-2.0-flash")

        Returns:
            Instantiated LLM client

        Raises:
            LLMException if model not recognised
        """
        model_lower = model.lower()

        if "gpt" in model_lower:
            return OpenAIClient(model=model)
        elif "claude" in model_lower:
            return ClaudeClient(model=model)
        elif "gemini" in model_lower:
            return GeminiClient(model=model)
        else:
            raise LLMException(
                f"Unknown model: {model}. Supported prefixes: gpt-*, claude-*, gemini-*"
            )

    @staticmethod
    def register_client(model_prefix: str, client_class: type) -> None:
        """Register a custom LLM client for a model prefix."""
        if not issubclass(client_class, BaseLLMClient):
            raise ValueError("Client class must inherit from BaseLLMClient")


# ============================================================
# CONVENIENCE HELPER
# ============================================================

async def generate_with_model(prompt: str, model: str) -> tuple[str, int]:
    """
    Convenience function to generate text with a specific model.

    Args:
        prompt: The prompt to send
        model: Model name

    Returns:
        Tuple of (generated_text, latency_ms)
    """
    client = LLMClientFactory.get_client(model)
    return await client.generate(prompt, model=model)
