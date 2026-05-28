"""Exact match scorer - lowercased string equality"""

from typing import Optional

from api.services.scorers.base import BaseScorer


class ExactMatchScorer(BaseScorer):
    """
    Exact match scorer - compares lowercased strings for equality.
    
    Returns:
        1.0 if strings match (case-insensitive)
        0.0 otherwise
    """
    
    @property
    def name(self) -> str:
        return "exact_match"
    
    async def score(self, expected: str, actual: str) -> tuple[float, Optional[str]]:
        """
        Score by exact match (case-insensitive).
        
        Args:
            expected: Expected output
            actual: Actual output
            
        Returns:
            Tuple of (score, reason)
        """
        expected_lower = expected.lower().strip()
        actual_lower = actual.lower().strip()
        
        score = 1.0 if expected_lower == actual_lower else 0.0
        reason = None
        
        return score, reason
