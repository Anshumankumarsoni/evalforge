"""Unit tests for all scorer implementations"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark that requires network (HuggingFace model download)
requires_network = pytest.mark.skipif(
    True,  # always skip in CI/sandbox — model not cached
    reason="Requires HuggingFace network access to download all-MiniLM-L6-v2"
)


# ============================================================
# EXACT MATCH SCORER TESTS
# ============================================================

@pytest.mark.asyncio
async def test_exact_match_identical():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, reason = await scorer.score("hello world", "hello world")
    assert score == 1.0
    assert reason is None


@pytest.mark.asyncio
async def test_exact_match_case_insensitive():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, _ = await scorer.score("Hello World", "hello world")
    assert score == 1.0


@pytest.mark.asyncio
async def test_exact_match_different_strings():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, _ = await scorer.score("expected answer", "different answer")
    assert score == 0.0


@pytest.mark.asyncio
async def test_exact_match_whitespace_trimmed():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, _ = await scorer.score("  hello  ", "hello")
    assert score == 1.0


@pytest.mark.asyncio
async def test_exact_match_empty_strings():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, _ = await scorer.score("", "")
    assert score == 1.0


@pytest.mark.asyncio
async def test_exact_match_one_empty():
    from api.services.scorers.exact import ExactMatchScorer
    scorer = ExactMatchScorer()
    score, _ = await scorer.score("expected", "")
    assert score == 0.0


def test_exact_match_name():
    from api.services.scorers.exact import ExactMatchScorer
    assert ExactMatchScorer().name == "exact_match"


# ============================================================
# SEMANTIC SIMILARITY SCORER TESTS
# Tests that require the real model are skipped in sandbox;
# the mock tests below validate the scoring logic.
# ============================================================

@requires_network
@pytest.mark.asyncio
async def test_semantic_identical_strings():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    scorer = SemanticSimilarityScorer()
    score, reason = await scorer.score("hello world", "hello world")
    assert score > 0.99
    assert reason is None


@requires_network
@pytest.mark.asyncio
async def test_semantic_similar_strings():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    scorer = SemanticSimilarityScorer()
    score, _ = await scorer.score(
        "Go to settings and click forgot password",
        "Navigate to settings, then select forgot password option"
    )
    assert score > 0.7


@requires_network
@pytest.mark.asyncio
async def test_semantic_unrelated_strings():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    scorer = SemanticSimilarityScorer()
    score, _ = await scorer.score(
        "The weather is sunny today",
        "Please reset your database credentials"
    )
    assert score < 0.5


@requires_network
@pytest.mark.asyncio
async def test_semantic_paraphrase():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    scorer = SemanticSimilarityScorer()
    reference = "We are open Monday through Friday from 9am to 6pm"
    paraphrase_score, _ = await scorer.score(reference, "Our business hours are 9am-6pm, weekdays only")
    unrelated_score, _ = await scorer.score(reference, "Please contact support for billing issues")
    assert paraphrase_score > unrelated_score


@pytest.mark.asyncio
async def test_semantic_score_in_range():
    """Score must be 0–1; uses a mocked model so no network needed."""
    import numpy as np
    from api.services.scorers.semantic import SemanticSimilarityScorer

    scorer = SemanticSimilarityScorer()

    # Inject a tiny mock model
    mock_model = MagicMock()
    mock_model.encode = MagicMock(
        return_value=np.array([[1.0, 0.0], [0.0, 1.0]])
    )
    scorer._model = mock_model

    score, _ = await scorer.score("hello", "world")
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_semantic_cosine_logic():
    """Verify cosine similarity calculation is correct."""
    import numpy as np
    from api.services.scorers.semantic import SemanticSimilarityScorer

    scorer = SemanticSimilarityScorer()
    mock_model = MagicMock()

    # Identical unit vectors → cosine = 1.0
    vec = np.array([1.0, 0.0, 0.0])
    mock_model.encode = MagicMock(return_value=np.array([vec, vec]))
    scorer._model = mock_model
    score, _ = await scorer.score("a", "a")
    assert abs(score - 1.0) < 1e-6

    # Orthogonal vectors → cosine = 0.0
    mock_model.encode = MagicMock(
        return_value=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    )
    score, _ = await scorer.score("a", "b")
    assert abs(score - 0.0) < 1e-6


def test_semantic_name():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    assert SemanticSimilarityScorer().name == "semantic_similarity"


@pytest.mark.asyncio
async def test_semantic_empty_string_returns_zero():
    from api.services.scorers.semantic import SemanticSimilarityScorer
    scorer = SemanticSimilarityScorer()
    score, _ = await scorer.score("", "something")
    assert score == 0.0


# ============================================================
# LLM JUDGE SCORER TESTS (all mocked — no API key needed)
# ============================================================

def _make_judge_with_mock(response_text: str):
    """Helper: build an LLMJudgeScorer with a mocked Claude client."""
    from api.services.scorers.llm_judge import LLMJudgeScorer
    scorer = LLMJudgeScorer()
    mock_client = MagicMock()
    mock_client.generate = AsyncMock(return_value=(response_text, 100))
    scorer._client = mock_client   # bypass lazy init
    return scorer


@pytest.mark.asyncio
async def test_llm_judge_perfect_score():
    scorer = _make_judge_with_mock('{"score": 5, "reason": "Fully correct"}')
    score, reason = await scorer.score("correct answer", "correct answer")
    assert score == 1.0
    assert "Fully correct" in reason


@pytest.mark.asyncio
async def test_llm_judge_lowest_score():
    scorer = _make_judge_with_mock('{"score": 1, "reason": "Completely wrong"}')
    score, reason = await scorer.score("expected answer", "totally wrong")
    assert score == 0.0
    assert "Completely wrong" in reason


@pytest.mark.asyncio
async def test_llm_judge_middle_score():
    scorer = _make_judge_with_mock('{"score": 3, "reason": "Partially correct"}')
    score, _ = await scorer.score("expected answer", "partial answer")
    assert score == 0.5


@pytest.mark.asyncio
async def test_llm_judge_score_2_normalises_correctly():
    scorer = _make_judge_with_mock('{"score": 2, "reason": "Mostly wrong"}')
    score, _ = await scorer.score("expected", "actual")
    assert abs(score - 0.25) < 0.001   # (2-1)/4


@pytest.mark.asyncio
async def test_llm_judge_score_4_normalises_correctly():
    scorer = _make_judge_with_mock('{"score": 4, "reason": "Good answer"}')
    score, _ = await scorer.score("expected", "actual")
    assert abs(score - 0.75) < 0.001   # (4-1)/4


@pytest.mark.asyncio
async def test_llm_judge_invalid_json():
    scorer = _make_judge_with_mock("not valid json at all")
    score, reason = await scorer.score("expected", "actual")
    assert score == 0.5
    assert reason is not None
    assert "error" in reason.lower()


@pytest.mark.asyncio
async def test_llm_judge_score_clamped():
    scorer = _make_judge_with_mock('{"score": 99, "reason": "Over limit"}')
    score, _ = await scorer.score("expected", "actual")
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_llm_judge_llm_error_fallback():
    from api.services.scorers.llm_judge import LLMJudgeScorer
    from api.services.llm_clients import LLMException
    scorer = LLMJudgeScorer()
    mock_client = MagicMock()
    mock_client.generate = AsyncMock(side_effect=LLMException("API unavailable"))
    scorer._client = mock_client
    score, reason = await scorer.score("expected", "actual")
    assert score == 0.5
    assert "LLM error" in reason


@pytest.mark.asyncio
async def test_llm_judge_markdown_json():
    scorer = _make_judge_with_mock('```json\n{"score": 4, "reason": "Good answer"}\n```')
    score, reason = await scorer.score("expected", "actual")
    assert abs(score - 0.75) < 0.001
    assert "Good answer" in reason


def test_llm_judge_name():
    from api.services.scorers.llm_judge import LLMJudgeScorer
    scorer = LLMJudgeScorer()
    assert scorer.name == "llm_judge"


# ============================================================
# SCORER REGISTRY TESTS
# ============================================================

def test_scorer_registry_register():
    from api.services.scorers.base import ScorerRegistry, BaseScorer
    from typing import Optional

    class _Unique(BaseScorer):
        @property
        def name(self):
            return "_unique_test_scorer"
        async def score(self, expected, actual):
            return 1.0, None

    scorer = _Unique()
    ScorerRegistry.register(scorer)
    assert ScorerRegistry.get("_unique_test_scorer") is scorer
    ScorerRegistry.unregister("_unique_test_scorer")


def test_scorer_registry_get_missing():
    from api.services.scorers.base import ScorerRegistry
    assert ScorerRegistry.get("totally_missing") is None


def test_scorer_registry_list():
    from api.services.scorers.base import ScorerRegistry
    names = ScorerRegistry.list_all()
    assert isinstance(names, list)
