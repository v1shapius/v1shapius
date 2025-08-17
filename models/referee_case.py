from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class CaseType(enum.Enum):
    DRAFT_DISPUTE = "draft_dispute"
    STREAM_ISSUE = "stream_issue"
    TIME_DISPUTE = "time_dispute"
    RESULT_DISPUTE = "result_dispute"
    RULE_VIOLATION = "rule_violation"
    TECHNICAL_ISSUE = "technical_issue"
    OTHER = "other"

class CaseStatus(enum.Enum):
    OPENED = "opened"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ResolutionType(enum.Enum):
    CONTINUE_MATCH = "continue_match"
    MODIFY_RESULTS = "modify_results"
    REPLAY_GAME = "replay_game"
    ANNULL_MATCH = "annull_match"
    WARNING_ISSUED = "warning_issued"
    OTHER = "other"

class RefereeCase(Base, TimestampMixin):
    __tablename__ = "referee_cases"
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    referee_id = Column(BigInteger, nullable=True)  # Discord ID of assigned referee
    
    # Case information
    case_type = Column(Enum(CaseType), nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.OPENED, nullable=False)
    
    # Problem description
    reported_by = Column(BigInteger, nullable=False)  # Discord ID of player who reported
    problem_description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)  # Links, screenshots, etc.
    
    # Referee actions
    referee_notes = Column(Text, nullable=True)
    resolution_type = Column(Enum(ResolutionType), nullable=True)
    resolution_details = Column(Text, nullable=True)
    resolution_time = Column(BigInteger, nullable=True)
    
    # Additional data
    stage_when_reported = Column(String(50), nullable=False)  # Match stage when reported
    additional_data = Column(JSON, nullable=True)  # Flexible data storage
    
    # Relationships
    match = relationship("Match", back_populates="referee_cases")
    
    def __repr__(self):
        return f"<RefereeCase(id={self.id}, match_id={self.match_id}, type={self.case_type.value}, status={self.status.value})>"
    
    def assign_referee(self, referee_id: int):
        """Assign a referee to the case"""
        self.referee_id = referee_id
        self.status = CaseStatus.ASSIGNED
    
    def start_resolution(self):
        """Mark case as in progress"""
        self.status = CaseStatus.IN_PROGRESS
    
    def resolve_case(self, resolution_type: ResolutionType, details: str, notes: str = None):
        """Resolve the case"""
        self.resolution_type = resolution_type
        self.resolution_details = details
        self.referee_notes = notes
        self.resolution_time = int(__import__('time').time())
        self.status = CaseStatus.RESOLVED
    
    def close_case(self):
        """Close the case"""
        self.status = CaseStatus.CLOSED
    
    def is_resolved(self) -> bool:
        """Check if case is resolved"""
        return self.status in [CaseStatus.RESOLVED, CaseStatus.CLOSED]
    
    def can_be_assigned(self) -> bool:
        """Check if case can be assigned to a referee"""
        return self.status == CaseStatus.OPENED
    
    def get_case_summary(self) -> str:
        """Get a summary of the case"""
        summary = f"**Тип**: {self.case_type.value}\n"
        summary += f"**Статус**: {self.status.value}\n"
        summary += f"**Этап**: {self.stage_when_reported}\n"
        summary += f"**Проблема**: {self.problem_description}\n"
        
        if self.referee_id:
            summary += f"**Судья**: <@{self.referee_id}>\n"
        
        if self.resolution_type:
            summary += f"**Решение**: {self.resolution_type.value}\n"
            if self.resolution_details:
                summary += f"**Детали**: {self.resolution_details}\n"
        
        return summary