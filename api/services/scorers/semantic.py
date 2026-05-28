"""Semantic similarity scorer — cosine similarity of sentence embeddings"""

from typing import Optional

import numpy as np

from api.services.scorers.base import BaseScorer


class SemanticSimilarityScorer(BaseScorer):
    """
    Semantic similarity scorer using sentence-transformers (all-MiniLM-L6-v2).

    The transformer model is loaded lazily on first use so tests that mock
    this scorer do not need a network connection or cached weights.

    Returns:
        Cosine similarity in [0.0, 1.0]
    """

    def __init__(self):
        self._model = None   # loaded on first call to score()

    def _get_model(self):
        """Load model on first use (lazy init)"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    @property
    def name(self) -> str:
        return "semantic_similarity"

    async def score(self, expected: str, actual: str) -> tuple[float, Optional[str]]:
        """
        Score by cosine similarity of sentence embeddings.

        Args:
            expected: Expected output
            actual: Actual output

        Returns:
            Tuple of (cosine_similarity, None)
        """
        # Guard before model load: empty strings → cosine similarity undefined
        if not expected.strip() or not actual.strip():
            return 0.0, None

        model = self._get_model()

        embeddings = model.encode([expected, actual], convert_to_numpy=True)
        e_vec = embeddings[0]
        a_vec = embeddings[1]

        norm_product = np.linalg.norm(e_vec) * np.linalg.norm(a_vec)
        if norm_product == 0.0:
            return 0.0, None

        cosine_sim = float(np.dot(e_vec, a_vec) / norm_product)
        score = float(np.clip(cosine_sim, 0.0, 1.0))

        return score, None
