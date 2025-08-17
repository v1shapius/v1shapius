import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for Discord Rating Bot"""
    
    # Discord Bot Token
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/discord_bot")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Bot Settings
    BOT_PREFIX: str = os.getenv("BOT_PREFIX", "!")
    DEFAULT_LOCALE: str = os.getenv("DEFAULT_LOCALE", "en")
    
    # Match Settings
    DEFAULT_RESTART_PENALTY: int = int(os.getenv("DEFAULT_RESTART_PENALTY", "30"))  # seconds
    VOICE_CHANNEL_DELETE_DELAY: int = int(os.getenv("VOICE_CHANNEL_DELAY", "300"))  # 5 minutes
    CONFIRMATION_TIMEOUT: int = int(os.getenv("CONFIRMATION_TIMEOUT", "300"))  # 5 minutes
    
    # Rating System
    INITIAL_RATING: int = int(os.getenv("INITIAL_RATING", "1500"))
    K_FACTOR_NEW: int = int(os.getenv("K_FACTOR_NEW", "40"))
    K_FACTOR_ESTABLISHED: int = int(os.getenv("K_FACTOR_ESTABLISHED", "20"))
    ESTABLISHED_THRESHOLD: int = int(os.getenv("ESTABLISHED_THRESHOLD", "30"))
    
    # Season Settings
    SEASON_DURATION_DAYS: int = int(os.getenv("SEASON_DURATION_DAYS", "90"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values"""
        required_fields = ["DISCORD_TOKEN", "DATABASE_URL"]
        for field in required_fields:
            value = getattr(cls, field)
            if not value:
                raise ValueError(f"Missing required configuration: {field}")
        return True
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with validation"""
        if not cls.DATABASE_URL:
            raise ValueError("Database URL not configured")
        return cls.DATABASE_URL
    
    @classmethod
    def get_discord_token(cls) -> str:
        """Get Discord token with validation"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("Discord token not configured")
        return cls.DISCORD_TOKEN