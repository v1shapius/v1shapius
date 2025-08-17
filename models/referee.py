from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Referee(Base, TimestampMixin):
    __tablename__ = "referees"
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    
    # Referee permissions and status
    is_active = Column(Boolean, default=True, nullable=False)
    can_annul_matches = Column(Boolean, default=True, nullable=False)
    can_modify_results = Column(Boolean, default=True, nullable=False)
    can_resolve_disputes = Column(Boolean, default=True, nullable=False)
    
    # Referee statistics
    cases_resolved = Column(Integer, default=0, nullable=False)
    matches_annulled = Column(Integer, default=0, nullable=False)
    
    # Additional information
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Referee(discord_id={self.discord_id}, username={self.username}, guild_id={self.guild_id})>"
    
    def can_handle_case(self, case_type: str) -> bool:
        """Check if referee can handle specific type of case"""
        if not self.is_active:
            return False
            
        if case_type == "annul_match":
            return self.can_annul_matches
        elif case_type == "modify_results":
            return self.can_modify_results
        elif case_type == "resolve_dispute":
            return self.can_resolve_disputes
            
        return True
    
    def increment_cases_resolved(self):
        """Increment resolved cases counter"""
        self.cases_resolved += 1
    
    def increment_matches_annulled(self):
        """Increment annulled matches counter"""
        self.matches_annulled += 1