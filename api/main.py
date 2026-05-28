"""FastAPI application entry point for EvalForge"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.models.db import init_db, close_db
from api.models.schemas import HealthResponse
from api.routes import suites, runs

# ============================================================
# APP CREATION
# ============================================================

app = FastAPI(
    title="EvalForge API",
    description=(
        "LLM Evaluation Framework — define test cases, run them against any "
        "LLM, score the outputs, and detect regressions over time."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ============================================================
# MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# LIFECYCLE EVENTS
# ============================================================

@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database (creates tables if they don't exist)."""
    await init_db()
    print("✓ EvalForge API started — database ready")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close the database connection pool gracefully."""
    await close_db()
    print("✓ EvalForge API shut down")


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "Validation error", "detail": str(exc), "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "code": "INTERNAL_ERROR"},
    )


# ============================================================
# CORE ENDPOINTS
# ============================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
)
async def health_check() -> HealthResponse:
    """Returns API status and version. Use to verify the service is up."""
    return HealthResponse(status="ok", version="0.1.0", database="connected")


@app.get("/", tags=["root"], summary="API info", include_in_schema=False)
async def root() -> dict:
    """Root endpoint — handy summary of available routes."""
    return {
        "name": "EvalForge API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "health":  "GET  /health",
            "run":     "POST /suites/run",
            "list":    "GET  /runs",
            "detail":  "GET  /runs/{run_id}",
            "export":  "GET  /runs/{run_id}/export?format=csv|json",
            "history": "GET  /suites/{suite_name}/history",
        },
    }


# ============================================================
# ROUTER REGISTRATION
# ============================================================

app.include_router(suites.router)   # /suites/...
app.include_router(runs.router)     # /runs/...


# ============================================================
# ENTRY POINT (local dev without Docker)
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
