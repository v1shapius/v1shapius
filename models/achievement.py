from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime

class AchievementType(enum.Enum):
    """Achievement type enumeration"""
    FIRST_MATCH = "first_match"
    FIRST_WIN = "first_win"
    STREAK_3 = "streak_3"
    STREAK_5 = "streak_5"
    STREAK_10 = "streak_10"
    RATING_1600 = "rating_1600"
    RATING_1800 = "rating_1800"
    RATING_2000 = "rating_2000"
    SEASON_WINNER = "season_winner"
    MATCHES_10 = "matches_10"
    MATCHES_50 = "matches_50"
    MATCHES_100 = "matches_100"
    REFEREE_HELP = "referee_help"
    PERFECT_MATCH = "perfect_match"
    COMEBACK_WIN = "comeback_win"

class Achievement(Base, TimestampMixin):
    """Achievement model for tracking player accomplishments"""
    
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    achievement_type = Column(Enum(AchievementType), nullable=False)
    unlocked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_hidden = Column(Boolean, default=False, nullable=False)  # Hidden until unlocked
    
    # Relationships
    player = relationship("Player", back_populates="achievements")
    
    def __repr__(self):
        return f"<Achievement(player_id={self.player_id}, type={self.achievement_type.value})>"
    
    @property
    def display_name(self) -> str:
        """Get human-readable achievement name"""
        names = {
            AchievementType.FIRST_MATCH: "Первая игра",
            AchievementType.FIRST_WIN: "Первая победа",
            AchievementType.STREAK_3: "Серия из 3 побед",
            AchievementType.STREAK_5: "Серия из 5 побед",
            AchievementType.STREAK_10: "Серия из 10 побед",
            AchievementType.RATING_1600: "Рейтинг 1600+",
            AchievementType.RATING_1800: "Рейтинг 1800+",
            AchievementType.RATING_2000: "Рейтинг 2000+",
            AchievementType.SEASON_WINNER: "Победитель сезона",
            AchievementType.MATCHES_10: "10 игр",
            AchievementType.MATCHES_50: "50 игр",
            AchievementType.MATCHES_100: "100 игр",
            AchievementType.REFEREE_HELP: "Помощь судье",
            AchievementType.PERFECT_MATCH: "Идеальная игра",
            AchievementType.COMEBACK_WIN: "Победа в трудной ситуации"
        }
        return names.get(self.achievement_type, self.achievement_type.value)
    
    @property
    def description(self) -> str:
        """Get achievement description"""
        descriptions = {
            AchievementType.FIRST_MATCH: "Сыграйте свою первую игру",
            AchievementType.FIRST_WIN: "Одержите первую победу",
            AchievementType.STREAK_3: "Выиграйте 3 игры подряд",
            AchievementType.STREAK_5: "Выиграйте 5 игр подряд",
            AchievementType.STREAK_10: "Выиграйте 10 игр подряд",
            AchievementType.RATING_1600: "Достигните рейтинга 1600",
            AchievementType.RATING_1800: "Достигните рейтинга 1800",
            AchievementType.RATING_2000: "Достигните рейтинга 2000",
            AchievementType.SEASON_WINNER: "Станьте победителем сезона",
            AchievementType.MATCHES_10: "Сыграйте 10 игр",
            AchievementType.MATCHES_50: "Сыграйте 50 игр",
            AchievementType.MATCHES_100: "Сыграйте 100 игр",
            AchievementType.REFEREE_HELP: "Помогите судье разрешить спор",
            AchievementType.PERFECT_MATCH: "Выиграйте игру без рестартов",
            AchievementType.COMEBACK_WIN: "Выиграйте после проигрыша первой игры"
        }
        return descriptions.get(self.achievement_type, "Описание недоступно")
    
    @property
    def icon(self) -> str:
        """Get achievement icon emoji"""
        icons = {
            AchievementType.FIRST_MATCH: "🎮",
            AchievementType.FIRST_WIN: "🏆",
            AchievementType.STREAK_3: "🔥",
            AchievementType.STREAK_5: "🔥🔥",
            AchievementType.STREAK_10: "🔥🔥🔥",
            AchievementType.RATING_1600: "⭐",
            AchievementType.RATING_1800: "⭐⭐",
            AchievementType.RATING_2000: "⭐⭐⭐",
            AchievementType.SEASON_WINNER: "👑",
            AchievementType.MATCHES_10: "📊",
            AchievementType.MATCHES_50: "📈",
            AchievementType.MATCHES_100: "🏅",
            AchievementType.REFEREE_HELP: "⚖️",
            AchievementType.PERFECT_MATCH: "💎",
            AchievementType.COMEBACK_WIN: "🔄"
        }
        return icons.get(self.achievement_type, "🏅")

class AchievementProgress(Base, TimestampMixin):
    """Achievement progress tracking for hidden achievements"""
    
    __tablename__ = "achievement_progress"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    achievement_type = Column(Enum(AchievementType), nullable=False)
    current_progress = Column(Integer, default=0, nullable=False)
    target_progress = Column(Integer, nullable=False)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="achievement_progress")
    
    def __repr__(self):
        return f"<AchievementProgress(player_id={self.player_id}, type={self.achievement_type.value}, progress={self.current_progress}/{self.target_progress})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if achievement is completed"""
        return self.current_progress >= self.target_progress
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.target_progress == 0:
            return 0.0
        return min(100.0, (self.current_progress / self.target_progress) * 100)
    
    def update_progress(self, increment: int = 1):
        """Update progress towards achievement"""
        self.current_progress += increment
        self.last_updated = datetime.utcnow()
        
        if self.is_completed:
            # Achievement unlocked!
            return True
        return False