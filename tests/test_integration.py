import pytest
import asyncio
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.match_management import MatchManagement, MatchJoinView
from cogs.admin import Admin
from cogs.rating_system import RatingSystem
from models.season import Season
from models.match import Match, MatchStatus, MatchFormat
from models.player import Player

class TestMatchManagementIntegration:
    """Integration tests for match management"""
    
    @pytest.fixture
    def bot(self):
        """Create a test bot instance"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        
        bot = commands.Bot(command_prefix="!", intents=intents)
        return bot
    
    @pytest.fixture
    def match_management_cog(self, bot):
        """Create match management cog instance"""
        return MatchManagement(bot)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock interaction"""
        interaction = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.user.id = 123456789
        interaction.user.display_name = "Test User"
        interaction.guild_id = 987654321
        interaction.channel_id = 111222333
        return interaction
    
    @pytest.fixture
    def mock_opponent(self):
        """Create a mock opponent"""
        opponent = Mock()
        opponent.id = 987654321
        opponent.display_name = "Test Opponent"
        opponent.bot = False
        return opponent
    
    @pytest.mark.asyncio
    async def test_challenge_command_success(self, match_management_cog, mock_interaction, mock_opponent):
        """Test successful challenge command execution"""
        # Mock season manager
        mock_season_manager = Mock()
        mock_season_manager.can_create_new_match = AsyncMock(return_value=(True, "Нет ограничений"))
        mock_season_manager.get_season_status = AsyncMock(return_value=None)
        
        match_management_cog.bot.get_cog = Mock(return_value=mock_season_manager)
        
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock penalty settings
        mock_penalty_settings = Mock()
        mock_penalty_settings.match_channel_id = None
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_penalty_settings
        
        # Mock database manager
        match_management_cog.db.get_session = AsyncMock()
        match_management_cog.db.get_session.return_value.__aenter__.return_value = mock_session
        
        # Execute challenge command
        await match_management_cog.challenge(mock_interaction, mock_opponent, "Bo1")
        
        # Verify interaction was deferred
        mock_interaction.response.defer.assert_called_once()
        
        # Verify followup was sent
        mock_interaction.followup.send.assert_called_once()
        
        # Verify the response contains the challenge
        call_args = mock_interaction.followup.send.call_args
        assert "⚔️" in call_args[0][0]  # Check for challenge emoji
        assert "Test User" in call_args[0][0]  # Check for challenger name
        assert "Test Opponent" in call_args[0][0]  # Check for opponent name
    
    @pytest.mark.asyncio
    async def test_challenge_command_self_challenge(self, match_management_cog, mock_interaction):
        """Test challenge command when user challenges themselves"""
        # Mock opponent as same user
        mock_opponent = Mock()
        mock_opponent.id = 123456789  # Same as interaction.user.id
        mock_opponent.display_name = "Test User"
        
        await match_management_cog.challenge(mock_interaction, mock_opponent, "Bo1")
        
        # Verify error message was sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in call_args[0][0]  # Check for error emoji
        assert "сами себя" in call_args[0][0]  # Check for error message
    
    @pytest.mark.asyncio
    async def test_challenge_command_bot_opponent(self, match_management_cog, mock_interaction):
        """Test challenge command when opponent is a bot"""
        # Mock bot opponent
        mock_opponent = Mock()
        mock_opponent.id = 987654321
        mock_opponent.display_name = "Test Bot"
        mock_opponent.bot = True
        
        await match_management_cog.challenge(mock_interaction, mock_opponent, "Bo1")
        
        # Verify error message was sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "❌" in call_args[0][0]  # Check for error emoji
        assert "бота" in call_args[0][0]  # Check for error message
    
    @pytest.mark.asyncio
    async def test_challenge_command_season_blocked(self, match_management_cog, mock_interaction, mock_opponent):
        """Test challenge command when season blocks new matches"""
        # Mock season manager that blocks matches
        mock_season_manager = Mock()
        mock_season_manager.can_create_new_match = AsyncMock(return_value=(False, "Сезон завершается"))
        
        mock_season = Mock()
        mock_season.name = "Test Season"
        mock_season.get_status_description.return_value = "Завершается через 3 дня"
        mock_season.is_ending_soon = True
        
        mock_season_manager.get_season_status = AsyncMock(return_value=mock_season)
        
        match_management_cog.bot.get_cog = Mock(return_value=mock_season_manager)
        
        # Execute challenge command
        await match_management_cog.challenge(mock_interaction, mock_opponent, "Bo1")
        
        # Verify error message was sent
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "🚫" in call_args[0][0]  # Check for blocked emoji
        assert "заблокировано" in call_args[0][0]  # Check for blocked message

