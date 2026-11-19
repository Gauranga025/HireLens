"""
Project Intelligence Service
Evaluates project complexity, relevance, and outcomes.
"""
import re
from typing import List
from dataclasses import dataclass

from app.services.experience_classification_service import ExperienceEntry, ExperienceType


@dataclass
class ProjectEvaluation:
    """Evaluation of a project."""
    entry: ExperienceEntry
    relevance_score: float  # 0-100
    complexity_score: float  # 0-100
    outcome_score: float  # 0-100
    matched_skills: List[str]


class ProjectIntelligenceService:
    """Service for evaluating project intelligence."""
    
    def __init__(self):
        """Initialize the project intelligence service."""
        # Complexity indicators
        self.complexity_indicators = [
            "microservices", "distributed", "scalable", "architecture",
            "high-availability", "load balancing", "caching", "sharding",
            "pipeline", "ci/cd", "kubernetes", "docker", "aws", "azure",
            "machine learning", "data pipeline", "real-time", "async",
            "api", "rest", "graphql", "database", "sql", "nosql",
            "authentication", "authorization", "security", "encryption",
        ]
        
        # Outcome indicators
        self.outcome_indicators = [
            r"\d+%", r"\d+\s*(users|customers|clients|transactions|requests)",
            r"(increased|decreased|reduced|improved|optimized)\s+by\s+\d+",
            r"(saved|reduced|cut)\s+\d+\s*(hours|days|weeks|months)",
            r"\$\d+", r"\d+\s*(gb|tb|pb|mb)",
        ]
    
    def evaluate_project(
        self,
        entry: ExperienceEntry,
        required_skills: List[str],
        job_description: str = "",
    ) -> ProjectEvaluation:
        """
        Evaluate a project entry.
        
        Args:
            entry: Project entry to evaluate.
            required_skills: Required skills for the job.
            job_description: Job description text (optional).
            
        Returns:
            ProjectEvaluation with project metrics.
        """
        # Extract text from entry
        entry_text = f"{entry.title} {entry.company} {entry.description}".lower()
        
        # Match skills
        matched_skills = self._match_skills(entry_text, required_skills)
        
        # Calculate relevance score
        relevance_score = self._calculate_relevance_score(
            matched_skills, required_skills, entry.experience_type
        )
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(entry_text)
        
        # Calculate outcome score
        outcome_score = self._calculate_outcome_score(entry.description)
        
        return ProjectEvaluation(
            entry=entry,
            relevance_score=relevance_score,
            complexity_score=complexity_score,
            outcome_score=outcome_score,
            matched_skills=matched_skills,
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
        """Calculate relevance score based on matched skills and project type."""
        if not required_skills:
            return 0.0
        
        # Base score from skill match percentage
        match_percentage = len(matched_skills) / len(required_skills)
        base_score = match_percentage * 100.0
        
        # Apply project type weight
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
        
        # Check for description length (longer descriptions may indicate more detail)
        if len(text) > 200:
            score += 10.0
        elif len(text) > 100:
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
