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
    
    # Achievement System
    ACHIEVEMENT_NOTIFICATIONS: bool = os.getenv("ACHIEVEMENT_NOTIFICATIONS", "true").lower() == "true"
    ACHIEVEMENT_DM_ENABLED: bool = os.getenv("ACHIEVEMENT_DM_ENABLED", "true").lower() == "true"
    ACHIEVEMENT_CHECK_INTERVAL: int = int(os.getenv("ACHIEVEMENT_CHECK_INTERVAL", "300"))  # 5 minutes
    
    # Tournament System
    TOURNAMENT_AUTO_START: bool = os.getenv("TOURNAMENT_AUTO_START", "true").lower() == "true"
    TOURNAMENT_MIN_PARTICIPANTS: int = int(os.getenv("TOURNAMENT_MIN_PARTICIPANTS", "4"))
    TOURNAMENT_REGISTRATION_DAYS: int = int(os.getenv("TOURNAMENT_REGISTRATION_DAYS", "7"))
    TOURNAMENT_CHECK_INTERVAL: int = int(os.getenv("TOURNAMENT_CHECK_INTERVAL", "600"))  # 10 minutes
    
    # Security System
    SECURITY_CHECK_INTERVAL: int = int(os.getenv("SECURITY_CHECK_INTERVAL", "300"))  # 5 minutes
    SUSPICIOUS_RATING_THRESHOLD: int = int(os.getenv("SUSPICIOUS_RATING_THRESHOLD", "100"))
    SUSPICIOUS_MATCH_DURATION: int = int(os.getenv("SUSPICIOUS_MATCH_DURATION", "120"))  # 2 minutes
    SUSPICIOUS_WIN_RATE_THRESHOLD: float = float(os.getenv("SUSPICIOUS_WIN_RATE_THRESHOLD", "0.9"))
    SECURITY_NOTIFICATIONS_ENABLED: bool = os.getenv("SECURITY_NOTIFICATIONS_ENABLED", "true").lower() == "true"
    
    # Monitoring and Analytics
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Performance Settings
    MAX_CONCURRENT_MATCHES: int = int(os.getenv("MAX_CONCURRENT_MATCHES", "100"))
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
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
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL with validation"""
        if not cls.REDIS_URL:
            raise ValueError("Redis URL not configured")
        return cls.REDIS_URL
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "production").lower() == "development"
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return os.getenv("ENVIRONMENT", "production").lower() == "production"