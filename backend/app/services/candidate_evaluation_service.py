"""
Unified Candidate Evaluation Service
Orchestrates the complete candidate evaluation pipeline, reusing existing services.
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.evidence_extraction_service import EvidenceExtractionService
from app.services.evidence_mapping_service import EvidenceMappingService
from app.services.temporal_service import TemporalService

logger = logging.getLogger(__name__)


@dataclass
class CandidateEvaluationContext:
    """Context for candidate evaluation."""
    resume_text: str
    job_text: str
    resume_skills: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    experience_metadata: Optional[List[Dict]] = None
    project_metadata: Optional[List[Dict]] = None
    use_semantic: bool = True
    evaluation_date: Optional[date] = None
    scoring_config: Optional[ScoringConfig] = None
    structured_requirements: Optional[List[Dict]] = None  # Phase 10.2: Structured requirements


@dataclass
class CandidateEvaluationResult:
    """Result of candidate evaluation."""
    overall_score: float
    required_skill_coverage: float
    preferred_skill_coverage: float
    evidence_score: float
    semantic_score: Optional[float]
    tfidf_score: float
    skill_match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    additional_skills: List[str]
    skill_evidence: Dict[str, List[Dict]]
    explanation: str
    scoring_strategy: Dict[str, Any]
    evidence_summary: Dict[str, List[str]]
    requirement_evaluations: Dict[str, Dict[str, Any]]
    strengths: List[str]
    gaps: List[str]
    temporal_metadata: Optional[Dict[str, Any]] = None
    keyword_stuffing_penalty: float = 0.0
    keyword_stuffing_analysis: Optional[Dict[str, Any]] = None
    group_evaluation: Optional[List[Dict[str, Any]]] = None  # Phase 10.2: Group evaluation


class CandidateEvaluationService:
    """
    Unified candidate evaluation orchestration service.
    
    Coordinates skill matching, semantic matching, evidence extraction,
    requirement mapping, temporal metadata, and score calculation.
    Reuses existing services without duplicating business logic.
    """
    
    ALGORITHM_VERSION = "3.0.0-unified-evaluation"
    
    def __init__(
        self,
        scoring_config: Optional[ScoringConfig] = None,
        evaluation_date: Optional[date] = None,
    ):
        """
        Initialize the evaluation service.
        
        Args:
            scoring_config: Scoring configuration (uses defaults if None).
            evaluation_date: Date for temporal calculations (uses today if None).
        """
        self.scoring_config = scoring_config or ScoringConfig(
            keyword_stuffing_education_aware=True,
            related_skill_credit_threshold=0.5,
        )
        self.evaluation_date = evaluation_date or date.today()
        
        # Initialize services (reuse existing implementations)
        self.scoring_service = ScoringService(config=self.scoring_config)
        self.evidence_extraction_service = EvidenceExtractionService()
        self.evidence_mapping_service = EvidenceMappingService()
        self.temporal_service = TemporalService(evaluation_date=self.evaluation_date)
    
    def evaluate_candidate(
        self,
        context: CandidateEvaluationContext,
    ) -> CandidateEvaluationResult:
        """
        Evaluate a candidate against job requirements.
        
        Args:
            context: Evaluation context with resume and job information.
            
        Returns:
            CandidateEvaluationResult with complete evaluation data.
        """
        logger.info(f"=== CANDIDATE EVALUATION STARTED ===")
        logger.info(f"Algorithm version: {self.ALGORITHM_VERSION}")
        logger.info(f"Evaluation date: {self.evaluation_date}")
        
        # Use scoring service for core evaluation (reuses existing logic)
        match_dict = self.scoring_service.compute_match(
            resume_text=context.resume_text,
            job_text=context.job_text,
            resume_skills=context.resume_skills,
            required_skills=context.required_skills,
            preferred_skills=context.preferred_skills,
            use_semantic=context.use_semantic,
            experience_metadata=context.experience_metadata,
            project_metadata=context.project_metadata,
            structured_requirements=context.structured_requirements,  # Phase 10.2
        )
        
        # Extract temporal metadata
        temporal_metadata = self._extract_temporal_metadata(
            context.experience_metadata,
            context.project_metadata,
        )
        
        # Build unified result
        result = CandidateEvaluationResult(
            overall_score=match_dict["overall_score"],
            required_skill_coverage=match_dict["required_skill_coverage"],
            preferred_skill_coverage=match_dict["preferred_skill_coverage"],
            evidence_score=match_dict["evidence_score"],
            semantic_score=match_dict["semantic_score"],
            tfidf_score=match_dict["tfidf_score"],
            skill_match_score=match_dict["skill_match_score"],
            matched_skills=match_dict["matched_skills"],
            missing_skills=match_dict["missing_skills"],
            additional_skills=match_dict["additional_skills"],
            skill_evidence=match_dict["skill_evidence"],
            explanation=match_dict["explanation"],
            scoring_strategy=match_dict["scoring_strategy"],
            evidence_summary=match_dict["evidence_summary"],
            requirement_evaluations=match_dict["requirement_evaluations"],
            strengths=match_dict["strengths"],
            gaps=match_dict["gaps"],
            temporal_metadata=temporal_metadata,
            keyword_stuffing_penalty=match_dict["keyword_stuffing_penalty"],
            keyword_stuffing_analysis=match_dict["keyword_stuffing_analysis"],
            group_evaluation=match_dict.get("group_evaluation", []),  # Phase 10.2
        )
        
        # Update algorithm version in scoring strategy
        result.scoring_strategy["algorithm_version"] = self.ALGORITHM_VERSION
        result.scoring_strategy["evaluation_date"] = self.evaluation_date.isoformat()
        
        logger.info(f"=== CANDIDATE EVALUATION COMPLETE ===")
        logger.info(f"Overall score: {result.overall_score}")
        
        return result
    
    def _extract_temporal_metadata(
        self,
        experience_metadata: Optional[List[Dict]],
        project_metadata: Optional[List[Dict]],
    ) -> Optional[Dict[str, Any]]:
        """
        Extract and aggregate temporal metadata.
        
        Args:
            experience_metadata: Experience entries with temporal fields.
            project_metadata: Project entries with temporal fields.
            
        Returns:
            Aggregated temporal metadata.
        """
        if not experience_metadata and not project_metadata:
            return None
        
        temporal_summary = {
            "evaluation_date": self.evaluation_date.isoformat(),
            "experiences": [],
            "projects": [],
            "timeline": [],
        }
        
        # Process experiences
        if experience_metadata:
            for exp in experience_metadata:
                if exp.get("duration_months") is not None:
                    temporal_summary["experiences"].append({
                        "title": exp.get("title"),
                        "duration_months": exp.get("duration_months"),
                        "recency_category": exp.get("recency_category"),
                        "temporal_status": exp.get("temporal_status"),
                        "is_current": exp.get("is_current", False),
                    })
        
        # Process projects
        if project_metadata:
            for proj in project_metadata:
                if proj.get("duration_months") is not None:
                    temporal_summary["projects"].append({
                        "title": proj.get("title"),
                        "duration_months": proj.get("duration_months"),
                        "recency_category": proj.get("recency_category"),
                        "temporal_status": proj.get("temporal_status"),
                        "is_current": proj.get("is_current", False),
                    })
        
        # Generate timeline
        if experience_metadata or project_metadata:
            timeline = self.temporal_service.generate_timeline(
                experience_metadata or [],
                project_metadata or [],
            )
            temporal_summary["timeline"] = timeline
        
        return temporal_summary
    
    def evaluate_batch(
        self,
        contexts: List[CandidateEvaluationContext],
    ) -> List[CandidateEvaluationResult]:
        """
        Evaluate multiple candidates.
        
        Args:
            contexts: List of evaluation contexts.
            
        Returns:
            List of evaluation results.
        """
        results = []
        for context in contexts:
            result = self.evaluate_candidate(context)
            results.append(result)
        
        return results
