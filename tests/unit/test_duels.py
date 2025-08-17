import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.match_management import MatchManagement, MatchJoinView
from models.match import Match, MatchStatus, MatchFormat
from models.player import Player
from models.season import Season
from services.season_manager import SeasonManager

class TestDuels:
    """Test class for duel functionality"""
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction"""
        interaction = Mock()
        interaction.user = Mock()
        interaction.user.id = 123456789
        interaction.user.display_name = "TestUser"
        interaction.user.mention = "<@123456789>"
        interaction.guild_id = 987654321
        interaction.response = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        return interaction
    
    @pytest.fixture
    def mock_opponent(self):
        """Create mock opponent"""
        opponent = Mock()
        opponent.id = 987654321
        opponent.display_name = "OpponentUser"
        opponent.mention = "<@987654321>"
        opponent.bot = False
        return opponent
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        bot.get_cog = Mock(return_value=Mock())
        return bot
    
    @pytest.fixture
    def match_management(self, mock_bot):
        """Create MatchManagement instance"""
        return MatchManagement(mock_bot)
    
    @pytest.mark.asyncio
    async def test_challenge_self(self, match_management, mock_interaction, mock_opponent):
        """Test that users cannot challenge themselves"""
        mock_interaction.user.id = mock_opponent.id
        
        await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "не можете вызвать сами себя" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_challenge_bot(self, match_management, mock_interaction, mock_opponent):
        """Test that users cannot challenge bots"""
        mock_opponent.bot = True
        
        await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "не можете вызвать бота" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_challenge_season_blocked(self, match_management, mock_interaction, mock_opponent):
        """Test challenge when season blocks new matches"""
        # Mock season manager to block matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(False, "Season ending"))
        season_manager.get_season_status = AsyncMock(return_value=Mock(
            name="Test Season",
            get_status_description=Mock(return_value="Ending soon"),
            is_ending_soon=True
        ))
        match_management.bot.get_cog.return_value = season_manager
        
        await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "Создание матчей заблокировано" in call_args[0][0].title
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_challenge_success_bo1(self, match_management, mock_interaction, mock_opponent):
        """Test successful Bo1 challenge"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        # Mock database session
        with patch.object(match_management, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player creation
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Mock match creation
            mock_match = Mock()
            mock_match.id = 1
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Mock thread creation
            mock_thread = Mock()
            mock_thread.id = 123
            mock_interaction.guild.create_text_channel = AsyncMock(return_value=mock_thread)
            
            await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
            
            # Verify match was created with correct format
            mock_session.add.assert_called()
            added_match = mock_session.add.call_args[0][0]
            assert added_match.format == MatchFormat.BO1
    
    @pytest.mark.asyncio
    async def test_challenge_success_bo3(self, match_management, mock_interaction, mock_opponent):
        """Test successful Bo3 challenge"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        # Mock database session
        with patch.object(match_management, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player creation
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Mock match creation
            mock_match = Mock()
            mock_match.id = 1
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Mock thread creation
            mock_thread = Mock()
            mock_thread.id = 123
            mock_interaction.guild.create_text_channel = AsyncMock(return_value=mock_thread)
            
            await match_management.challenge(mock_interaction, mock_opponent, "Bo3")
            
            # Verify match was created with correct format
            mock_session.add.assert_called()
            added_match = mock_session.add.call_args[0][0]
            assert added_match.format == MatchFormat.BO3
    
    @pytest.mark.asyncio
    async def test_challenge_success_bo5(self, match_management, mock_interaction, mock_opponent):
        """Test successful Bo5 challenge"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        # Mock database session
        with patch.object(match_management, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player creation
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Mock match creation
            mock_match = Mock()
            mock_match.id = 1
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Mock thread creation
            mock_thread = Mock()
            mock_thread.id = 123
            mock_interaction.guild.create_text_channel = AsyncMock(return_value=mock_thread)
            
            await match_management.challenge(mock_interaction, mock_opponent, "Bo5")
            
            # Verify match was created with correct format
            mock_session.add.assert_called()
            added_match = mock_session.add.call_args[0][0]
            assert added_match.format == MatchFormat.BO5
    
    @pytest.mark.asyncio
    async def test_challenge_invalid_format(self, match_management, mock_interaction, mock_opponent):
        """Test challenge with invalid format"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        await match_management.challenge(mock_interaction, mock_opponent, "Invalid")
        
        # Should still work as format is converted to lowercase
        mock_interaction.followup.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_challenge_active_match_exists(self, match_management, mock_interaction, mock_opponent):
        """Test challenge when player has active match"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        # Mock database session
        with patch.object(match_management, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock existing active match
            mock_session.execute.return_value.scalar_one_or_none.return_value = Mock(
                id=1,
                player1_id=123,
                player2_id=456,
                status=MatchStatus.ACTIVE
            )
            
            await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "уже есть активный матч" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_challenge_opponent_active_match(self, match_management, mock_interaction, mock_opponent):
        """Test challenge when opponent has active match"""
        # Mock season manager to allow matches
        season_manager = Mock()
        season_manager.can_create_new_match = AsyncMock(return_value=(True, ""))
        match_management.bot.get_cog.return_value = season_manager
        
        # Mock database session
        with patch.object(match_management, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no active match for challenger
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                None,  # No active match for challenger
                Mock(id=1, status=MatchStatus.ACTIVE)  # Active match for opponent
            ]
            
            await match_management.challenge(mock_interaction, mock_opponent, "Bo1")
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "противник уже участвует в матче" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True

class TestMatchJoinView:
    """Test class for match join view"""
    
    @pytest.fixture
    def mock_view(self):
        """Create MatchJoinView instance"""
        return MatchJoinView(
            challenger_id=123456789,
            opponent_id=987654321,
            match_id=1,
            format=MatchFormat.BO3
        )
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction"""
        interaction = Mock()
        interaction.user = Mock()
        interaction.user.id = 987654321
        interaction.response = Mock()
        interaction.response.send_message = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_interaction_check_valid_user(self, mock_view, mock_interaction):
        """Test interaction check for valid user"""
        result = await mock_view.interaction_check(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_interaction_check_invalid_user(self, mock_view, mock_interaction):
        """Test interaction check for invalid user"""
        mock_interaction.user.id = 111111111
        
        result = await mock_view.interaction_check(mock_interaction)
        assert result is False
        
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "только противник может принять вызов" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_accept_challenge(self, mock_view, mock_interaction):
        """Test accepting challenge"""
        # Mock database session
        with patch('cogs.match_management.DatabaseManager') as mock_db_class:
            mock_db = Mock()
            mock_db_class.return_value = mock_db
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock match retrieval
            mock_match = Mock(
                id=1,
                status=MatchStatus.PENDING,
                player1_id=123456789,
                player2_id=987654321,
                format=MatchFormat.BO3
            )
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_match
            
            # Mock thread creation
            mock_thread = Mock()
            mock_thread.id = 123
            mock_interaction.guild.create_text_channel = AsyncMock(return_value=mock_thread)
            
            await mock_view.accept_challenge(mock_interaction)
            
            # Verify match status was updated
            assert mock_match.status == MatchStatus.ACTIVE
            mock_session.commit.assert_called_once()

class TestMatchFormats:
    """Test class for match format functionality"""
    
    def test_match_format_enum_values(self):
        """Test that all match format enum values are correct"""
        assert MatchFormat.BO1.value == "bo1"
        assert MatchFormat.BO3.value == "bo3"
        assert MatchFormat.BO5.value == "bo5"
    
    def test_match_format_validation(self):
        """Test match format validation"""
        # Valid formats
        assert MatchFormat("bo1") == MatchFormat.BO1
        assert MatchFormat("bo3") == MatchFormat.BO3
        assert MatchFormat("bo5") == MatchFormat.BO5
        
        # Invalid format should raise ValueError
        with pytest.raises(ValueError):
            MatchFormat("invalid")
    
    def test_match_format_display_names(self):
        """Test match format display names"""
        assert str(MatchFormat.BO1) == "Bo1"
        assert str(MatchFormat.BO3) == "Bo3"
        assert str(MatchFormat.BO5) == "Bo5"

class TestMatchStatus:
    """Test class for match status functionality"""
    
    def test_match_status_enum_values(self):
        """Test that all match status enum values are correct"""
        assert MatchStatus.PENDING.value == "pending"
        assert MatchStatus.ACTIVE.value == "active"
        assert MatchStatus.COMPLETE.value == "complete"
        assert MatchStatus.CANCELLED.value == "cancelled"
        assert MatchStatus.ANNULLED.value == "annulled"
    
    def test_match_status_transitions(self):
        """Test valid match status transitions"""
        # Pending -> Active (valid)
        assert MatchStatus.PENDING.can_transition_to(MatchStatus.ACTIVE)
        
        # Active -> Complete (valid)
        assert MatchStatus.ACTIVE.can_transition_to(MatchStatus.COMPLETE)
        
        # Pending -> Complete (invalid)
        assert not MatchStatus.PENDING.can_transition_to(MatchStatus.COMPLETE)
        
        # Complete -> Active (invalid)
        assert not MatchStatus.COMPLETE.can_transition_to(MatchStatus.ACTIVE)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])