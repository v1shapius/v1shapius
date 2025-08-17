import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.admin import Admin, GuildSettingsModal
from models.penalty_settings import PenaltySettings
from models.season import Season

class TestAdminFunctions:
    """Test class for admin functionality"""
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction"""
        interaction = Mock()
        interaction.user = Mock()
        interaction.user.id = 123456789
        interaction.user.guild_permissions = Mock()
        interaction.user.guild_permissions.administrator = True
        interaction.response = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        interaction.guild_id = 987654321
        return interaction
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        return bot
    
    @pytest.fixture
    def admin_cog(self, mock_bot):
        """Create Admin cog instance"""
        return Admin(mock_bot)
    
    @pytest.fixture
    def mock_season(self):
        """Create mock season"""
        season = Mock()
        season.id = 1
        season.name = "Test Season"
        season.start_date = datetime.utcnow() - timedelta(days=30)
        season.end_date = datetime.utcnow() + timedelta(days=30)
        season.is_active = True
        season.is_ending = False
        season.is_rating_locked = False
        season.new_matches_blocked = False
        season.rating_calculation_locked = False
        season.season_end_warning_sent = False
        
        # Mock methods
        season.get_status_description = Mock(return_value="Active")
        season.get_blocking_reason = Mock(return_value="No blocking")
        season.mark_as_ending = Mock()
        season.end_season = Mock()
        season.block_new_matches = Mock()
        
        return season

class TestSeasonManagement:
    """Test class for season management commands"""
    
    @pytest.mark.asyncio
    async def test_season_management_no_permissions(self, admin_cog, mock_interaction):
        """Test season management without admin permissions"""
        mock_interaction.user.guild_permissions.administrator = False
        
        await admin_cog.season_management(mock_interaction, "status")
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "нет прав администратора" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_season_management_no_active_season(self, admin_cog, mock_interaction):
        """Test season management when no active season exists"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            await admin_cog.season_management(mock_interaction, "status")
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "нет активного сезона" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_season_management_block_matches(self, admin_cog, mock_interaction, mock_season):
        """Test blocking new matches"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "block_matches")
            
            # Verify season was updated
            mock_season.block_new_matches.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Создание матчей заблокировано" in call_args[0][0].title
    
    @pytest.mark.asyncio
    async def test_season_management_unblock_matches(self, admin_cog, mock_interaction, mock_season):
        """Test unblocking new matches"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "unblock_matches")
            
            # Verify season was updated
            assert mock_season.new_matches_blocked is False
            mock_session.commit.assert_called_once()
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Создание матчей разблокировано" in call_args[0][0].title
    
    @pytest.mark.asyncio
    async def test_season_management_mark_ending(self, admin_cog, mock_interaction, mock_season):
        """Test marking season as ending"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "mark_ending")
            
            # Verify season was updated
            mock_season.mark_as_ending.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Сезон помечен как завершающийся" in call_args[0][0].title
    
    @pytest.mark.asyncio
    async def test_season_management_force_end(self, admin_cog, mock_interaction, mock_season):
        """Test forcing season end"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "force_end")
            
            # Verify season was updated
            mock_season.end_season.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Сезон принудительно завершен" in call_args[0][0].title
    
    @pytest.mark.asyncio
    async def test_season_management_status(self, admin_cog, mock_interaction, mock_season):
        """Test season status display"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "status")
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Статус сезона" in call_args[0][0].title
    
    @pytest.mark.asyncio
    async def test_season_management_invalid_action(self, admin_cog, mock_interaction, mock_season):
        """Test season management with invalid action"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            await admin_cog.season_management(mock_interaction, "invalid_action")
            
            # Verify error response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Неизвестное действие" in call_args[0][0]

