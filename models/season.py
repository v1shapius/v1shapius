from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from datetime import datetime

class Season(Base, TimestampMixin):
    """Season model for organizing matches and ratings"""
    
    __tablename__ = 'seasons'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # Null for active seasons
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Season settings
    initial_rating = Column(Integer, default=1500, nullable=False)
    k_factor_new = Column(Integer, default=40, nullable=False)
    k_factor_established = Column(Integer, default=20, nullable=False)
    established_threshold = Column(Integer, default=30, nullable=False)
    
    # Relationships
    ratings = relationship("Rating", back_populates="season")
    
    def __repr__(self):
        return f"<Season(id={self.id}, name='{self.name}', active={self.is_active})>"
    
    @property
    def duration_days(self):
        """Calculate season duration in days"""
        if self.end_date:
            return (self.end_date - self.start_date).days
        return None
    
    def end_season(self):
        """Mark season as ended"""
        self.is_active = False
        self.end_date = datetime.utcnow()
    
    def is_current(self):
        """Check if this is the current active season"""
        return self.is_active