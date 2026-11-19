"""
Temporal Intelligence Service
Handles date parsing, duration calculation, recency categorization, and timeline generation.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, date


class TemporalStatus(Enum):
    """Temporal status of an experience or project."""
    CURRENT = "current"
    COMPLETED = "completed"
    OPEN_ENDED = "open_ended"
    UNKNOWN = "unknown"
    INVALID = "invalid"


class RecencyCategory(Enum):
    """Recency category relative to evaluation date."""
    WITHIN_6_MONTHS = "within_6_months"
    WITHIN_1_YEAR = "within_1_year"
    WITHIN_2_YEARS = "within_2_years"
    OLDER_THAN_2_YEARS = "older_than_2_years"
    UNKNOWN = "unknown"


@dataclass
class TemporalMetadata:
    """Temporal metadata for an experience or project."""
    start_date: Optional[str]  # Normalized YYYY-MM format
    end_date: Optional[str]  # Normalized YYYY-MM format
    is_current: bool
    duration_months: Optional[int]
    recency_category: Optional[str]
    temporal_status: str
    date_confidence: float  # 0.0 to 1.0


class TemporalService:
    """Service for temporal intelligence."""
    
    def __init__(self, evaluation_date: Optional[date] = None):
        """
        Initialize the temporal service.
        
        Args:
            evaluation_date: Date to use for recency calculations (defaults to today).
        """
        self.evaluation_date = evaluation_date or date.today()
        
        # Month name mapping
        self.month_map = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }
        
        # Date patterns
        self.date_patterns = [
            # Month Year (e.g., "January 2025", "Jan 2025")
            re.compile(
                r"\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
                r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?))\s+(\d{4})\b",
                re.IGNORECASE
            ),
            # MM/YYYY (e.g., "01/2025", "1/2025")
            re.compile(r"\b(\d{1,2})/(\d{4})\b"),
            # YYYY (e.g., "2025")
            re.compile(r"\b(199\d|20[0-2]\d|2030)\b"),
        ]
    
    def parse_duration_string(self, duration_str: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Parse a duration string into start date, end date, and current status.
        
        Args:
            duration_str: Duration string from resume (e.g., "Jan 2020 - Present").
            
        Returns:
            Tuple of (start_date, end_date, is_current) in YYYY-MM format.
        """
        if not duration_str or duration_str == "Not found":
            return None, None, False
        
        # Check for current/present indicators
        is_current = bool(re.search(r"\b[Pp]resent|[Cc]urrent\b", duration_str))
        
        # Extract date ranges
        # Pattern: "Jan 2020 - Dec 2022" or "Jan 2020 - Present"
        range_pattern = re.compile(
            r"(.+?)\s*[-–—to]+\s*(.+)",
            re.IGNORECASE
        )
        range_match = range_pattern.search(duration_str)
        
        if range_match:
            start_part = range_match.group(1).strip()
            end_part = range_match.group(2).strip()
            
            start_date = self._parse_date_part(start_part)
            end_date = self._parse_date_part(end_part) if not is_current else None
            
            return start_date, end_date, is_current
        
        # Single date (assume it's start date)
        single_date = self._parse_date_part(duration_str)
        if single_date:
            return single_date, None, False
        
        return None, None, False
    
    def _parse_date_part(self, date_part: str) -> Optional[str]:
        """
        Parse a date part into YYYY-MM format.
        
        Args:
            date_part: Date part string.
            
        Returns:
            Normalized date in YYYY-MM format, or None if unparseable.
        """
        date_part = date_part.strip()
        
        # Check for current/present
        if re.search(r"\b[Pp]resent|[Cc]urrent\b", date_part):
            return None
        
        # Try month year pattern
        for pattern in self.date_patterns:
            match = pattern.search(date_part)
            if match:
                if pattern == self.date_patterns[0]:  # Month Year
                    month_name = match.group(1).lower()
                    year = int(match.group(2))
                    month = self.month_map.get(month_name)
                    if month and 1990 <= year <= 2030:
                        return f"{year:04d}-{month:02d}"
                elif pattern == self.date_patterns[1]:  # MM/YYYY
                    month = int(match.group(1))
                    year = int(match.group(2))
                    if 1 <= month <= 12 and 1990 <= year <= 2030:
                        return f"{year:04d}-{month:02d}"
                elif pattern == self.date_patterns[2]:  # YYYY
                    year = int(match.group(1))
                    if 1990 <= year <= 2030:
                        return f"{year:04d}-01"  # Default to January
        
        return None
    
    def calculate_duration_months(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        is_current: bool,
    ) -> Optional[int]:
        """
        Calculate duration in months.
        
        Args:
            start_date: Start date in YYYY-MM format.
            end_date: End date in YYYY-MM format.
            is_current: Whether this is a current position.
            
        Returns:
            Duration in months, or None if cannot calculate.
        """
        if not start_date:
            return None
        
        try:
            start = datetime.strptime(start_date, "%Y-%m").date()
            
            if is_current:
                end = self.evaluation_date
            elif end_date:
                end = datetime.strptime(end_date, "%Y-%m").date()
            else:
                return None
            
            # Calculate difference in months
            months = (end.year - start.year) * 12 + (end.month - start.month)
            
            # Ensure non-negative
            return max(0, months)
        except (ValueError, TypeError):
            return None
    
    def determine_recency_category(
        self,
        end_date: Optional[str],
        is_current: bool,
    ) -> str:
        """
        Determine recency category.
        
        Args:
            end_date: End date in YYYY-MM format.
            is_current: Whether this is a current position.
            
        Returns:
            Recency category string.
        """
        if is_current:
            return RecencyCategory.WITHIN_6_MONTHS.value
        
        if not end_date:
            return RecencyCategory.UNKNOWN.value
        
        try:
            end = datetime.strptime(end_date, "%Y-%m").date()
            delta = self.evaluation_date - end
            
            months_ago = delta.days / 30.44  # Average days per month
            
            if months_ago <= 6:
                return RecencyCategory.WITHIN_6_MONTHS.value
            elif months_ago <= 12:
                return RecencyCategory.WITHIN_1_YEAR.value
            elif months_ago <= 24:
                return RecencyCategory.WITHIN_2_YEARS.value
            else:
                return RecencyCategory.OLDER_THAN_2_YEARS.value
        except (ValueError, TypeError):
            return RecencyCategory.UNKNOWN.value
    
    def determine_temporal_status(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        is_current: bool,
    ) -> str:
        """
        Determine temporal status.
        
        Args:
            start_date: Start date in YYYY-MM format.
            end_date: End date in YYYY-MM format.
            is_current: Whether this is a current position.
            
        Returns:
            Temporal status string.
        """
        if is_current:
            return TemporalStatus.CURRENT.value
        
        if not start_date:
            return TemporalStatus.UNKNOWN.value
        
        if not end_date:
            return TemporalStatus.OPEN_ENDED.value
        
        # Validate date range
        try:
            start = datetime.strptime(start_date, "%Y-%m").date()
            end = datetime.strptime(end_date, "%Y-%m").date()
            
            if end < start:
                return TemporalStatus.INVALID.value
            
            return TemporalStatus.COMPLETED.value
        except (ValueError, TypeError):
            return TemporalStatus.INVALID.value
    
    def calculate_date_confidence(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        is_current: bool,
    ) -> float:
        """
        Calculate confidence in date parsing (0.0 to 1.0).
        
        Args:
            start_date: Start date in YYYY-MM format.
            end_date: Optional[str]: End date in YYYY-MM format.
            is_current: Whether this is a current position.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        if not start_date:
            return 0.0
        
        confidence = 0.5  # Base confidence for having start date
        
        if end_date:
            confidence += 0.3  # Higher confidence with end date
        
        if is_current:
            confidence += 0.2  # Higher confidence for current positions
        
        return min(confidence, 1.0)
    
    def generate_temporal_metadata(
        self,
        duration_str: str,
    ) -> TemporalMetadata:
        """
        Generate complete temporal metadata from a duration string.
        
        Args:
            duration_str: Duration string from resume.
            
        Returns:
            TemporalMetadata object.
        """
        start_date, end_date, is_current = self.parse_duration_string(duration_str)
        
        duration_months = self.calculate_duration_months(start_date, end_date, is_current)
        recency_category = self.determine_recency_category(end_date, is_current)
        temporal_status = self.determine_temporal_status(start_date, end_date, is_current)
        date_confidence = self.calculate_date_confidence(start_date, end_date, is_current)
        
        return TemporalMetadata(
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            duration_months=duration_months,
            recency_category=recency_category,
            temporal_status=temporal_status,
            date_confidence=date_confidence,
        )
    
    def detect_overlap(
        self,
        entry1: Dict[str, Any],
        entry2: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if two entries overlap in time.
        
        Args:
            entry1: First entry with temporal metadata.
            entry2: Second entry with temporal metadata.
            
        Returns:
            Overlap information dict, or None if no overlap.
        """
        start1 = entry1.get("start_date")
        end1 = entry1.get("end_date")
        is_current1 = entry1.get("is_current", False)
        
        start2 = entry2.get("start_date")
        end2 = entry2.get("end_date")
        is_current2 = entry2.get("is_current", False)
        
        if not start1 or not start2:
            return None
        
        try:
            s1 = datetime.strptime(start1, "%Y-%m").date()
            e1 = datetime.strptime(end1, "%Y-%m").date() if end1 and not is_current1 else self.evaluation_date
            s2 = datetime.strptime(start2, "%Y-%m").date()
            e2 = datetime.strptime(end2, "%Y-%m").date() if end2 and not is_current2 else self.evaluation_date
            
            # Check for overlap
            if s1 <= e2 and s2 <= e1:
                overlap_start = max(s1, s2)
                overlap_end = min(e1, e2)
                overlap_months = max(0, (overlap_end.year - overlap_start.year) * 12 + (overlap_end.month - overlap_start.month))
                
                return {
                    "overlap_start": overlap_start.strftime("%Y-%m"),
                    "overlap_end": overlap_end.strftime("%Y-%m"),
                    "overlap_months": overlap_months,
                }
        except (ValueError, TypeError):
            pass
        
        return None
    
    def generate_timeline(
        self,
        experiences: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate a chronological timeline from experiences and projects.
        
        Args:
            experiences: List of experience entries with temporal metadata.
            projects: List of project entries with temporal metadata.
            
        Returns:
            Chronologically sorted timeline.
        """
        timeline = []
        
        # Add experiences
        for exp in experiences:
            if exp.get("start_date"):
                timeline.append({
                    "type": "experience",
                    "title": exp.get("title"),
                    "company": exp.get("company"),
                    "start_date": exp.get("start_date"),
                    "end_date": exp.get("end_date"),
                    "is_current": exp.get("is_current", False),
                    "experience_type": exp.get("experience_type"),
                })
        
        # Add projects
        for proj in projects:
            if proj.get("start_date"):
                timeline.append({
                    "type": "project",
                    "title": proj.get("title"),
                    "start_date": proj.get("start_date"),
                    "end_date": proj.get("end_date"),
                    "is_current": proj.get("is_current", False),
                    "project_type": proj.get("project_type"),
                })
        
        # Sort by start date (most recent first)
        timeline.sort(key=lambda x: (
            x.get("is_current", False),
            x.get("start_date", "0000-01") or "0000-01"
        ), reverse=True)
        
        return timeline
