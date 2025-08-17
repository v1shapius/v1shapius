from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
import time

class MatchFormat(enum.Enum):
    """Match format enumeration"""
    BO1 = "bo1"
    BO2 = "bo2"
    BO3 = "bo3"

class MatchStatus(enum.Enum):
    """Match status enumeration"""
    WAITING_PLAYERS = "waiting_players"
    WAITING_READINESS = "waiting_readiness"
    DRAFT_VERIFICATION = "draft_verification"
    FIRST_PLAYER_SELECTION = "first_player_selection"
    GAME_PREPARATION = "game_preparation"
    GAME_IN_PROGRESS = "game_in_progress"
    RESULT_CONFIRMATION = "result_confirmation"
    REFEREE_INTERVENTION = "referee_intervention"  # Status for referee cases
    COMPLETE = "complete"
    ANNULLED = "annulled"  # Status for annulled matches

class MatchStage(enum.Enum):
    """Match stage enumeration"""
    WAITING_READINESS = "waiting_readiness"
    DRAFT_VERIFICATION = "draft_verification"
    FIRST_PLAYER_SELECTION = "first_player_selection"
    GAME_PREPARATION = "game_preparation"
    GAME_IN_PROGRESS = "game_in_progress"
    RESULT_CONFIRMATION = "result_confirmation"
    REFEREE_INTERVENTION = "referee_intervention"

class Match(Base, TimestampMixin):
    """Match model representing a game between two players"""
    
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    format = Column(Enum(MatchFormat), nullable=False)
    status = Column(Enum(MatchStatus), nullable=False, default=MatchStatus.WAITING_PLAYERS)
    current_stage = Column(Enum(MatchStage), nullable=False, default=MatchStage.WAITING_READINESS)
    
    # Player information
    player1_id = Column(Integer, ForeignKey("players.id"))
    player2_id = Column(Integer, ForeignKey("players.id"))
    
    # Season and guild
    season_id = Column(Integer, ForeignKey("seasons.id"))
    guild_id = Column(BigInteger, nullable=False)
    
    # Discord channels
    thread_id = Column(BigInteger)
    voice_channel_id = Column(BigInteger)
    
    # Referee system
    referee_id = Column(BigInteger, nullable=True)  # Discord ID of assigned referee
    referee_intervention_stage = Column(Enum(MatchStage), nullable=True)  # Stage when referee was called
    referee_intervention_reason = Column(Text, nullable=True)  # Reason for referee intervention
    referee_intervention_time = Column(BigInteger, nullable=True)  # Timestamp when referee was called
    referee_resolution = Column(Text, nullable=True)  # How referee resolved the issue
    referee_resolution_time = Column(BigInteger, nullable=True)  # Timestamp when referee resolved
    
    # Match outcome
    winner_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    annulment_reason = Column(Text, nullable=True)  # Reason for match annulment
    
    # Relationships
    player1 = relationship("Player", foreign_keys=[player1_id])
    player2 = relationship("Player", foreign_keys=[player2_id])
    winner = relationship("Player", foreign_keys=[winner_id])
    season = relationship("Season")
    game_results = relationship("GameResult", back_populates="match", cascade="all, delete-orphan")
    match_states = relationship("MatchState", back_populates="match", cascade="all, delete-orphan")
    referee_cases = relationship("RefereeCase", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Match(id={self.id}, format={self.format.value}, status={self.status.value})>"
    
    def is_referee_needed(self) -> bool:
        """Check if match needs referee intervention"""
        return self.status == MatchStatus.REFEREE_INTERVENTION
    
    def can_call_referee(self) -> bool:
        """Check if referee can be called at current stage"""
        return self.status not in [MatchStatus.COMPLETE, MatchStatus.ANNULLED, MatchStatus.REFEREE_INTERVENTION]
    
    def call_referee(self, referee_id: int, reason: str):
        """Call referee for intervention"""
        self.referee_id = referee_id
        self.referee_intervention_stage = self.current_stage
        self.referee_intervention_reason = reason
        self.referee_intervention_time = int(time.time())
        self.status = MatchStatus.REFEREE_INTERVENTION
    
    def resolve_referee_intervention(self, resolution: str):
        """Resolve referee intervention"""
        self.referee_resolution = resolution
        self.referee_resolution_time = int(time.time())
        self.status = self.referee_intervention_stage  # Return to previous stage
    
    def annul_match(self, reason: str):
        """Annul the match"""
        self.status = MatchStatus.ANNULLED
        self.annulment_reason = reason
        self.referee_resolution = f"Матч аннулирован: {reason}"
        self.referee_resolution_time = int(time.time())

class MatchState(Base, TimestampMixin):
    """Match state model for tracking match progress"""
    
    __tablename__ = "match_states"
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    stage = Column(Enum(MatchStage), nullable=False)
    data = Column(Text, nullable=True)  # JSON data for stage-specific information
    
    # Relationships
    match = relationship("Match", back_populates="match_states")
    
    def __repr__(self):
        return f"<MatchState(id={self.id}, match_id={self.match_id}, stage={self.stage.value})>"