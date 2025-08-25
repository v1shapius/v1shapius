import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config.config import Config
from models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for handling PostgreSQL connections and operations"""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.sync_session_maker = None
        
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                Config.DATABASE_URL,
                echo=False,  # Set to True for SQL debugging
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True
            )
            
            # Create async session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("Database connection established successfully")
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized")
        
        return self.async_session_maker()
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def initialize_guild_settings(self, guild_id: int):
        """Initialize default settings for a new guild"""
        from models.penalty_settings import PenaltySettings
        
        session = await self.get_session()
        async with session as session:
            # Check if guild settings already exist
            existing = await session.get(PenaltySettings, guild_id)
            if not existing:
                # Create default penalty settings
                penalty_settings = PenaltySettings(
                    discord_guild_id=guild_id,
                    restart_penalty_seconds=Config.DEFAULT_RESTART_PENALTY,
                    max_restarts_before_penalty=0,
                    description="Default penalty settings"
                )
                session.add(penalty_settings)
                await session.commit()
                logger.info(f"Created default penalty settings for guild {guild_id}")
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            session = await self.get_session()
            async with session as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def execute_query(self, query: str, params: dict = None):
        """Execute a raw SQL query"""
        session = await self.get_session()
        async with session as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result
    
    async def get_player_by_discord_id(self, discord_id: int):
        """Get player by Discord ID"""
        from models.player import Player
        
        session = await self.get_session()
        async with session as session:
            result = await session.execute(
                text("SELECT * FROM players WHERE discord_id = :discord_id"),
                {"discord_id": discord_id}
            )
            row = result.fetchone()
            if row:
                return Player(**dict(row))
            return None
    
    async def create_player(self, discord_id: int, username: str, display_name: str = None):
        """Create a new player"""
        from models.player import Player
        
        session = await self.get_session()
        async with session as session:
            player = Player(
                discord_id=discord_id,
                username=username,
                display_name=display_name or username
            )
            session.add(player)
            await session.commit()
            await session.refresh(player)
            return player
    
    async def get_or_create_player(self, discord_id: int, username: str, display_name: str = None):
        """Get existing player or create new one"""
        player = await self.get_player_by_discord_id(discord_id)
        if not player:
            player = await self.create_player(discord_id, username, display_name)
        return player