"""
Skill Hierarchy Registry
Centralized, configurable skill relationship system.
Distinguishes between aliases, equivalents, parent-child, related, and unrelated technologies.
"""
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class RelationshipType(Enum):
    """Types of skill relationships."""
    ALIAS = "alias"  # Exact synonyms (e.g., RESTful services ↔ REST API)
    EQUIVALENT = "equivalent"  # Functionally equivalent (e.g., Postgres ↔ PostgreSQL)
    PARENT_CHILD = "parent_child"  # Hierarchical (e.g., SQL → PostgreSQL)
    RELATED = "related"  # Related but not equivalent (e.g., TensorFlow ↔ PyTorch)
    DISTINCT = "distinct"  # Unrelated (e.g., Java ↔ JavaScript)


@dataclass
class SkillRelationship:
    """Represents a relationship between two skills."""
    skill_a: str
    skill_b: str
    relationship: RelationshipType
    confidence: float = 1.0  # 0.0 to 1.0


class SkillHierarchyRegistry:
    """
    Registry for skill relationships.
    Provides methods to query relationships and determine match strictness.
    """
    
    def __init__(self):
        self._relationships: Dict[str, List[SkillRelationship]] = {}
        self._initialize_default_relationships()
    
    def _initialize_default_relationships(self):
        """Initialize default skill relationships."""
        
        # REST API aliases
        self._add_relationship("REST API", "RESTful services", RelationshipType.ALIAS)
        self._add_relationship("REST API", "RESTful API", RelationshipType.ALIAS)
        self._add_relationship("REST API", "REST APIs", RelationshipType.ALIAS)
        
        # PostgreSQL aliases
        self._add_relationship("PostgreSQL", "Postgres", RelationshipType.ALIAS)
        self._add_relationship("PostgreSQL", "PostgreSQL database", RelationshipType.ALIAS)
        
        # SQL family (parent-child)
        self._add_relationship("SQL", "PostgreSQL", RelationshipType.PARENT_CHILD)
        self._add_relationship("SQL", "MySQL", RelationshipType.PARENT_CHILD)
        self._add_relationship("SQL", "SQLite", RelationshipType.PARENT_CHILD)
        self._add_relationship("SQL", "Microsoft SQL Server", RelationshipType.PARENT_CHILD)
        
        # Database relationships (related but not equivalent)
        self._add_relationship("PostgreSQL", "MySQL", RelationshipType.RELATED)
        self._add_relationship("MySQL", "PostgreSQL", RelationshipType.RELATED)
        
        # NoSQL family (parent-child)
        self._add_relationship("NoSQL", "MongoDB", RelationshipType.PARENT_CHILD)
        self._add_relationship("NoSQL", "Redis", RelationshipType.PARENT_CHILD)
        self._add_relationship("NoSQL", "Cassandra", RelationshipType.PARENT_CHILD)
        self._add_relationship("NoSQL", "DynamoDB", RelationshipType.PARENT_CHILD)
        
        # JavaScript framework family (related)
        self._add_relationship("React", "Next.js", RelationshipType.RELATED)
        self._add_relationship("React", "Vue.js", RelationshipType.RELATED)
        self._add_relationship("React", "Angular", RelationshipType.RELATED)
        
        # Python web frameworks (related)
        self._add_relationship("Django", "Flask", RelationshipType.RELATED)
        self._add_relationship("Django", "FastAPI", RelationshipType.RELATED)
        self._add_relationship("Flask", "FastAPI", RelationshipType.RELATED)
        
        # ML frameworks (related)
        self._add_relationship("TensorFlow", "PyTorch", RelationshipType.RELATED)
        self._add_relationship("TensorFlow", "Keras", RelationshipType.RELATED)
        self._add_relationship("PyTorch", "Keras", RelationshipType.RELATED)
        
        # Cloud platforms (related)
        self._add_relationship("AWS", "Azure", RelationshipType.RELATED)
        self._add_relationship("AWS", "GCP", RelationshipType.RELATED)
        self._add_relationship("Azure", "GCP", RelationshipType.RELATED)
        
        # Distinct technologies (explicitly marked as unrelated)
        self._add_relationship("Java", "JavaScript", RelationshipType.DISTINCT)
        self._add_relationship("C#", "C++", RelationshipType.DISTINCT)
        self._add_relationship("React", "React Native", RelationshipType.DISTINCT)
        
    def _add_relationship(self, skill_a: str, skill_b: str, relationship: RelationshipType):
        """Add a bidirectional relationship."""
        # Normalize keys for storage
        skill_a_norm = skill_a.lower().strip()
        skill_b_norm = skill_b.lower().strip()
        
        rel = SkillRelationship(skill_a, skill_b, relationship)
        
        if skill_a_norm not in self._relationships:
            self._relationships[skill_a_norm] = []
        self._relationships[skill_a_norm].append(rel)
        
        # Add reverse relationship
        rel_reverse = SkillRelationship(skill_b, skill_a, relationship)
        if skill_b_norm not in self._relationships:
            self._relationships[skill_b_norm] = []
        self._relationships[skill_b_norm].append(rel_reverse)
    
    def get_relationship(self, skill_a: str, skill_b: str) -> Optional[RelationshipType]:
        """
        Get the relationship type between two skills.
        Returns None if no relationship is defined.
        """
        skill_a_norm = skill_a.lower().strip()
        skill_b_norm = skill_b.lower().strip()
        
        if skill_a_norm in self._relationships:
            for rel in self._relationships[skill_a_norm]:
                if rel.skill_b.lower() == skill_b_norm:
                    return rel.relationship
        
        return None
    
    def is_alias(self, skill_a: str, skill_b: str) -> bool:
        """Check if two skills are aliases."""
        rel = self.get_relationship(skill_a, skill_b)
        return rel == RelationshipType.ALIAS
    
    def is_equivalent(self, skill_a: str, skill_b: str) -> bool:
        """Check if two skills are equivalent."""
        rel = self.get_relationship(skill_a, skill_b)
        return rel in [RelationshipType.ALIAS, RelationshipType.EQUIVALENT]
    
    def is_related(self, skill_a: str, skill_b: str) -> bool:
        """Check if two skills are related (not equivalent)."""
        rel = self.get_relationship(skill_a, skill_b)
        return rel == RelationshipType.RELATED
    
    def is_parent_child(self, skill_a: str, skill_b: str) -> bool:
        """Check if two skills have parent-child relationship."""
        rel = self.get_relationship(skill_a, skill_b)
        return rel == RelationshipType.PARENT_CHILD
    
    def is_distinct(self, skill_a: str, skill_b: str) -> bool:
        """Check if two skills are explicitly marked as distinct."""
        rel = self.get_relationship(skill_a, skill_b)
        return rel == RelationshipType.DISTINCT
    
    def get_match_credit(self, required_skill: str, candidate_skill: str) -> float:
        """
        Determine the match credit for a candidate skill against a required skill.
        
        Returns:
            1.0: Full credit (alias or equivalent)
            0.5: Partial credit (parent-child or related)
            0.0: No credit (distinct or no relationship)
        """
        rel = self.get_relationship(required_skill, candidate_skill)
        
        if rel in [RelationshipType.ALIAS, RelationshipType.EQUIVALENT]:
            return 1.0
        elif rel in [RelationshipType.PARENT_CHILD, RelationshipType.RELATED]:
            return 0.5
        elif rel == RelationshipType.DISTINCT:
            return 0.0
        else:
            # No relationship defined - treat as no match
            return 0.0
    
    def get_related_skills(self, skill: str) -> List[str]:
        """Get all skills related to the given skill."""
        skill_norm = skill.lower().strip()
        related = []
        
        if skill_norm in self._relationships:
            for rel in self._relationships[skill_norm]:
                if rel.relationship in [RelationshipType.RELATED, RelationshipType.PARENT_CHILD]:
                    related.append(rel.skill_b)
        
        return related
    
    def add_custom_relationship(self, skill_a: str, skill_b: str, relationship: RelationshipType):
        """Add a custom relationship at runtime."""
        self._add_relationship(skill_a, skill_b, relationship)


# Global registry instance
_skill_hierarchy_registry = None


def get_skill_hierarchy_registry() -> SkillHierarchyRegistry:
    """Get the global skill hierarchy registry instance."""
    global _skill_hierarchy_registry
    if _skill_hierarchy_registry is None:
        _skill_hierarchy_registry = SkillHierarchyRegistry()
    return _skill_hierarchy_registry
