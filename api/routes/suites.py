"""API routes for test suite operations"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import Run, Result, get_db_session
from api.models.schemas import (
    RunSummary, SuiteHistory, HistoryEntry, ScorerBreakdown, ErrorResponse
)
from api.services.runner import run_yaml_suite

router = APIRouter(prefix="/suites", tags=["suites"])


# ============================================================
# POST /suites/run
# ============================================================

@router.post(
    "/run",
    response_model=RunSummary,
    responses={400: {"model": ErrorResponse}},
    summary="Run a test suite",
    description="Upload a YAML test suite and run all test cases against the configured LLM.",
)
async def run_suite(
    file: UploadFile = File(..., description="YAML test suite definition"),
    session: AsyncSession = Depends(get_db_session),
) -> RunSummary:
    """
    Run a complete test suite from a YAML file upload.

    Returns a RunSummary immediately on completion. Detailed per-case results
    are available via GET /runs/{run_id}.
    """
    if not (file.filename or "").endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="File must be YAML (.yaml or .yml)")

    try:
        content = await file.read()
        summary, _ = await run_yaml_suite(content.decode("utf-8"), session)
        return summary
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid test suite: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running suite: {e}")


# ============================================================
# GET /suites/{suite_name}/history
# ============================================================

@router.get(
    "/{suite_name}/history",
    response_model=SuiteHistory,
    responses={404: {"model": ErrorResponse}},
    summary="Suite score history",
    description="Get historical average scores for a suite to detect drift over time.",
)
async def get_suite_history(
    suite_name: str,
    session: AsyncSession = Depends(get_db_session),
) -> SuiteHistory:
    """
    Return all runs for a suite ordered by timestamp, with per-scorer breakdowns.

    Use the history data to draw trend charts and compute the Prompt Drift Index.
    """
    try:
        # All runs for this suite, oldest first
        runs_q = (
            select(Run)
            .where(Run.suite_name == suite_name)
            .order_by(Run.timestamp)
        )
        runs_result = await session.execute(runs_q)
        runs = runs_result.scalars().all()

        history: list[HistoryEntry] = []

        for run in runs:
            # Per-scorer averages for this run
            results_q = select(Result).where(Result.run_id == run.run_id)
            results_result = await session.execute(results_q)
            db_results = results_result.scalars().all()

            totals: dict[str, float] = {}
            counts: dict[str, int] = {}
            for r in db_results:
                totals[r.scorer] = totals.get(r.scorer, 0.0) + r.score
                counts[r.scorer] = counts.get(r.scorer, 0) + 1

            # Only attach breakdown if all three scorers were used
            breakdown: ScorerBreakdown | None = None
            if all(k in totals for k in ("exact_match", "semantic_similarity", "llm_judge")):
                breakdown = ScorerBreakdown(
                    exact_match=totals["exact_match"] / counts["exact_match"],
                    semantic_similarity=totals["semantic_similarity"] / counts["semantic_similarity"],
                    llm_judge=totals["llm_judge"] / counts["llm_judge"],
                )

            history.append(
                HistoryEntry(
                    run_id=run.run_id,
                    timestamp=run.timestamp,
                    avg_score=run.avg_score,
                    scorer_breakdown=breakdown,
                )
            )

        return SuiteHistory(suite_name=suite_name, history=history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {e}")