class TestMatchJoinViewIntegration:
    """Integration tests for match join view"""
    
    @pytest.fixture
    def mock_challenger(self):
        """Create a mock challenger"""
        challenger = Mock()
        challenger.id = 123456789
        challenger.display_name = "Test Challenger"
        return challenger
    
    @pytest.fixture
    def mock_opponent(self):
        """Create a mock opponent"""
        opponent = Mock()
        opponent.id = 987654321
        opponent.display_name = "Test Opponent"
        return opponent
    
    @pytest.fixture
    def match_join_view(self, mock_challenger, mock_opponent):
        """Create a match join view instance"""
        return MatchJoinView(mock_challenger, mock_opponent, "bo1")
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock interaction"""
        interaction = Mock()
        interaction.user.id = 123456789
        interaction.user.mention = "<@123456789>"
        interaction.data = {"custom_id": "accept_challenge"}
        interaction.response.send_message = AsyncMock()
        interaction.message.edit = AsyncMock()
        interaction.channel.create_thread = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_interaction_check_valid_user(self, match_join_view, mock_interaction):
        """Test interaction check with valid user"""
        result = await match_join_view.interaction_check(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_interaction_check_invalid_user(self, match_join_view, mock_interaction):
        """Test interaction check with invalid user"""
        mock_interaction.user.id = 555666777  # Different user ID
        
        result = await match_join_view.interaction_check(mock_interaction)
        assert result is False
        
        # Verify error message was sent
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "не можете взаимодействовать" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_accept_challenge_challenger(self, match_join_view, mock_interaction):
        """Test challenger accepting challenge"""
        mock_interaction.user.id = 123456789  # Challenger ID
        
        result = await match_join_view.interaction_check(mock_interaction)
        assert result is True
        
        # Verify challenger accepted message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "готовность" in call_args[0][0]
        
        # Verify challenger_accepted was set
        assert match_join_view.challenger_accepted is True
        assert match_join_view.opponent_accepted is False
    
    @pytest.mark.asyncio
    async def test_accept_challenge_opponent(self, match_join_view, mock_interaction):
        """Test opponent accepting challenge"""
        mock_interaction.user.id = 987654321  # Opponent ID
        
        result = await match_join_view.interaction_check(mock_interaction)
        assert result is True
        
        # Verify opponent accepted message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "приняли вызов" in call_args[0][0]
        
        # Verify opponent_accepted was set
        assert match_join_view.challenger_accepted is False
        assert match_join_view.opponent_accepted is True

class TestAdminIntegration:
    """Integration tests for admin functionality"""
    
    @pytest.fixture
    def bot(self):
        """Create a test bot instance"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        bot = commands.Bot(command_prefix="!", intents=intents)
        return bot
    
    @pytest.fixture
    def admin_cog(self, bot):
        """Create admin cog instance"""
        return Admin(bot)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock interaction"""
        interaction = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.user.guild_permissions.administrator = True
        interaction.guild_id = 987654321
        return interaction
    
    @pytest.mark.asyncio
    async def test_season_management_command(self, admin_cog, mock_interaction):
        """Test season management command"""
        # Mock database session
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # Mock current season
        mock_season = Mock()
        mock_season.id = 1
        mock_season.name = "Test Season"
        mock_season.is_active = True
        mock_season.is_ending = False
        mock_season.is_rating_locked = False
        mock_season.new_matches_blocked = False
        mock_season.rating_calculation_locked = False
        mock_season.season_end_warning_sent = False
        mock_season.start_date = Mock()
        mock_season.start_date.strftime.return_value = "01.01.2024 00:00"
        mock_season.end_date = Mock()
        mock_season.end_date.strftime.return_value = "31.01.2024 23:59"
        mock_season.days_until_end = 30
        mock_season.get_status_description.return_value = "Активен"
        mock_season.get_blocking_reason.return_value = "Нет ограничений"
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
        
        # Mock database manager
        admin_cog.db.get_session = AsyncMock()
        admin_cog.db.get_session.return_value.__aenter__.return_value = mock_session
        
        # Execute season management command
        await admin_cog.season_management(mock_interaction, "status")
        
        # Verify interaction was deferred
        mock_interaction.response.defer.assert_called_once()
        
        # Verify followup was sent
        mock_interaction.followup.send.assert_called_once()
        
        # Verify the response contains season information
        call_args = mock_interaction.followup.send.call_args
        assert "📊" in call_args[0][0]  # Check for status emoji
        assert "Test Season" in call_args[0][0]  # Check for season name

if __name__ == "__main__":
    pytest.main([__file__])