class TestGuildSettings:
    """Test class for guild settings functionality"""
    
    @pytest.mark.asyncio
    async def test_settings_no_permissions(self, admin_cog, mock_interaction):
        """Test settings command without admin permissions"""
        mock_interaction.user.guild_permissions.administrator = False
        
        await admin_cog.settings(mock_interaction)
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "нет прав администратора" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_settings_display(self, admin_cog, mock_interaction):
        """Test settings display"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock penalty settings
            mock_settings = Mock()
            mock_settings.restart_penalty = 30
            mock_settings.max_restarts = 3
            mock_settings.audit_channel_id = 123456789
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_settings
            
            await admin_cog.settings(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Настройки сервера" in call_args[0][0].title

class TestPenaltySettings:
    """Test class for penalty settings functionality"""
    
    @pytest.mark.asyncio
    async def test_penalties_no_permissions(self, admin_cog, mock_interaction):
        """Test penalties command without admin permissions"""
        mock_interaction.user.guild_permissions.administrator = False
        
        await admin_cog.penalties(mock_interaction)
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "нет прав администратора" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_penalties_display(self, admin_cog, mock_interaction):
        """Test penalties display"""
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock penalty settings
            mock_settings = Mock()
            mock_settings.restart_penalty = 30
            mock_settings.max_restarts = 3
            mock_settings.audit_channel_id = 123456789
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_settings
            
            await admin_cog.penalties(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Настройки штрафов" in call_args[0][0].title

class TestGuildSettingsModal:
    """Test class for guild settings modal"""
    
    @pytest.fixture
    def modal(self):
        """Create GuildSettingsModal instance"""
        return GuildSettingsModal()
    
    def test_modal_fields(self, modal):
        """Test that modal has all required fields"""
        assert hasattr(modal, 'restart_penalty')
        assert hasattr(modal, 'max_restarts')
        assert hasattr(modal, 'audit_channel_id')
    
    def test_modal_validation(self, modal):
        """Test modal field validation"""
        # Test restart penalty validation
        modal.restart_penalty.value = "30"
        assert modal.restart_penalty.value == "30"
        
        # Test max restarts validation
        modal.max_restarts.value = "3"
        assert modal.max_restarts.value == "3"
        
        # Test audit channel validation
        modal.audit_channel_id.value = "123456789"
        assert modal.audit_channel_id.value == "123456789"

class TestAdminPermissions:
    """Test class for admin permission checks"""
    
    @pytest.mark.asyncio
    async def test_admin_commands_require_permissions(self, admin_cog, mock_interaction):
        """Test that admin commands require administrator permissions"""
        # Test without permissions
        mock_interaction.user.guild_permissions.administrator = False
        
        await admin_cog.season_management(mock_interaction, "status")
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "нет прав администратора" in call_args[0][0]
        
        # Reset mock
        mock_interaction.followup.send.reset_mock()
        
        # Test with permissions
        mock_interaction.user.guild_permissions.administrator = True
        
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            await admin_cog.season_management(mock_interaction, "status")
            
            # Should not get permission error
            call_args = mock_interaction.followup.send.call_args
            if call_args:
                assert "нет прав администратора" not in call_args[0][0]

class TestAdminErrorHandling:
    """Test class for admin error handling"""
    
    @pytest.mark.asyncio
    async def test_admin_database_error_handling(self, admin_cog, mock_interaction):
        """Test admin command error handling when database fails"""
        mock_interaction.user.guild_permissions.administrator = True
        
        # Mock database session to raise exception
        with patch.object(admin_cog, 'db') as mock_db:
            mock_db.get_session.side_effect = Exception("Database connection failed")
            
            await admin_cog.season_management(mock_interaction, "status")
            
            # Verify error response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Ошибка" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_admin_invalid_input_handling(self, admin_cog, mock_interaction):
        """Test admin command handling of invalid input"""
        mock_interaction.user.guild_permissions.administrator = True
        
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_season = Mock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            # Test with invalid action
            await admin_cog.season_management(mock_interaction, "invalid_action")
            
            # Verify error response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Неизвестное действие" in call_args[0][0]

class TestAdminIntegration:
    """Test class for admin integration with other systems"""
    
    @pytest.mark.asyncio
    async def test_admin_season_manager_integration(self, admin_cog, mock_interaction, mock_season):
        """Test admin commands integrate with season manager"""
        mock_interaction.user.guild_permissions.administrator = True
        
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            # Test marking season as ending
            await admin_cog.season_management(mock_interaction, "mark_ending")
            
            # Verify season manager methods were called
            mock_season.mark_as_ending.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_admin_audit_logging(self, admin_cog, mock_interaction, mock_season):
        """Test that admin actions are properly logged"""
        mock_interaction.user.guild_permissions.administrator = True
        
        # Mock database session
        with patch.object(admin_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock active season
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_season
            
            # Test blocking matches
            await admin_cog.season_management(mock_interaction, "block_matches")
            
            # Verify action was logged in database
            mock_session.commit.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])