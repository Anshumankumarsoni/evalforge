"""Suite runner - orchestrates complete evaluation pipeline"""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import Run, Result, RegressionAlert
from api.models.schemas import TestSuite, CaseResult, ScorerResult, RunSummary
from api.services.llm_clients import generate_with_model, LLMException
from api.services.scorers.base import ScorerRegistry
from api.services.scorers.exact import ExactMatchScorer
from api.services.scorers.semantic import SemanticSimilarityScorer
from api.services.scorers.llm_judge import LLMJudgeScorer
from api.config import settings


# ============================================================
# INITIALIZE SCORERS
# ============================================================

# Register scorers on import
_exact_scorer = ExactMatchScorer()
_semantic_scorer = SemanticSimilarityScorer()
_llm_judge_scorer = LLMJudgeScorer()

ScorerRegistry.register(_exact_scorer)
ScorerRegistry.register(_semantic_scorer)
ScorerRegistry.register(_llm_judge_scorer)


# ============================================================
# SUITE RUNNER
# ============================================================

class SuiteRunner:
    """Orchestrates complete test suite evaluation"""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize runner.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    @staticmethod
    def parse_yaml(yaml_content: str) -> TestSuite:
        """
        Parse YAML test suite.
        
        Args:
            yaml_content: YAML file content as string
            
        Returns:
            Validated TestSuite object
            
        Raises:
            ValueError if YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
            suite = TestSuite(**data)
            return suite
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {str(e)}")
        except Exception as e:
            raise ValueError(f"Invalid test suite: {str(e)}")
    
    async def run_suite(self, suite: TestSuite) -> tuple[RunSummary, List[CaseResult]]:
        """
        Execute a complete test suite.
        
        Args:
            suite: Validated TestSuite
            
        Returns:
            Tuple of (RunSummary, list of CaseResults)
        """
        # Generate unique run ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}_{str(uuid4())[:8]}"
        
        # Process all test cases
        case_results = []
        all_scores = []
        
        for test_case in suite.cases:
            # Build prompt with input
            prompt = suite.prompt_template.format(input=test_case.input)
            
            # Call LLM
            try:
                actual_output, latency_ms = await generate_with_model(prompt, suite.model)
            except LLMException as e:
                actual_output = f"[LLM Error: {str(e)}]"
                latency_ms = 0
            
            # Score with all requested scorers
            scorer_scores = {}
            scorer_details = []
            
            for scorer_name in test_case.scorers:
                scorer = ScorerRegistry.get(scorer_name)
                if not scorer:
                    scorer_scores[scorer_name] = 0.0
                    scorer_details.append(ScorerResult(
                        scorer=scorer_name,
                        score=0.0,
                        reason=f"Scorer '{scorer_name}' not found"
                    ))
                    continue
                
                try:
                    score, reason = await scorer.score(test_case.expected, actual_output)
                    scorer_scores[scorer_name] = score
                    scorer_details.append(ScorerResult(
                        scorer=scorer_name,
                        score=score,
                        reason=reason
                    ))
                    all_scores.append(score)
                except Exception as e:
                    scorer_scores[scorer_name] = 0.0
                    scorer_details.append(ScorerResult(
                        scorer=scorer_name,
                        score=0.0,
                        reason=f"Scorer error: {str(e)}"
                    ))
            
            # Create case result
            avg_case_score = sum(scorer_scores.values()) / len(scorer_scores) if scorer_scores else 0.0
            case_result = CaseResult(
                case_id=test_case.id,
                input=test_case.input,
                expected=test_case.expected,
                actual=actual_output,
                scores=scorer_scores,
                avg_score=avg_case_score,
                latency_ms=latency_ms,
                details=scorer_details
            )
            case_results.append(case_result)
            
            # Save result to database
            for scorer_name, score in scorer_scores.items():
                reason = next(
                    (d.reason for d in scorer_details if d.scorer == scorer_name),
                    None
                )
                db_result = Result(
                    run_id=run_id,
                    case_id=test_case.id,
                    input=test_case.input,
                    expected=test_case.expected,
                    actual=actual_output,
                    scorer=scorer_name,
                    score=score,
                    latency_ms=latency_ms,
                    reason=reason
                )
                self.session.add(db_result)
        
        # Calculate run statistics
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        pass_count = sum(1 for score in all_scores if score >= 0.8)
        
        # Check for regression
        is_regression = await self._check_regression(suite.suite, avg_score)
        
        # Create run record
        run = Run(
            run_id=run_id,
            suite_name=suite.suite,
            model=suite.model,
            timestamp=datetime.now(timezone.utc),
            total_cases=len(suite.cases),
            pass_count=pass_count,
            avg_score=avg_score,
            is_regression=is_regression
        )
        self.session.add(run)
        
        # If regression detected, create alert
        if is_regression:
            previous_avg = await self._get_previous_avg(suite.suite)
            if previous_avg is not None:
                delta = avg_score - previous_avg
                alert = RegressionAlert(
                    suite_name=suite.suite,
                    run_id=run_id,
                    previous_avg=previous_avg,
                    current_avg=avg_score,
                    delta=delta
                )
                self.session.add(alert)
        
        # Commit to database
        await self.session.commit()
        
        # Create summary
        summary = RunSummary(
            run_id=run_id,
            suite_name=suite.suite,
            model=suite.model,
            timestamp=run.timestamp,
            total_cases=run.total_cases,
            pass_count=run.pass_count,
            avg_score=run.avg_score,
            is_regression=run.is_regression
        )
        
        return summary, case_results
    
    async def _check_regression(self, suite_name: str, current_avg: float) -> bool:
        """
        Check if current score is a regression compared to previous run.
        
        Args:
            suite_name: Name of test suite
            current_avg: Current average score
            
        Returns:
            True if regression detected (drop > threshold)
        """
        previous_avg = await self._get_previous_avg(suite_name)
        if previous_avg is None:
            return False  # No previous run, not a regression
        
        delta = current_avg - previous_avg
        threshold = settings.regression_threshold
        
        return delta < -threshold
    
    async def _get_previous_avg(self, suite_name: str) -> Optional[float]:
        """
        Get average score from previous run of same suite.
        
        Args:
            suite_name: Name of test suite
            
        Returns:
            Average score or None if no previous run
        """
        query = select(Run).where(
            Run.suite_name == suite_name
        ).order_by(Run.timestamp.desc()).limit(1)
        
        result = await self.session.execute(query)
        previous_run = result.scalars().first()
        
        if previous_run:
            return previous_run.avg_score
        return None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def run_yaml_suite(yaml_content: str, session: AsyncSession) -> tuple[RunSummary, List[CaseResult]]:
    """
    Convenience function to run a complete YAML suite.
    
    Args:
        yaml_content: YAML file content as string
        session: Async database session
        
    Returns:
        Tuple of (RunSummary, list of CaseResults)
        
    Raises:
        ValueError if YAML is invalid
    """
    runner = SuiteRunner(session)
    suite = runner.parse_yaml(yaml_content)
    return await runner.run_suite(suite)
