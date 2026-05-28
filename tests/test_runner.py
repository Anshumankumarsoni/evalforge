"""Unit tests for suite runner and YAML parsing"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================================
# YAML PARSING TESTS
# ============================================================

def test_parse_valid_yaml():
    """Valid YAML should parse into TestSuite"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer this: {input}"
cases:
  - id: tc_001
    input: "What is 2+2?"
    expected: "4"
    scorers: [exact_match]
"""
    suite = SuiteRunner.parse_yaml(yaml_content)
    assert suite.suite == "test_suite"
    assert suite.model == "gpt-4o"
    assert len(suite.cases) == 1
    assert suite.cases[0].id == "tc_001"


def test_parse_yaml_missing_input_placeholder():
    """Template missing {input} should raise ValueError"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer this question"
cases:
  - id: tc_001
    input: "hello"
    expected: "world"
    scorers: [exact_match]
"""
    with pytest.raises(ValueError, match="input"):
        SuiteRunner.parse_yaml(yaml_content)


def test_parse_yaml_duplicate_case_ids():
    """Duplicate case IDs should raise ValueError"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "hello"
    expected: "world"
    scorers: [exact_match]
  - id: tc_001
    input: "another"
    expected: "case"
    scorers: [exact_match]
"""
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        SuiteRunner.parse_yaml(yaml_content)


def test_parse_yaml_invalid_scorer():
    """Unknown scorer name should raise ValueError"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "hello"
    expected: "world"
    scorers: [nonexistent_scorer]
"""
    with pytest.raises(ValueError):
        SuiteRunner.parse_yaml(yaml_content)


def test_parse_yaml_invalid_syntax():
    """Malformed YAML should raise ValueError"""
    from api.services.runner import SuiteRunner

    yaml_content = "this: is: not: valid: yaml: {"
    with pytest.raises(ValueError):
        SuiteRunner.parse_yaml(yaml_content)


def test_parse_yaml_empty_cases():
    """Suite with zero cases should raise ValueError"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases: []
"""
    with pytest.raises(ValueError):
        SuiteRunner.parse_yaml(yaml_content)


def test_parse_yaml_multiple_cases():
    """Suite with multiple cases should parse all of them"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: multi_case_suite
model: claude-opus-4-1
prompt_template: "You are a helpful assistant. {input}"
cases:
  - id: tc_001
    input: "Question 1"
    expected: "Answer 1"
    scorers: [exact_match, semantic_similarity]
  - id: tc_002
    input: "Question 2"
    expected: "Answer 2"
    scorers: [llm_judge]
  - id: tc_003
    input: "Question 3"
    expected: "Answer 3"
    scorers: [exact_match, semantic_similarity, llm_judge]
"""
    suite = SuiteRunner.parse_yaml(yaml_content)
    assert len(suite.cases) == 3
    assert suite.cases[0].scorers == ["exact_match", "semantic_similarity"]
    assert suite.cases[1].scorers == ["llm_judge"]
    assert len(suite.cases[2].scorers) == 3


def test_parse_yaml_with_tags():
    """Tags should be parsed and stored"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: tagged_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "hello"
    expected: "world"
    scorers: [exact_match]
    tags: [account, password]
"""
    suite = SuiteRunner.parse_yaml(yaml_content)
    assert suite.cases[0].tags == ["account", "password"]


def test_parse_yaml_with_description():
    """Optional description should be parsed"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: described_suite
description: "This is a test suite description"
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "hello"
    expected: "world"
    scorers: [exact_match]
