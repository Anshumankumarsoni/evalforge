"""LLM judge scorer - uses Claude to evaluate answers"""

import json
from typing import Optional

from api.services.scorers.base import BaseScorer
from api.services.llm_clients import ClaudeClient, OpenAIClient, LLMException
from api.config import settings


class LLMJudgeScorer(BaseScorer):
    """
    LLM judge scorer - uses Claude or OpenAI to evaluate quality.
    
    Sends expected and actual outputs to the model with a structured rubric prompt,
    parses the JSON response to get a 1-5 rating, and normalizes to 0.0-1.0.
    
    Returns:
        Float from 0.0 to 1.0 based on the model's 1-5 rating
    """
    
    SYSTEM_PROMPT = """You are an impartial evaluator. Given an EXPECTED answer and an ACTUAL answer, rate how well the actual answer satisfies the intent of the expected answer on a scale of 1 to 5.

1 = Completely wrong or irrelevant
2 = Mostly incorrect with some relevant elements
3 = Partially correct, missing key details
4 = Mostly correct with minor omissions
5 = Fully correct and complete

Respond with ONLY a JSON object: {"score": <int>, "reason": "<one sentence>"}"""
    
    def __init__(self):
        """Client is created lazily on first score() call so tests that mock
        this scorer do not need a network connection or cached weights."""
        self._client = None

    def _get_client(self):
        if self._client is None:
            if settings.anthropic_api_key:
                self._client = ClaudeClient()
            elif settings.openai_api_key:
                self._client = OpenAIClient(model=settings.openai_model_default)
            else:
                raise LLMException("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is configured for LLM Judge")
        return self._client
    
    @property
    def name(self) -> str:
        return "llm_judge"
    
    async def score(self, expected: str, actual: str) -> tuple[float, Optional[str]]:
        """
        Score using Claude's evaluation.
        
        Args:
            expected: Expected output
            actual: Actual output
            
        Returns:
            Tuple of (normalized_score, reason)
            Where normalized_score is 0.0-1.0 based on Claude's 1-5 rating
        """
        prompt = f"""Expected answer:
{expected}

Actual answer:
{actual}"""
        
        try:
            response, _ = await self._get_client().generate(prompt)
            
            # Parse JSON response
            json_str = response.strip()
            # Handle markdown code blocks if present
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            
            result = json.loads(json_str)
            
            # Extract score (1-5) and normalize to 0.0-1.0
            raw_score = int(result.get("score", 3))
            raw_score = max(1, min(5, raw_score))  # Clamp to 1-5
            normalized_score = (raw_score - 1) / 4.0  # Convert 1-5 to 0.0-1.0
            reason = result.get("reason", "")
            
            return normalized_score, reason
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, return middle score with error reason
            return 0.5, f"Judge error: {str(e)}"
        except LLMException as e:
            # If LLM call fails, return middle score
            return 0.5, f"LLM error: {str(e)}"
