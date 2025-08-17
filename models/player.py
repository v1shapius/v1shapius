from sqlalchemy import Column, Integer, String, BigInteger, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Player(Base, TimestampMixin):
    """Player model representing a Discord user"""
    
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    discriminator = Column(String(4), nullable=True)  # Discord discriminator (deprecated but kept for compatibility)
    display_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    matches_as_player1 = relationship("Match", foreign_keys="Match.player1_id", back_populates="player1")
    matches_as_player2 = relationship("Match", foreign_keys="Match.player2_id", back_populates="player2")
    ratings = relationship("Rating", back_populates="player")
    
    def __repr__(self):
        return f"<Player(id={self.id}, discord_id={self.discord_id}, username='{self.username}')>"
    
    @property
    def current_rating(self):
        """Get current active rating"""
        if self.ratings:
            return max(self.ratings, key=lambda r: r.created_at)
        return None