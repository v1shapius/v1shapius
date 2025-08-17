from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class PenaltySettings(Base, TimestampMixin):
    __tablename__ = "penalty_settings"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False, unique=True)
    restart_penalty = Column(Integer, default=30, nullable=False)  # seconds
    
    # Guild configuration
    match_channel_id = Column(BigInteger, nullable=True)  # Channel for match creation
    leaderboard_channel_id = Column(BigInteger, nullable=True)  # Channel for leaderboard updates
    audit_channel_id = Column(BigInteger, nullable=True)  # Channel for audit logs
    voice_category_id = Column(BigInteger, nullable=True)  # Category for voice channels
    
    # Instructions message
    instructions_message_id = Column(BigInteger, nullable=True)  # ID of pinned instructions message
    
    def __repr__(self):
        return f"<PenaltySettings(guild_id={self.guild_id}, restart_penalty={self.restart_penalty})>"