"""API routes for run retrieval and export"""

import csv
import json
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import Run, Result, get_db_session
from api.models.schemas import (
    RunsList, RunSummary, RunDetail, CaseResult,
    ScorerResult, ErrorResponse,
)

router = APIRouter(prefix="/runs", tags=["runs"])


# ============================================================
# GET /runs
# ============================================================

@router.get(
    "",
    response_model=RunsList,
    summary="List all runs",
    description="Returns all past runs sorted by timestamp descending.",
)
async def list_runs(
    suite: str | None = Query(default=None, description="Filter by suite name"),
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
    session: AsyncSession = Depends(get_db_session),
) -> RunsList:
    """List runs, optionally filtered by suite name."""
    try:
        q = select(Run).order_by(Run.timestamp.desc()).limit(limit)
        if suite:
            q = q.where(Run.suite_name == suite)

        result = await session.execute(q)
        runs = result.scalars().all()

        summaries = [
            RunSummary(
                run_id=r.run_id,
                suite_name=r.suite_name,
                model=r.model,
                timestamp=r.timestamp,
                total_cases=r.total_cases,
                pass_count=r.pass_count,
                avg_score=r.avg_score,
                is_regression=r.is_regression,
            )
            for r in runs
        ]
        return RunsList(runs=summaries, total=len(summaries))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing runs: {e}")


# ============================================================
# GET /runs/{run_id}
# ============================================================

@router.get(
    "/{run_id}",
    response_model=RunDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get run details",
    description="Full results for a specific run including all case results.",
)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RunDetail:
    """Return complete run details with per-case, per-scorer results."""
    try:
        # Fetch run header
        run_q = select(Run).where(Run.run_id == run_id)
        run_result = await session.execute(run_q)
        run = run_result.scalars().first()

        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        # Fetch all result rows for this run
        res_q = select(Result).where(Result.run_id == run_id).order_by(Result.case_id)
        res_result = await session.execute(res_q)
        db_results = res_result.scalars().all()

        # Group by case_id
        cases: dict[str, dict] = {}
        for row in db_results:
            if row.case_id not in cases:
                cases[row.case_id] = {
                    "case_id": row.case_id,
                    "input": row.input,
                    "expected": row.expected,
                    "actual": row.actual,
                    "latency_ms": row.latency_ms,
                    "scores": {},
                    "details": [],
                }
            cases[row.case_id]["scores"][row.scorer] = row.score
            cases[row.case_id]["details"].append(
                ScorerResult(scorer=row.scorer, score=row.score, reason=row.reason)
            )

        case_results = [
            CaseResult(
                case_id=c["case_id"],
                input=c["input"],
                expected=c["expected"],
                actual=c["actual"],
                scores=c["scores"],
                avg_score=sum(c["scores"].values()) / len(c["scores"]) if c["scores"] else 0.0,
                latency_ms=c["latency_ms"],
                details=c["details"],
            )
            for c in cases.values()
        ]

        return RunDetail(
            run_id=run.run_id,
            suite_name=run.suite_name,
            model=run.model,
            timestamp=run.timestamp,
            total_cases=run.total_cases,
            pass_count=run.pass_count,
            avg_score=run.avg_score,
            is_regression=run.is_regression,
            results=case_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting run: {e}")


# ============================================================
# GET /runs/{run_id}/export
# ============================================================

@router.get(
    "/{run_id}/export",
    responses={
        200: {"description": "CSV or JSON file download"},
        404: {"model": ErrorResponse},
    },
    summary="Export run results",
    description="Download all results for a run as CSV or JSON.",
)
async def export_run(
    run_id: str,
    format: str = Query(default="csv", pattern="^(csv|json)$", description="csv or json"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export run results as a downloadable CSV or JSON file."""
    try:
        # Verify run exists
        run_q = select(Run).where(Run.run_id == run_id)
        run_result = await session.execute(run_q)
        run = run_result.scalars().first()

        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        # Fetch results
        res_q = select(Result).where(Result.run_id == run_id)
        res_result = await session.execute(res_q)
        db_results = res_result.scalars().all()

        if format == "json":
            payload = {
                "run_id": run.run_id,
                "suite_name": run.suite_name,
                "model": run.model,
                "timestamp": run.timestamp.isoformat(),
                "total_cases": run.total_cases,
                "pass_count": run.pass_count,
                "avg_score": run.avg_score,
                "is_regression": run.is_regression,
                "results": [
                    {
                        "case_id": r.case_id,
                        "input": r.input,
                        "expected": r.expected,
                        "actual": r.actual,
                        "scorer": r.scorer,
                        "score": r.score,
                        "latency_ms": r.latency_ms,
                        "reason": r.reason,
                    }
                    for r in db_results
                ],
            }
            return StreamingResponse(
                iter([json.dumps(payload, indent=2)]),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'},
            )

        # Default: CSV
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["case_id", "input", "expected", "actual",
                          "scorer", "score", "latency_ms", "reason"])
        for r in db_results:
            writer.writerow([
                r.case_id, r.input, r.expected, r.actual,
                r.scorer, r.score, r.latency_ms, r.reason or "",
            ])

        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting run: {e}")
