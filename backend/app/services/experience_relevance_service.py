"""
Experience Relevance Service
Evaluates experience relevance to job requirements based on skills, technologies, and context.
"""
import re
from typing import List
from dataclasses import dataclass

from app.services.experience_classification_service import ExperienceEntry, ExperienceType


@dataclass
class ExperienceRelevance:
    """Relevance score for an experience entry."""
    entry: ExperienceEntry
    relevance_score: float  # 0-100
    matched_skills: List[str]
    complexity_score: float  # 0-100
    outcome_score: float  # 0-100


class ExperienceRelevanceService:
    """Service for evaluating experience relevance."""
    
    def __init__(self):
        """Initialize the experience relevance service."""
        # Action verbs indicating implementation
        self.action_verbs = [
            "developed", "built", "created", "implemented", "designed",
            "engineered", "architected", "programmed", "coded", "wrote",
            "deployed", "maintained", "optimized", "refactored", "integrated",
        ]
        
        # Complexity indicators
        self.complexity_indicators = [
            "microservices", "distributed", "scalable", "architecture",
            "high-availability", "load balancing", "caching", "sharding",
            "pipeline", "ci/cd", "kubernetes", "docker", "aws", "azure",
            "machine learning", "data pipeline", "real-time", "async",
        ]
        
        # Outcome indicators
        self.outcome_indicators = [
            r"\d+%", r"\d+\s*(users|customers|clients|transactions|requests)",
            r"(increased|decreased|reduced|improved|optimized)\s+by\s+\d+",
            r"(saved|reduced|cut)\s+\d+\s*(hours|days|weeks|months)",
            r"\$\d+", r"\d+\s*(gb|tb|pb|mb)",
        ]
    
    def evaluate_relevance(
        self,
        entry: ExperienceEntry,
        required_skills: List[str],
        job_description: str = "",
    ) -> ExperienceRelevance:
        """
        Evaluate the relevance of an experience entry to job requirements.
        
        Args:
            entry: Experience entry to evaluate.
            required_skills: Required skills for the job.
            job_description: Job description text (optional).
            
        Returns:
            ExperienceRelevance with relevance metrics.
        """
        # Extract text from entry
        entry_text = f"{entry.title} {entry.company} {entry.description}".lower()
        
        # Match skills
        matched_skills = self._match_skills(entry_text, required_skills)
        
        # Calculate relevance score based on matched skills
        relevance_score = self._calculate_relevance_score(
            matched_skills, required_skills, entry.experience_type
        )
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(entry_text)
        
        # Calculate outcome score
        outcome_score = self._calculate_outcome_score(entry.description)
        
        return ExperienceRelevance(
            entry=entry,
            relevance_score=relevance_score,
            matched_skills=matched_skills,
            complexity_score=complexity_score,
            outcome_score=outcome_score,
        )
    
    def _match_skills(self, text: str, skills: List[str]) -> List[str]:
        """Match skills in text."""
        matched = []
        text_lower = text.lower()
        
        for skill in skills:
            if skill.lower() in text_lower:
                matched.append(skill)
        
        return matched
    
    def _calculate_relevance_score(
        self,
        matched_skills: List[str],
        required_skills: List[str],
        experience_type: ExperienceType,
    ) -> float:
        """Calculate relevance score based on matched skills and experience type."""
        if not required_skills:
            return 0.0
        
        # Base score from skill match percentage
        match_percentage = len(matched_skills) / len(required_skills)
        base_score = match_percentage * 100.0
        
        # Apply experience type weight
        from app.services.experience_classification_service import ExperienceClassificationService
        classifier = ExperienceClassificationService()
        type_weight = classifier.get_experience_weight(experience_type)
        
        return base_score * type_weight
    
    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate complexity score based on complexity indicators."""
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Count complexity indicators
        for indicator in self.complexity_indicators:
            if indicator.lower() in text_lower:
                score += 10.0
        
        # Check for action verbs (indicates implementation)
        for verb in self.action_verbs:
            if verb in text_lower:
                score += 5.0
        
        # Cap at 100
        return min(score, 100.0)
    
    def _calculate_outcome_score(self, description: str) -> float:
        """Calculate outcome score based on measurable outcomes."""
        if not description:
            return 0.0
        
        score = 0.0
        desc_lower = description.lower()
        
        # Check for outcome indicators
        for pattern in self.outcome_indicators:
            if re.search(pattern, desc_lower):
                score += 25.0
        
        # Cap at 100
        return min(score, 100.0)
