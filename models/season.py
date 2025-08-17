from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from datetime import datetime, timedelta

class Season(Base, TimestampMixin):
    __tablename__ = "seasons"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Season status
    is_active = Column(Boolean, default=True, nullable=False)
    is_ending = Column(Boolean, default=False, nullable=False)  # New: season is ending
    is_rating_locked = Column(Boolean, default=False, nullable=False)  # New: rating calculation locked
    
    # Season end management
    season_end_warning_sent = Column(Boolean, default=False, nullable=False)  # New: warning sent to active players
    new_matches_blocked = Column(Boolean, default=False, nullable=False)  # New: new matches blocked
    rating_calculation_locked = Column(Boolean, default=False, nullable=False)  # New: rating updates blocked
    
    # Glicko-2 parameters
    tau = Column(Float, default=0.5, nullable=False)  # System parameter
    rating_volatility = Column(Float, default=0.06, nullable=False)  # Initial volatility
    
    # Relationships
    matches = relationship("Match", back_populates="season")
    ratings = relationship("Rating", back_populates="season")
    
    def __repr__(self):
        return f"<Season(id={self.id}, name={self.name}, active={self.is_active})>"
    
    @property
    def days_until_end(self) -> int:
        """Calculate days until season ends"""
        return (self.end_date - datetime.utcnow()).days
    
    @property
    def is_ending_soon(self) -> bool:
        """Check if season is ending within 7 days"""
        return self.days_until_end <= 7 and self.days_until_end > 0
    
    @property
    def should_block_new_matches(self) -> bool:
        """Check if new matches should be blocked"""
        return self.is_ending_soon or self.new_matches_blocked
    
    @property
    def should_lock_rating_calculation(self) -> bool:
        """Check if rating calculation should be locked"""
        return self.is_ending_soon or self.rating_calculation_locked
    
    def mark_as_ending(self):
        """Mark season as ending"""
        self.is_ending = True
        self.is_rating_locked = True
    
    def block_new_matches(self):
        """Block creation of new matches"""
        self.new_matches_blocked = True
    
    def lock_rating_calculation(self):
        """Lock rating calculation"""
        self.rating_calculation_locked = True
    
    def end_season(self):
        """End the season"""
        self.is_active = False
        self.is_ending = False
        self.new_matches_blocked = False
        self.rating_calculation_locked = False
    
    def get_status_description(self) -> str:
        """Get human-readable season status"""
        if not self.is_active:
            return "Завершен"
        elif self.is_ending:
            return "Завершается"
        elif self.is_ending_soon:
            return f"Завершается через {self.days_until_end} дней"
        else:
            return "Активен"
    
    def get_blocking_reason(self) -> str:
        """Get reason why new matches are blocked"""
        if not self.is_active:
            return "Сезон завершен"
        elif self.is_ending:
            return "Сезон завершается"
        elif self.is_ending_soon:
            return f"Сезон завершается через {self.days_until_end} дней"
        elif self.new_matches_blocked:
            return "Создание новых матчей временно заблокировано"
        else:
            return "Нет ограничений"