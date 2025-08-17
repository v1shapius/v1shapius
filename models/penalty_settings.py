from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class PenaltySettings(Base, TimestampMixin):
    __tablename__ = "penalty_settings"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False, unique=True)
    
    # Legacy field for backward compatibility
    restart_penalty = Column(Integer, default=30, nullable=False)  # seconds
    
    # Detailed restart penalty configuration
    restart_penalties = Column(JSON, default={
        "free_restarts": 2,  # Number of free restarts
        "penalty_tiers": {   # Penalty for each restart after free ones
            "3": 5,          # 3rd restart: +5 seconds
            "4": 15,         # 4th restart: +15 seconds
            "5": 999         # 5th restart: +999 seconds
        }
    }, nullable=False)
    
    # Guild configuration
    match_channel_id = Column(BigInteger, nullable=True)  # Channel for match creation
    leaderboard_channel_id = Column(BigInteger, nullable=True)  # Channel for leaderboard updates
    audit_channel_id = Column(BigInteger, nullable=True)  # Channel for audit logs
    voice_category_id = Column(BigInteger, nullable=True)  # Category for voice channels
    
    # Instructions message
    instructions_message_id = Column(BigInteger, nullable=True)  # ID of pinned instructions message
    
    def get_penalty_for_restart(self, restart_count: int) -> int:
        """Calculate penalty for a specific restart count"""
        if restart_count <= self.restart_penalties.get("free_restarts", 0):
            return 0
        
        # Get penalty from tiers
        penalty_tiers = self.restart_penalties.get("penalty_tiers", {})
        
        # Find the appropriate tier
        for tier in sorted(penalty_tiers.keys(), key=int, reverse=True):
            if restart_count >= int(tier):
                return penalty_tiers[tier]
        
        # Fallback to legacy penalty if no tier found
        return self.restart_penalty
    
    def calculate_total_penalty(self, restart_count: int) -> int:
        """Calculate total penalty for all restarts"""
        total_penalty = 0
        for i in range(1, restart_count + 1):
            total_penalty += self.get_penalty_for_restart(i)
        return total_penalty
    
    def __repr__(self):
        return f"<PenaltySettings(guild_id={self.guild_id}, free_restarts={self.restart_penalties.get('free_restarts', 0)})>"