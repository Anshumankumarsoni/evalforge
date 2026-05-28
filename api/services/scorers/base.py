"""Base scorer abstract class and scorer registry"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseScorer(ABC):
    """
    Abstract base class for all scorers.
    
    A scorer takes expected and actual outputs and returns a normalized score (0.0-1.0).
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this scorer (e.g., 'exact_match')"""
        pass
    
    @abstractmethod
    async def score(self, expected: str, actual: str) -> tuple[float, Optional[str]]:
        """
        Score the actual output against the expected output.
        
        Args:
            expected: The expected/reference output
            actual: The actual output from the LLM
            
        Returns:
            Tuple of (score, reason) where:
            - score: Float from 0.0 to 1.0
            - reason: Optional explanation (used by llm_judge)
        """
        pass


class ScorerRegistry:
    """Registry for managing scorers"""
    
    _scorers: Dict[str, BaseScorer] = {}
    
    @classmethod
    def register(cls, scorer: BaseScorer) -> None:
        """
        Register a scorer.
        
        Args:
            scorer: Scorer instance
        """
        cls._scorers[scorer.name] = scorer
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseScorer]:
        """
        Get a registered scorer by name.
        
        Args:
            name: Scorer name
            
        Returns:
            Scorer instance or None if not found
        """
        return cls._scorers.get(name)
    
    @classmethod
    def list_all(cls) -> list[str]:
        """Get list of all registered scorer names"""
        return list(cls._scorers.keys())
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a scorer"""
        cls._scorers.pop(name, None)
