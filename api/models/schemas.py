"""Pydantic schemas for request/response validation (Pydantic v2 compatible)"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# TEST CASE & SUITE SCHEMAS
# ============================================================

VALID_SCORERS = {"exact_match", "semantic_similarity", "llm_judge"}


class TestCase(BaseModel):
    """Single test case from YAML suite"""
    id: str = Field(..., description="Unique case identifier (e.g., tc_001)")
    input: str = Field(..., description="Input to send to LLM")
    expected: str = Field(..., description="Expected/reference output")
    scorers: List[str] = Field(
        ...,
        description="Scorers to apply: exact_match, semantic_similarity, llm_judge"
    )
    tags: Optional[List[str]] = Field(default=None, description="Optional metadata tags")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Case id cannot be empty")
        return v.strip()

    @field_validator("input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Input cannot be empty")
        return v.strip()

    @field_validator("expected")
    @classmethod
    def validate_expected(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Expected cannot be empty")
        return v.strip()

    @field_validator("scorers")
    @classmethod
    def validate_scorers(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one scorer must be specified")
        for scorer in v:
            if scorer not in VALID_SCORERS:
                raise ValueError(
                    f"Invalid scorer: '{scorer}'. Must be one of {sorted(VALID_SCORERS)}"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "tc_001",
                "input": "How do I reset my password?",
                "expected": "Go to settings and click forgot password",
                "scorers": ["exact_match", "semantic_similarity", "llm_judge"],
                "tags": ["account", "password"]
            }
        }
    }


class TestSuite(BaseModel):
    """Complete test suite loaded from YAML"""
    suite: str = Field(..., description="Unique suite name")
    description: Optional[str] = Field(default=None, description="Human-readable description")
    model: str = Field(..., description="LLM model to test")
    prompt_template: str = Field(..., description="Prompt with {input} placeholder")
    cases: List[TestCase] = Field(..., description="List of test cases")

    @field_validator("suite")
    @classmethod
    def validate_suite_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Suite name cannot be empty")
        return v.strip()

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model cannot be empty")
        return v.strip()

    @field_validator("prompt_template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        if "{input}" not in v:
            raise ValueError("Prompt template must contain '{input}' placeholder")
        return v

    @field_validator("cases")
    @classmethod
    def validate_cases(cls, v: List[TestCase]) -> List[TestCase]:
        if not v:
            raise ValueError("At least one test case is required")
        case_ids = [case.id for case in v]
        if len(case_ids) != len(set(case_ids)):
            duplicates = [i for i in case_ids if case_ids.count(i) > 1]
            raise ValueError(f"Duplicate case IDs found: {list(set(duplicates))}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "suite": "customer_support_bot",
                "description": "Tests for the customer support chatbot",
                "model": "gpt-4o",
                "prompt_template": "You are a helpful support agent. Answer: {input}",
                "cases": [
                    {
                        "id": "tc_001",
                        "input": "How do I reset my password?",
                        "expected": "Go to settings and click forgot password",
                        "scorers": ["semantic_similarity", "llm_judge"],
                        "tags": ["account"]
                    }
                ]
            }
        }
    }


# ============================================================
# SCORING RESULT SCHEMAS
# ============================================================

class ScorerResult(BaseModel):
    """Result from a single scorer on a case"""
    scorer: str
    score: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None


class CaseResult(BaseModel):
    """Complete result for a single test case"""
    case_id: str
    input: str
    expected: str
    actual: str
    scores: Dict[str, float]
    avg_score: Optional[float] = None
    latency_ms: Optional[int] = None
    details: Optional[List[ScorerResult]] = None


# ============================================================
# RUN RESULT SCHEMAS
# ============================================================

class RunSummary(BaseModel):
    """Summary of a single run"""
    run_id: str
    suite_name: str
    model: str
    timestamp: datetime
    total_cases: int = Field(..., ge=0)
    pass_count: int = Field(..., ge=0)
    avg_score: float = Field(..., ge=0.0, le=1.0)
    is_regression: bool


class RunDetail(BaseModel):
    """Complete details of a run including all case results"""
    run_id: str
    suite_name: str
    model: str
    timestamp: datetime
    total_cases: int = Field(..., ge=0)
    pass_count: int = Field(..., ge=0)
    avg_score: float = Field(..., ge=0.0, le=1.0)
    is_regression: bool
    results: List[CaseResult]


class RunsList(BaseModel):
    """Paginated list of runs"""
    runs: List[RunSummary]
    total: int = Field(..., ge=0)


# ============================================================
# SCORE HISTORY SCHEMAS
# ============================================================

class ScorerBreakdown(BaseModel):
    """Per-scorer average scores for a run"""
    exact_match: float = Field(..., ge=0.0, le=1.0)
    semantic_similarity: float = Field(..., ge=0.0, le=1.0)
    llm_judge: float = Field(..., ge=0.0, le=1.0)


class HistoryEntry(BaseModel):
    """Single entry in a suite's score history"""
    run_id: str
    timestamp: datetime
    avg_score: float = Field(..., ge=0.0, le=1.0)
    scorer_breakdown: Optional[ScorerBreakdown] = None


class SuiteHistory(BaseModel):
    """Complete history for a suite"""
    suite_name: str
    history: List[HistoryEntry]


# ============================================================
# REGRESSION ALERT SCHEMA
# ============================================================

class RegressionAlertSchema(BaseModel):
    """Regression alert detail"""
    alert_id: int
    suite_name: str
    run_id: str
    previous_avg: float = Field(..., ge=0.0, le=1.0)
    current_avg: float = Field(..., ge=0.0, le=1.0)
    delta: float
    flagged_at: datetime


# ============================================================
# GENERIC ERROR & HEALTH
# ============================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: Optional[str] = None
    database: Optional[str] = None