"""
    suite = SuiteRunner.parse_yaml(yaml_content)
    assert suite.description == "This is a test suite description"


# ============================================================
# RUNNER INTEGRATION TESTS (using mocks)
# ============================================================

@pytest.mark.asyncio
async def test_run_suite_creates_run_record(mock_db_session):
    """Running a suite should create a Run record in the database"""
    from api.services.runner import SuiteRunner
    from api.models.schemas import TestSuite

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "What is 2+2?"
    expected: "4"
    scorers: [exact_match]
"""
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get:
        
        mock_generate.return_value = ("4", 500)
        
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(1.0, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, case_results = await runner.run_suite(suite)
        
        assert summary.suite_name == "test_suite"
        assert summary.model == "gpt-4o"
        assert summary.total_cases == 1
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_run_suite_returns_correct_case_count(mock_db_session):
    """run_suite should return one CaseResult per test case"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Q1"
    expected: "A1"
    scorers: [exact_match]
  - id: tc_002
    input: "Q2"
    expected: "A2"
    scorers: [exact_match]
  - id: tc_003
    input: "Q3"
    expected: "A3"
    scorers: [exact_match]
"""
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get:
        
        mock_generate.return_value = ("Answer", 100)
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(0.8, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, case_results = await runner.run_suite(suite)
        
        assert len(case_results) == 3


@pytest.mark.asyncio
async def test_run_suite_calculates_avg_score(mock_db_session):
    """run_suite avg_score should be the mean of all scorer scores"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Q1"
    expected: "A1"
    scorers: [exact_match]
  - id: tc_002
    input: "Q2"
    expected: "A2"
    scorers: [exact_match]
"""
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get:
        
        mock_generate.return_value = ("Answer", 100)
        
        # Return 1.0 for first, 0.0 for second
        mock_scorer = MagicMock()
        call_count = {"n": 0}
        
        async def side_effect(expected, actual):
            call_count["n"] += 1
            return (1.0, None) if call_count["n"] == 1 else (0.0, None)
        
        mock_scorer.score = side_effect
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, _ = await runner.run_suite(suite)
        
        assert abs(summary.avg_score - 0.5) < 0.001


@pytest.mark.asyncio
async def test_run_suite_llm_error_handled_gracefully(mock_db_session):
    """LLM errors should not crash the suite; they produce a fallback result"""
    from api.services.runner import SuiteRunner
    from api.services.llm_clients import LLMException

    yaml_content = """
suite: test_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Question"
    expected: "Answer"
    scorers: [exact_match]
"""
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get:
        
        mock_generate.side_effect = LLMException("API down")
        
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(0.0, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, case_results = await runner.run_suite(suite)
        
        # Should still complete without raising
        assert len(case_results) == 1
        assert "LLM Error" in case_results[0].actual


@pytest.mark.asyncio
async def test_regression_detection_first_run(mock_db_session):
    """First run for a suite should never be flagged as regression"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: brand_new_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Q"
    expected: "A"
    scorers: [exact_match]
"""
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get, \
         patch.object(SuiteRunner, "_get_previous_avg", AsyncMock(return_value=None)):
        
        mock_generate.return_value = ("A", 100)
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(1.0, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, _ = await runner.run_suite(suite)
        
        assert summary.is_regression is False


@pytest.mark.asyncio
async def test_regression_detected_when_score_drops(mock_db_session):
    """Should flag regression when score drops more than threshold"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: regression_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Q"
    expected: "A"
    scorers: [exact_match]
"""
    # Previous avg was 0.9; current will be 0.0 -> drop of 0.9 > 0.05 threshold
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get, \
         patch.object(SuiteRunner, "_get_previous_avg", AsyncMock(return_value=0.9)):
        
        mock_generate.return_value = ("wrong answer", 100)
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(0.0, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, _ = await runner.run_suite(suite)
        
        assert summary.is_regression is True


@pytest.mark.asyncio
async def test_no_regression_when_score_improves(mock_db_session):
    """Should not flag regression when score improves"""
    from api.services.runner import SuiteRunner

    yaml_content = """
suite: improving_suite
model: gpt-4o
prompt_template: "Answer: {input}"
cases:
  - id: tc_001
    input: "Q"
    expected: "A"
    scorers: [exact_match]
"""
    # Previous avg was 0.5; current will be 1.0 -> improvement
    with patch("api.services.runner.generate_with_model") as mock_generate, \
         patch("api.services.runner.ScorerRegistry.get") as mock_scorer_get, \
         patch.object(SuiteRunner, "_get_previous_avg", AsyncMock(return_value=0.5)):
        
        mock_generate.return_value = ("A", 100)
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(return_value=(1.0, None))
        mock_scorer_get.return_value = mock_scorer
        
        runner = SuiteRunner(mock_db_session)
        suite = SuiteRunner.parse_yaml(yaml_content)
        summary, _ = await runner.run_suite(suite)
        
        assert summary.is_regression is False


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_db_session():
    """Async mock database session"""
    from unittest.mock import AsyncMock, MagicMock
    from sqlalchemy.ext.asyncio import AsyncSession

    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()
    
    # _get_previous_avg queries the DB, so mock execute to return empty
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    session.execute.return_value = mock_result
    
    return session
