"""Database models and async SQLite setup for EvalForge"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    Text, ForeignKey, Index, event
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker
)
from sqlalchemy.orm import declarative_base, relationship

from api.config import settings

# Base class for all ORM models
Base = declarative_base()

# ============================================================
# DATABASE MODELS
# ============================================================

class Run(Base):
    """
    Represents a single test suite execution.
    
    Attributes:
        run_id: Unique identifier for this run (e.g., "run_20231215_143022")
        suite_name: Name of the test suite that was run
        model: LLM model used (e.g., "gpt-4o", "claude-opus-4-1")
        timestamp: When the run started
        total_cases: Total number of test cases in this run
        pass_count: Number of cases that passed (score >= 0.8 for all scorers)
        avg_score: Average score across all cases and scorers
        is_regression: Whether this run is flagged as a regression
        results: Relationship to Result records for this run
        alerts: Relationship to RegressionAlert records for this run
    """
    __tablename__ = "runs"
    
    run_id = Column(String(50), primary_key=True, index=True)
    suite_name = Column(String(255), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    total_cases = Column(Integer, nullable=False)
    pass_count = Column(Integer, nullable=False, default=0)
    avg_score = Column(Float, nullable=False, default=0.0)
    is_regression = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    results = relationship("Result", back_populates="run", cascade="all, delete-orphan")
    alerts = relationship("RegressionAlert", back_populates="run", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_run_suite_timestamp", "suite_name", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<Run(run_id={self.run_id}, suite_name={self.suite_name}, avg_score={self.avg_score})>"


class Result(Base):
    """
    Represents a single test case result within a run.
    
    Attributes:
        result_id: Unique identifier (auto-generated)
        run_id: Foreign key to the parent Run
        case_id: Test case identifier from the YAML suite
        input: The input sent to the LLM
        expected: The expected/reference output
        actual: The actual output from the LLM
        scorer: Name of the scorer (exact_match, semantic_similarity, llm_judge)
        score: Normalized score from this scorer (0.0-1.0)
        latency_ms: How long the LLM call took in milliseconds
        timestamp: When this result was recorded
        reason: Optional explanation from LLM judge scorer
        run: Relationship to parent Run
    """
    __tablename__ = "results"
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey("runs.run_id"), nullable=False, index=True)
    case_id = Column(String(100), nullable=False, index=True)
    input = Column(Text, nullable=False)
    expected = Column(Text, nullable=False)
    actual = Column(Text, nullable=False)
    scorer = Column(String(50), nullable=False)  # exact_match, semantic_similarity, llm_judge
    score = Column(Float, nullable=False)  # 0.0 to 1.0
    latency_ms = Column(Integer, nullable=True)  # Optional
    timestamp = Column(DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    reason = Column(Text, nullable=True)  # Explanation from llm_judge
    
    # Relationships
    run = relationship("Run", back_populates="results")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_result_run_case", "run_id", "case_id"),
        Index("ix_result_scorer", "scorer"),
    )
    
    def __repr__(self) -> str:
        return f"<Result(case_id={self.case_id}, scorer={self.scorer}, score={self.score})>"


class RegressionAlert(Base):
    """
    Represents a flagged regression (score drop > threshold).
    
    Attributes:
        alert_id: Unique identifier (auto-generated)
        suite_name: Which test suite was affected
        run_id: Foreign key to the Run that triggered this alert
        previous_avg: Average score from previous run
        current_avg: Average score from current run
        delta: The change (current_avg - previous_avg, typically negative)
        flagged_at: When the alert was created
        run: Relationship to the Run that triggered this
    """
    __tablename__ = "regression_alerts"
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    suite_name = Column(String(255), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey("runs.run_id"), nullable=False, unique=True)
    previous_avg = Column(Float, nullable=False)
    current_avg = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)  # current_avg - previous_avg (usually negative)
    flagged_at = Column(DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    run = relationship("Run", back_populates="alerts")
    
    def __repr__(self) -> str:
        return f"<RegressionAlert(suite_name={self.suite_name}, delta={self.delta})>"


# ============================================================
# DATABASE ENGINE & SESSION SETUP
# ============================================================

class DatabaseManager:
    """
    Manages async SQLite database connections and session creation.
    
    Usage:
        db = DatabaseManager()
        await db.initialize()  # Create tables on startup
        async with db.get_session() as session:
            # Use session
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_url: Connection string (defaults to settings.database_url)
        """
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.async_session_maker = None
    
    async def initialize(self) -> None:
        """
        Create async engine and session factory.
        Must be called once on application startup.
        """
        # Enable WAL mode for SQLite (better for concurrent access)
        connect_args = {"check_same_thread": False}
        if "sqlite" in self.database_url:
            connect_args = {"check_same_thread": False, "timeout": 30}
        
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True to see SQL queries
            connect_args=connect_args,
            pool_pre_ping=True,  # Verify connections before using
        )
        
        # Enable SQLite WAL mode for better concurrency
        if "sqlite" in self.database_url:
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        
        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Close the database connection. Call on application shutdown."""
        if self.engine:
            await self.engine.dispose()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager that yields a database session and closes it on exit.

        Usage::

            async with db.get_session() as session:
                result = await session.execute(select(Run))
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        session: AsyncSession = self.async_session_maker()
        try:
            yield session
        finally:
            await session.close()
    
    async def create_tables(self) -> None:
        """Explicitly create all tables. Useful for migrations."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables. WARNING: Destructive — use in tests only."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global database manager instance
db = DatabaseManager()


# ============================================================
# DATABASE HELPER FUNCTIONS
# ============================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage in route handlers::

        @app.get("/endpoint")
        async def my_route(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with db.get_session() as session:
        yield session


async def init_db() -> None:
    """Initialize database on application startup."""
    await db.initialize()


async def close_db() -> None:
    """Close database connection on application shutdown."""
    await db.close()
