from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class MatchFormat(enum.Enum):
    """Match format enumeration"""
    BO1 = "bo1"
    BO2 = "bo2" 
    BO3 = "bo3"

class MatchStatus(enum.Enum):
    """Match status enumeration"""
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MatchStage(enum.Enum):
    """Match stage enumeration"""
    WAITING_READINESS = "waiting_readiness"
    WAITING_DRAFT = "waiting_draft"
    WAITING_FIRST_PLAYER = "waiting_first_player"
    PREPARING_GAME = "preparing_game"
    GAME_IN_PROGRESS = "game_in_progress"
    WAITING_CONFIRMATION = "waiting_confirmation"
    MATCH_COMPLETE = "match_complete"

class Match(Base, TimestampMixin):
    """Match model representing a game between two players"""
    
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    discord_guild_id = Column(BigInteger, nullable=False, index=True)
    discord_channel_id = Column(BigInteger, nullable=False, index=True)
    discord_voice_channel_id = Column(BigInteger, nullable=True, index=True)
    
    player1_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player2_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    
    format = Column(Enum(MatchFormat), nullable=False)
    status = Column(Enum(MatchStatus), default=MatchStatus.WAITING, nullable=False)
    current_stage = Column(Enum(MatchStage), default=MatchStage.WAITING_READINESS, nullable=False)
    
    draft_link = Column(String(500), nullable=True)
    first_player_id = Column(Integer, ForeignKey('players.id'), nullable=True)
    
    # Relationships
    player1 = relationship("Player", foreign_keys=[player1_id], back_populates="matches_as_player1")
    player2 = relationship("Player", foreign_keys=[player2_id], back_populates="matches_as_player2")
    first_player = relationship("Player", foreign_keys=[first_player_id])
    game_results = relationship("GameResult", back_populates="match")
    states = relationship("MatchState", back_populates="match")
    
    def __repr__(self):
        return f"<Match(id={self.id}, format={self.format.value}, status={self.status.value})>"
    
    @property
    def is_completed(self):
        """Check if match is completed"""
        return self.status == MatchStatus.COMPLETED
    
    @property
    def winner_id(self):
        """Get winner player ID based on format and results"""
        if not self.is_completed:
            return None
            
        if self.format == MatchFormat.BO1:
            # For BO1, winner is player with better time
            if self.game_results:
                result = self.game_results[0]
                if result.player1_time < result.player2_time:
                    return self.player1_id
                else:
                    return self.player2_id
        elif self.format == MatchFormat.BO2:
            # For BO2, sum up times from both games
            if len(self.game_results) == 2:
                total_time1 = sum(r.player1_time for r in self.game_results)
                total_time2 = sum(r.player2_time for r in self.game_results)
                return self.player1_id if total_time1 < total_time2 else self.player2_id
        elif self.format == MatchFormat.BO3:
            # For BO3, count wins
            wins1 = sum(1 for r in self.game_results if r.player1_time < r.player2_time)
            wins2 = sum(1 for r in self.game_results if r.player2_time < r.player1_time)
            if wins1 > wins2:
                return self.player1_id
            elif wins2 > wins1:
                return self.player2_id
            # If tied, it's a draw
            return None
        
        return None

class MatchState(Base, TimestampMixin):
    """Match state model for tracking match progress"""
    
    __tablename__ = 'match_states'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    stage = Column(Enum(MatchStage), nullable=False)
    data = Column(JSON, nullable=True)  # Store stage-specific data
    notes = Column(Text, nullable=True)
    
    # Relationships
    match = relationship("Match", back_populates="states")
    
    def __repr__(self):
        return f"<MatchState(id={self.id}, match_id={self.match_id}, stage={self.stage.value})>"