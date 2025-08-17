from sqlalchemy import Column, Integer, BigInteger, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Rating(Base, TimestampMixin):
    """Rating model for tracking player ratings over time"""
    
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    
    rating = Column(Float, nullable=False)
    games_played = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    draws = Column(Integer, default=0, nullable=False)
    
    # Rating change from last match
    rating_change = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    player = relationship("Player", back_populates="ratings")
    season = relationship("Season", back_populates="ratings")
    
    def __repr__(self):
        return f"<Rating(id={self.id}, player_id={self.player_id}, rating={self.rating})>"
    
    @property
    def win_rate(self):
        """Calculate win rate"""
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played
    
    def update_after_match(self, is_win: bool, is_draw: bool, rating_change: float):
        """Update rating statistics after a match"""
        self.games_played += 1
        if is_draw:
            self.draws += 1
        elif is_win:
            self.wins += 1
        else:
            self.losses += 1
        
        self.rating += rating_change
        self.rating_change = rating_change