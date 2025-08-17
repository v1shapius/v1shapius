from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime, timedelta

class TournamentStatus(enum.Enum):
    """Tournament status enumeration"""
    REGISTRATION = "registration"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TournamentFormat(enum.Enum):
    """Tournament format enumeration"""
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    SWISS_SYSTEM = "swiss_system"
    ROUND_ROBIN = "round_robin"

class Tournament(Base, TimestampMixin):
    """Tournament model for organizing competitive events"""
    
    __tablename__ = "tournaments"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    guild_id = Column(BigInteger, nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=True)
    
    # Tournament settings
    status = Column(Enum(TournamentStatus), default=TournamentStatus.REGISTRATION, nullable=False)
    format = Column(Enum(TournamentFormat), nullable=False)
    max_participants = Column(Integer, nullable=True)  # None for unlimited
    min_participants = Column(Integer, default=4, nullable=False)
    
    # Timing
    registration_start = Column(DateTime, nullable=False)
    registration_end = Column(DateTime, nullable=False)
    tournament_start = Column(DateTime, nullable=True)
    tournament_end = Column(DateTime, nullable=True)
    
    # Rules and settings
    match_format = Column(String(10), default="bo3", nullable=False)  # bo1, bo3, bo5
    rules = Column(Text, nullable=True)
    prize_pool = Column(Text, nullable=True)
    
    # Tournament data
    bracket_data = Column(JSON, nullable=True)  # Tournament bracket structure
    current_round = Column(Integer, default=0, nullable=False)
    total_rounds = Column(Integer, nullable=True)
    
    # Relationships
    season = relationship("Season")
    participants = relationship("TournamentParticipant", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("TournamentMatch", back_populates="tournament", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tournament(id={self.id}, name='{self.name}', status={self.status.value})>"
    
    @property
    def is_registration_open(self) -> bool:
        """Check if registration is currently open"""
        now = datetime.utcnow()
        return (self.status == TournamentStatus.REGISTRATION and 
                self.registration_start <= now <= self.registration_end)
    
    @property
    def can_start(self) -> bool:
        """Check if tournament can start"""
        if self.status != TournamentStatus.REGISTRATION:
            return False
        
        participant_count = len([p for p in self.participants if p.is_active])
        return participant_count >= self.min_participants
    
    @property
    def participant_count(self) -> int:
        """Get current participant count"""
        return len([p for p in self.participants if p.is_active])
    
    @property
    def is_full(self) -> bool:
        """Check if tournament is full"""
        if self.max_participants is None:
            return False
        return self.participant_count >= self.max_participants
    
    def start_tournament(self):
        """Start the tournament"""
        if not self.can_start:
            raise ValueError("Tournament cannot start yet")
        
        self.status = TournamentStatus.ACTIVE
        self.tournament_start = datetime.utcnow()
        self.current_round = 1
        
        # Generate bracket based on format
        self.generate_bracket()
    
    def generate_bracket(self):
        """Generate tournament bracket"""
        if self.format == TournamentFormat.SINGLE_ELIMINATION:
            self.generate_single_elimination_bracket()
        elif self.format == TournamentFormat.DOUBLE_ELIMINATION:
            self.generate_double_elimination_bracket()
        # Add other formats as needed
    
    def generate_single_elimination_bracket(self):
        """Generate single elimination bracket"""
        active_participants = [p for p in self.participants if p.is_active]
        participant_count = len(active_participants)
        
        # Calculate rounds needed
        import math
        self.total_rounds = math.ceil(math.log2(participant_count))
        
        # Create bracket structure
        self.bracket_data = {
            "rounds": self.total_rounds,
            "matches": []
        }
        
        # Generate first round matches
        for i in range(0, participant_count, 2):
            if i + 1 < participant_count:
                match_data = {
                    "round": 1,
                    "match_number": i // 2 + 1,
                    "player1_id": active_participants[i].player_id,
                    "player2_id": active_participants[i + 1].player_id,
                    "winner_id": None,
                    "status": "pending"
                }
                self.bracket_data["matches"].append(match_data)
    
    def complete_tournament(self):
        """Complete the tournament"""
        self.status = TournamentStatus.COMPLETED
        self.tournament_end = datetime.utcnow()

class TournamentParticipant(Base, TimestampMixin):
    """Tournament participant model"""
    
    __tablename__ = "tournament_participants"
    
    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Participant status
    is_active = Column(Boolean, default=True, nullable=False)
    registration_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Tournament performance
    final_place = Column(Integer, nullable=True)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="participants")
    player = relationship("Player", back_populates="tournament_participations")
    
    def __repr__(self):
        return f"<TournamentParticipant(tournament_id={self.tournament_id}, player_id={self.player_id})>"
    
    @property
    def total_matches(self) -> int:
        """Get total matches played"""
        return self.matches_won + self.matches_lost
    
    @property
    def win_rate(self) -> float:
        """Get win rate percentage"""
        if self.total_matches == 0:
            return 0.0
        return (self.matches_won / self.total_matches) * 100

class TournamentMatch(Base, TimestampMixin):
    """Tournament match model"""
    
    __tablename__ = "tournament_matches"
    
    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)  # Link to regular match
    
    # Match information
    round_number = Column(Integer, nullable=False)
    match_number = Column(Integer, nullable=False)
    player1_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Match status
    status = Column(String(20), default="pending", nullable=False)  # pending, active, completed, cancelled
    winner_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    
    # Match details
    match_format = Column(String(10), nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="matches")
    match = relationship("Match")
    player1 = relationship("Player", foreign_keys=[player1_id])
    player2 = relationship("Player", foreign_keys=[player2_id])
    winner = relationship("Player", foreign_keys=[winner_id])
    
    def __repr__(self):
        return f"<TournamentMatch(id={self.id}, tournament_id={self.tournament_id}, round={self.round_number})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if match is completed"""
        return self.status == "completed"
    
    @property
    def is_active(self) -> bool:
        """Check if match is currently active"""
        return self.status == "active"
    
    def start_match(self):
        """Start the match"""
        self.status = "active"
        self.actual_start_time = datetime.utcnow()
    
    def complete_match(self, winner_id: int):
        """Complete the match"""
        self.status = "completed"
        self.winner_id = winner_id
        self.actual_end_time = datetime.utcnow()
        
        # Update participant statistics
        if winner_id == self.player1_id:
            self.update_participant_stats(self.player1_id, True)
            self.update_participant_stats(self.player2_id, False)
        else:
            self.update_participant_stats(self.player2_id, True)
            self.update_participant_stats(self.player1_id, False)
    
    def update_participant_stats(self, player_id: int, won: bool):
        """Update participant statistics"""
        from .tournament import TournamentParticipant
        
        participant = TournamentParticipant.query.filter_by(
            tournament_id=self.tournament_id,
            player_id=player_id
        ).first()
        
        if participant:
            if won:
                participant.matches_won += 1
            else:
                participant.matches_lost += 1