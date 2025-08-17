import pytest
import asyncio
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import RatingBot
from config.config import Config
from models.season import Season
from models.match import Match, MatchStatus, MatchFormat
from models.player import Player
from services.season_manager import SeasonManager

class TestRatingBot:
    """Test class for RatingBot"""
    
    @pytest.fixture
    def bot(self):
        """Create a test bot instance"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        
        bot = RatingBot()
        bot.db_manager = Mock()
        bot.season_manager = Mock()
        return bot
    
    @pytest.fixture
    def mock_guild(self):
        """Create a mock guild"""
        guild = Mock()
        guild.id = 123456789
        guild.name = "Test Guild"
        return guild
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = Mock()
        user.id = 987654321
        user.display_name = "Test User"
        user.bot = False
        return user
    
    def test_bot_initialization(self, bot):
        """Test bot initialization"""
        assert bot.command_prefix == Config.BOT_PREFIX
        assert bot.intents.message_content is True
        assert bot.intents.guilds is True
        assert bot.intents.voice_states is True
        assert bot.intents.members is True
    
    @pytest.mark.asyncio
    async def test_setup_hook(self, bot):
        """Test bot setup hook"""
        # Mock database initialization
        bot.db_manager.initialize = AsyncMock()
        
        # Mock cog loading
        bot.load_extension = AsyncMock()
        
        # Mock command syncing
        bot.tree.sync = AsyncMock()
        
        await bot.setup_hook()
        
        # Verify database was initialized
        bot.db_manager.initialize.assert_called_once()
        
        # Verify cogs were loaded
        assert bot.load_extension.call_count == 7  # All cogs
        
        # Verify commands were synced
        bot.tree.sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_ready(self, bot):
        """Test bot ready event"""
        # Mock guilds
        bot.guilds = [Mock(id=123, name="Test Guild")]
        
        # Mock presence change
        bot.change_presence = AsyncMock()
        
        # Mock season manager
        bot.season_manager = Mock()
        
        await bot.on_ready()
        
        # Verify presence was changed
        bot.change_presence.assert_called_once()
        
        # Verify guild count is correct
        assert len(bot.guilds) == 1
    
    @pytest.mark.asyncio
    async def test_on_guild_join(self, bot):
        """Test bot guild join event"""
        mock_guild = Mock()
        mock_guild.id = 123456789
        mock_guild.name = "Test Guild"
        
        # Mock guild settings initialization
        bot.db_manager.initialize_guild_settings = AsyncMock()
        
        await bot.on_guild_join(mock_guild)
        
        # Verify guild settings were initialized
        bot.db_manager.initialize_guild_settings.assert_called_once_with(mock_guild.id)
    
    @pytest.mark.asyncio
    async def test_on_guild_remove(self, bot):
        """Test bot guild remove event"""
        mock_guild = Mock()
        mock_guild.id = 123456789
        mock_guild.name = "Test Guild"
        
        await bot.on_guild_remove(mock_guild)
        
        # This should just log the event, no assertions needed
    
    @pytest.mark.asyncio
    async def test_on_command_error(self, bot):
        """Test bot command error handling"""
        mock_ctx = Mock()
        mock_ctx.send = AsyncMock()
        
        # Test MissingPermissions error
        error = commands.MissingPermissions(["administrator"])
        await bot.on_command_error(mock_ctx, error)
        mock_ctx.send.assert_called_with("❌ You don't have permission to use this command.")
        
        # Test BotMissingPermissions error
        mock_ctx.send.reset_mock()
        error = commands.BotMissingPermissions(["send_messages"])
        await bot.on_command_error(mock_ctx, error)
        mock_ctx.send.assert_called_with("❌ I don't have the required permissions to execute this command.")
        
        # Test generic error
        mock_ctx.send.reset_mock()
        error = Exception("Test error")
        await bot.on_command_error(mock_ctx, error)
        mock_ctx.send.assert_called_with("❌ An unexpected error occurred. Please try again later.")

class TestSeasonManager:
    """Test class for SeasonManager"""
    
    @pytest.fixture
    def season_manager(self):
        """Create a test season manager instance"""
        mock_bot = Mock()
        return SeasonManager(mock_bot)
    
    @pytest.fixture
    def mock_season(self):
        """Create a mock season"""
        season = Mock()
        season.id = 1
        season.name = "Test Season"
        season.is_active = True
        season.is_ending = False
        season.is_ending_soon = False
        season.season_end_warning_sent = False
        season.days_until_end = 10
        season.should_block_new_matches = False
        season.get_status_description.return_value = "Активен"
        season.get_blocking_reason.return_value = "Нет ограничений"
        return season
    
    @pytest.mark.asyncio
    async def test_can_create_new_match(self, season_manager, mock_season):
        """Test if new matches can be created"""
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
        
        # Mock database manager
        season_manager.db.get_session = AsyncMock()
        season_manager.db.get_session.return_value.__aenter__.return_value = mock_session
        
        can_create, reason = await season_manager.can_create_new_match(123456789)
        
        assert can_create is True
        assert reason == "Нет ограничений"
    
    @pytest.mark.asyncio
    async def test_can_create_new_match_blocked(self, season_manager, mock_season):
        """Test if new matches are blocked when season is ending"""
        # Mock season that blocks matches
        mock_season.should_block_new_matches = True
        mock_season.get_blocking_reason.return_value = "Сезон завершается через 3 дня"
        
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
        
        # Mock database manager
        season_manager.db.get_session = AsyncMock()
        season_manager.db.get_session.return_value.__aenter__.return_value = mock_session
        
        can_create, reason = await season_manager.can_create_new_match(123456789)
        
        assert can_create is False
        assert reason == "Сезон завершается через 3 дня"
    
    @pytest.mark.asyncio
    async def test_get_season_status(self, season_manager, mock_season):
        """Test getting season status"""
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
        
        # Mock database manager
        season_manager.db.get_session = AsyncMock()
        season_manager.db.get_session.return_value.__aenter__.return_value = mock_session
        
        season = await season_manager.get_season_status(123456789)
        
        assert season == mock_season
    
    @pytest.mark.asyncio
    async def test_get_season_status_no_season(self, season_manager):
        """Test getting season status when no season exists"""
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock database manager
        season_manager.db.get_session = AsyncMock()
        season_manager.db.get_session.return_value.__aenter__.return_value = mock_session
        
        season = await season_manager.get_season_status(123456789)
        
        assert season is None

class TestModels:
    """Test class for database models"""
    
    def test_match_format_enum(self):
        """Test MatchFormat enum values"""
        assert MatchFormat.BO1.value == "bo1"
        assert MatchFormat.BO2.value == "bo2"
        assert MatchFormat.BO3.value == "bo3"
    
    def test_match_status_enum(self):
        """Test MatchStatus enum values"""
        assert MatchStatus.WAITING_PLAYERS.value == "waiting_players"
        assert MatchStatus.COMPLETE.value == "complete"
        assert MatchStatus.ANNULLED.value == "annulled"
    
    def test_match_stage_enum(self):
        """Test MatchStage enum values"""
        assert MatchStage.WAITING_READINESS.value == "waiting_readiness"
        assert MatchStage.GAME_IN_PROGRESS.value == "game_in_progress"
        assert MatchStage.RESULT_CONFIRMATION.value == "result_confirmation"
    
    def test_season_properties(self):
        """Test Season model properties"""
        from datetime import datetime, timedelta
        
        # Create a test season
        season = Season()
        season.start_date = datetime.utcnow()
        season.end_date = datetime.utcnow() + timedelta(days=30)
        season.is_active = True
        season.is_ending = False
        season.new_matches_blocked = False
        
        # Test properties
        assert season.is_ending_soon is False
        assert season.should_block_new_matches is False
        assert season.should_lock_rating_calculation is False
        
        # Test status description
        assert season.get_status_description() == "Активен"
        assert season.get_blocking_reason() == "Нет ограничений"
    
    def test_match_methods(self):
        """Test Match model methods"""
        # Create a test match
        match = Match()
        match.status = MatchStatus.WAITING_READINESS
        match.current_stage = MatchStage.WAITING_READINESS
        
        # Test referee methods
        assert match.can_call_referee() is True
        assert match.is_referee_needed() is False
        
        # Test calling referee
        match.call_referee(123456789, "Test reason")
        assert match.status == MatchStatus.REFEREE_INTERVENTION
        assert match.referee_id == 123456789
        assert match.referee_intervention_reason == "Test reason"
        
        # Test resolving referee intervention
        match.resolve_referee_intervention("Test resolution")
        assert match.status == MatchStage.WAITING_READINESS
        assert match.referee_resolution == "Test resolution"
        
        # Test annulling match
        match.annul_match("Test annulment")
        assert match.status == MatchStatus.ANNULLED
        assert match.annulment_reason == "Test annulment"

if __name__ == "__main__":
    pytest.main([__file__])