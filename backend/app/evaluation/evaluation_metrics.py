"""
Evaluation metrics for ranking assessment.
Implements precision@K, recall@K, NDCG@K, MRR, and skill extraction metrics.
"""
import math
from typing import List, Dict, Any


class RankingMetrics:
    """Calculate ranking evaluation metrics."""
    
    @staticmethod
    def precision_at_k(relevant_items: List[int], retrieved_items: List[int], k: int) -> float:
        """
        Calculate Precision@K.
        
        Args:
            relevant_items: List of relevant item IDs.
            retrieved_items: List of retrieved item IDs (ranked).
            k: Cutoff rank.
            
        Returns:
            Precision@K score.
        """
        if k <= 0 or not retrieved_items:
            return 0.0
        
        retrieved_at_k = retrieved_items[:k]
        relevant_retrieved = len(set(retrieved_at_k) & set(relevant_items))
        
        return relevant_retrieved / k
    
    @staticmethod
    def recall_at_k(relevant_items: List[int], retrieved_items: List[int], k: int) -> float:
        """
        Calculate Recall@K.
        
        Args:
            relevant_items: List of relevant item IDs.
            retrieved_items: List of retrieved item IDs (ranked).
            k: Cutoff rank.
            
        Returns:
            Recall@K score.
        """
        if not relevant_items:
            return 0.0
        
        retrieved_at_k = retrieved_items[:k]
        relevant_retrieved = len(set(retrieved_at_k) & set(relevant_items))
        
        return relevant_retrieved / len(relevant_items)
    
    @staticmethod
    def ndcg_at_k(relevant_items: Dict[int, float], retrieved_items: List[int], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain@K.
        
        Args:
            relevant_items: Dictionary mapping item IDs to relevance scores (graded).
            retrieved_items: List of retrieved item IDs (ranked).
            k: Cutoff rank.
            
        Returns:
            NDCG@K score.
        """
        if k <= 0 or not retrieved_items:
            return 0.0
        
        retrieved_at_k = retrieved_items[:k]
        
        # Calculate DCG
        dcg = 0.0
        for i, item in enumerate(retrieved_at_k):
            relevance = relevant_items.get(item, 0.0)
            if relevance > 0:
                dcg += relevance / math.log2(i + 2)
        
        # Calculate ideal DCG
        ideal_relevances = sorted(
            [relevant_items.get(item, 0.0) for item in relevant_items.keys()],
            reverse=True
        )[:k]
        
        idcg = 0.0
        for i, relevance in enumerate(ideal_relevances):
            if relevance > 0:
                idcg += relevance / math.log2(i + 2)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def mean_reciprocal_rank(relevant_items: List[int], retrieved_items: List[int]) -> float:
        """
        Calculate Mean Reciprocal Rank.
        
        Args:
            relevant_items: List of relevant item IDs.
            retrieved_items: List of retrieved item IDs (ranked).
            
        Returns:
            MRR score.
        """
        if not relevant_items or not retrieved_items:
            return 0.0
        
        for i, item in enumerate(retrieved_items):
            if item in relevant_items:
                return 1.0 / (i + 1)
        
        return 0.0


class SkillExtractionMetrics:
    """Calculate skill extraction metrics."""
    
    @staticmethod
    def precision(predicted_skills: List[str], actual_skills: List[str]) -> float:
        """
        Calculate precision for skill extraction.
        
        Args:
            predicted_skills: Skills predicted by the system.
            actual_skills: Ground truth skills.
            
        Returns:
            Precision score.
        """
        if not predicted_skills:
            return 0.0
        
        predicted_set = set(s.lower() for s in predicted_skills)
        actual_set = set(s.lower() for s in actual_skills)
        
        correct = len(predicted_set & actual_set)
        return correct / len(predicted_set)
    
    @staticmethod
    def recall(predicted_skills: List[str], actual_skills: List[str]) -> float:
        """
        Calculate recall for skill extraction.
        
        Args:
            predicted_skills: Skills predicted by the system.
            actual_skills: Ground truth skills.
            
        Returns:
            Recall score.
        """
        if not actual_skills:
            return 0.0
        
        predicted_set = set(s.lower() for s in predicted_skills)
        actual_set = set(s.lower() for s in actual_skills)
        
        correct = len(predicted_set & actual_set)
        return correct / len(actual_set)
    
    @staticmethod
    def f1_score(predicted_skills: List[str], actual_skills: List[str]) -> float:
        """
        Calculate F1 score for skill extraction.
        
        Args:
            predicted_skills: Skills predicted by the system.
            actual_skills: Ground truth skills.
            
        Returns:
            F1 score.
        """
        precision = SkillExtractionMetrics.precision(predicted_skills, actual_skills)
        recall = SkillExtractionMetrics.recall(predicted_skills, actual_skills)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)


class EvidenceMetrics:
    """Calculate evidence extraction metrics."""
    
    @staticmethod
    def evidence_precision(
        predicted_evidence: Dict[str, List[Dict]],
        actual_evidence: Dict[str, List[str]],
    ) -> float:
        """
        Calculate evidence extraction precision.
        
        Args:
            predicted_evidence: Predicted evidence (skill -> list of evidence dicts).
            actual_evidence: Ground truth evidence (skill -> list of section names).
            
        Returns:
            Evidence precision score.
        """
        if not predicted_evidence:
            return 0.0
        
        correct = 0
        total = 0
        
        for skill, evidence_list in predicted_evidence.items():
            if skill in actual_evidence:
                # Check if at least one evidence is in correct section
                predicted_sections = set(ev.get("section", "") for ev in evidence_list)
                actual_sections = set(actual_evidence[skill])
                
                if predicted_sections & actual_sections:
                    correct += 1
            total += 1
        
        return correct / total if total > 0 else 0.0
    
    @staticmethod
    def section_classification_accuracy(
        predicted_sections: List[str],
        actual_sections: List[str],
    ) -> float:
        """
        Calculate section classification accuracy.
        
        Args:
            predicted_sections: Predicted section types.
            actual_sections: Ground truth section types.
            
        Returns:
            Classification accuracy.
        """
        if len(predicted_sections) != len(actual_sections):
            return 0.0
        
        correct = sum(1 for p, a in zip(predicted_sections, actual_sections) if p == a)
        return correct / len(predicted_sections)


class EvaluationReport:
    """Generate evaluation report."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {
            "ranking_metrics": {},
            "skill_extraction_metrics": {},
            "evidence_metrics": {},
            "error_cases": [],
        }
    
    def add_ranking_metrics(
        self,
        precision_at_5: float,
        recall_at_5: float,
        ndcg_at_5: float,
        mrr: float,
    ):
        """Add ranking metrics."""
        self.results["ranking_metrics"] = {
            "precision_at_5": precision_at_5,
            "recall_at_5": recall_at_5,
            "ndcg_at_5": ndcg_at_5,
            "mrr": mrr,
        }
    
    def add_skill_extraction_metrics(
        self,
        precision: float,
        recall: float,
        f1: float,
    ):
        """Add skill extraction metrics."""
        self.results["skill_extraction_metrics"] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }
    
    def add_evidence_metrics(
        self,
        evidence_precision: float,
        section_accuracy: float,
    ):
        """Add evidence metrics."""
        self.results["evidence_metrics"] = {
            "evidence_precision": evidence_precision,
            "section_accuracy": section_accuracy,
        }
    
    def add_error_case(self, case: Dict[str, Any]):
        """Add an error case for analysis."""
        self.results["error_cases"].append(case)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.results
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = []
        
        lines.append("# HireLens Evaluation Report")
        lines.append("")
        
        # Ranking Metrics
        lines.append("## Ranking Metrics")
        lines.append("")
        if self.results["ranking_metrics"]:
            rm = self.results["ranking_metrics"]
            lines.append(f"- **Precision@5**: {rm['precision_at_5']:.4f}")
            lines.append(f"- **Recall@5**: {rm['recall_at_5']:.4f}")
            lines.append(f"- **NDCG@5**: {rm['ndcg_at_5']:.4f}")
            lines.append(f"- **MRR**: {rm['mrr']:.4f}")
        else:
            lines.append("No ranking metrics available.")
        lines.append("")
        
        # Skill Extraction Metrics
        lines.append("## Skill Extraction Metrics")
        lines.append("")
        if self.results["skill_extraction_metrics"]:
            sem = self.results["skill_extraction_metrics"]
            lines.append(f"- **Precision**: {sem['precision']:.4f}")
            lines.append(f"- **Recall**: {sem['recall']:.4f}")
            lines.append(f"- **F1 Score**: {sem['f1_score']:.4f}")
        else:
            lines.append("No skill extraction metrics available.")
        lines.append("")
        
        # Evidence Metrics
        lines.append("## Evidence Metrics")
        lines.append("")
        if self.results["evidence_metrics"]:
            em = self.results["evidence_metrics"]
            lines.append(f"- **Evidence Precision**: {em['evidence_precision']:.4f}")
            lines.append(f"- **Section Accuracy**: {em['section_accuracy']:.4f}")
        else:
            lines.append("No evidence metrics available.")
        lines.append("")
        
        # Error Cases
        lines.append("## Error Cases")
        lines.append("")
        if self.results["error_cases"]:
            for i, case in enumerate(self.results["error_cases"], 1):
                lines.append(f"### Case {i}")
                lines.append(f"- **Type**: {case.get('type', 'Unknown')}")
                lines.append(f"- **Description**: {case.get('description', 'N/A')}")
                lines.append("")
        else:
            lines.append("No error cases recorded.")
        lines.append("")
        
        return "\n".join(lines)
