from sqlalchemy import Column, Integer, BigInteger, Float, String
from .base import Base, TimestampMixin

class PenaltySettings(Base, TimestampMixin):
    """Penalty settings model for configuring restart penalties"""
    
    __tablename__ = 'penalty_settings'
    
    id = Column(Integer, primary_key=True)
    discord_guild_id = Column(BigInteger, nullable=False, index=True)
    
    # Penalty settings
    restart_penalty_seconds = Column(Float, default=30.0, nullable=False)
    max_restarts_before_penalty = Column(Integer, default=0, nullable=False)  # 0 = penalty from first restart
    
    # Additional settings
    description = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<PenaltySettings(id={self.id}, guild_id={self.discord_guild_id}, penalty={self.restart_penalty_seconds}s)>"
    
    def calculate_penalty(self, restart_count: int) -> float:
        """Calculate penalty time based on restart count"""
        if restart_count <= self.max_restarts_before_penalty:
            return 0.0
        return (restart_count - self.max_restarts_before_penalty) * self.restart_penalty_seconds