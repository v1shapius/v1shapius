from sqlalchemy import Column, Integer, BigInteger, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class GameResult(Base, TimestampMixin):
    """Game result model for individual games within a match"""
    
    __tablename__ = 'game_results'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    game_number = Column(Integer, nullable=False)  # 1, 2, or 3 for BO2/BO3
    
    # Player 1 results (input by player 2)
    player1_time = Column(Float, nullable=False)  # Time in seconds
    player1_restarts = Column(Integer, default=0, nullable=False)
    player1_penalties = Column(Float, default=0.0, nullable=False)  # Penalty time in seconds
    player1_final_time = Column(Float, nullable=False)  # Time + penalties
    
    # Player 2 results (input by player 1)
    player2_time = Column(Float, nullable=False)  # Time in seconds
    player2_restarts = Column(Integer, default=0, nullable=False)
    player2_penalties = Column(Float, default=0.0, nullable=False)  # Penalty time in seconds
    player2_final_time = Column(Float, nullable=False)  # Time + penalties
    
    # Confirmation status
    player1_confirmed = Column(Integer, ForeignKey('players.id'), nullable=True)
    player2_confirmed = Column(Integer, ForeignKey('players.id'), nullable=True)
    
    # Notes or disputes
    notes = Column(Text, nullable=True)
    
    # Relationships
    match = relationship("Match", back_populates="game_results")
    player1_confirmer = relationship("Player", foreign_keys=[player1_confirmed])
    player2_confirmer = relationship("Player", foreign_keys=[player2_confirmed])
    
    def __repr__(self):
        return f"<GameResult(id={self.id}, match_id={self.match_id}, game_number={self.game_number})>"
    
    @property
    def winner_id(self):
        """Get winner player ID for this game"""
        if self.player1_final_time < self.player2_final_time:
            return self.match.player1_id
        elif self.player2_final_time < self.player1_final_time:
            return self.match.player2_id
        else:
            return None  # Tie
    
    @property
    def is_confirmed(self):
        """Check if both players confirmed the results"""
        return self.player1_confirmed is not None and self.player2_confirmed is not None
    
    def calculate_penalties(self, restart_penalty_seconds: float):
        """Calculate penalties based on restart count"""
        self.player1_penalties = self.player1_restarts * restart_penalty_seconds
        self.player2_penalties = self.player2_restarts * restart_penalty_seconds
        
        self.player1_final_time = self.player1_time + self.player1_penalties
        self.player2_final_time = self.player2_time + self.player2_penalties