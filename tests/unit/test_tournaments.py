import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.tournaments import Tournaments, TournamentView, TournamentCreationModal
from models.tournament import Tournament, TournamentStatus, TournamentFormat, TournamentParticipant, TournamentMatch
from services.tournament_service import TournamentService

class TestTournamentFormats:
    """Test class for tournament formats"""
    
    def test_tournament_format_enum_values(self):
        """Test that all tournament format enum values are correct"""
        assert TournamentFormat.SINGLE_ELIMINATION.value == "single_elimination"
        assert TournamentFormat.DOUBLE_ELIMINATION.value == "double_elimination"
        assert TournamentFormat.SWISS_SYSTEM.value == "swiss_system"
        assert TournamentFormat.ROUND_ROBIN.value == "round_robin"
    
    def test_tournament_format_display_names(self):
        """Test tournament format display names"""
        assert str(TournamentFormat.SINGLE_ELIMINATION) == "Single Elimination"
        assert str(TournamentFormat.DOUBLE_ELIMINATION) == "Double Elimination"
        assert str(TournamentFormat.SWISS_SYSTEM) == "Swiss System"
        assert str(TournamentFormat.ROUND_ROBIN) == "Round Robin"

class TestTournamentStatus:
    """Test class for tournament status"""
    
    def test_tournament_status_enum_values(self):
        """Test that all tournament status enum values are correct"""
        assert TournamentStatus.REGISTRATION.value == "registration"
        assert TournamentStatus.ACTIVE.value == "active"
        assert TournamentStatus.COMPLETED.value == "completed"
        assert TournamentStatus.CANCELLED.value == "cancelled"
    
    def test_tournament_status_transitions(self):
        """Test valid tournament status transitions"""
        # Registration -> Active (valid)
        assert TournamentStatus.REGISTRATION.can_transition_to(TournamentStatus.ACTIVE)
        
        # Active -> Completed (valid)
        assert TournamentStatus.ACTIVE.can_transition_to(TournamentStatus.COMPLETED)
        
        # Registration -> Completed (invalid)
        assert not TournamentStatus.REGISTRATION.can_transition_to(TournamentStatus.COMPLETED)
        
        # Completed -> Active (invalid)
        assert not TournamentStatus.COMPLETED.can_transition_to(TournamentStatus.ACTIVE)

class TestTournamentService:
    """Test class for tournament service"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        bot.get_user = Mock(return_value=Mock())
        return bot
    
    @pytest.fixture
    def tournament_service(self, mock_bot):
        """Create TournamentService instance"""
        return TournamentService(mock_bot)
    
    @pytest.mark.asyncio
    async def test_create_tournament(self, tournament_service):
        """Test tournament creation"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament creation
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Create tournament
            tournament = await tournament_service.create_tournament(
                name="Test Tournament",
                description="Test Description",
                guild_id=123456789,
                format=TournamentFormat.SINGLE_ELIMINATION,
                match_format="bo3",
                min_participants=4,
                max_participants=16,
                registration_days=7
            )
            
            # Verify tournament was created
            assert tournament.name == "Test Tournament"
            assert tournament.guild_id == 123456789
            assert tournament.format == TournamentFormat.SINGLE_ELIMINATION
            assert tournament.min_participants == 4
            assert tournament.max_participants == 16
            
            # Verify it was added to session
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_player_success(self, tournament_service):
        """Test successful player registration"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament exists and is open
            mock_tournament = Mock()
            mock_tournament.status = TournamentStatus.REGISTRATION
            mock_tournament.max_participants = 16
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_tournament
            
            # Mock no existing registration
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                None,  # No existing registration
                8      # Current participant count
            ]
            
            # Mock participant creation
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            
            # Register player
            result = await tournament_service.register_player(1, 123)
            
            # Verify success
            assert result is True
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_player_tournament_full(self, tournament_service):
        """Test player registration when tournament is full"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament exists and is open
            mock_tournament = Mock()
            mock_tournament.status = TournamentStatus.REGISTRATION
            mock_tournament.max_participants = 8
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_tournament
            
            # Mock no existing registration
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                None,  # No existing registration
                8      # Current participant count (at max)
            ]
            
            # Register player
            result = await tournament_service.register_player(1, 123)
            
            # Verify failure
            assert result is False
            mock_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_register_player_already_registered(self, tournament_service):
        """Test player registration when already registered"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament exists and is open
            mock_tournament = Mock()
            mock_tournament.status = TournamentStatus.REGISTRATION
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_tournament
            
            # Mock existing registration
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                Mock()  # Existing registration
            ]
            
            # Register player
            result = await tournament_service.register_player(1, 123)
            
            # Verify failure
            assert result is False
            mock_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_single_elimination_bracket(self, tournament_service):
        """Test single elimination bracket generation"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament
            mock_tournament = Mock()
            mock_tournament.id = 1
            mock_tournament.match_format = "bo3"
            
            # Mock participants
            mock_participants = [
                Mock(player_id=1), Mock(player_id=2), Mock(player_id=3), Mock(player_id=4)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_participants
            
            # Generate bracket
            await tournament_service.generate_single_elimination_bracket(mock_session, mock_tournament)
            
            # Verify bracket was generated
            assert mock_tournament.total_rounds == 2  # log2(4) = 2
            
            # Verify matches were created
            assert mock_session.add.call_count == 2  # 4 participants = 2 matches in first round
    
    @pytest.mark.asyncio
    async def test_advance_tournament_round(self, tournament_service):
        """Test tournament round advancement"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament
            mock_tournament = Mock()
            mock_tournament.id = 1
            mock_tournament.current_round = 1
            mock_tournament.total_rounds = 2
            
            # Mock current round matches (all completed)
            mock_matches = [
                Mock(status="completed", winner_id=1),
                Mock(status="completed", winner_id=2)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_matches
            
            # Mock next round creation
            with patch.object(tournament_service, 'create_next_round_matches') as mock_create:
                await tournament_service.advance_tournament_round(mock_session, mock_tournament)
                
                # Verify next round was created
                mock_create.assert_called_once()
                assert mock_tournament.current_round == 2
    
    @pytest.mark.asyncio
    async def test_advance_tournament_round_final(self, tournament_service):
        """Test tournament round advancement to final round"""
        # Mock database session
        with patch.object(tournament_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock tournament
            mock_tournament = Mock()
            mock_tournament.id = 1
            mock_tournament.current_round = 2
            mock_tournament.total_rounds = 2
            
            # Mock current round matches (all completed)
            mock_matches = [
                Mock(status="completed", winner_id=1)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_matches
            
            # Mock tournament end
            with patch.object(tournament_service, 'end_tournament') as mock_end:
                await tournament_service.advance_tournament_round(mock_session, mock_tournament)
                
                # Verify tournament was ended
                mock_end.assert_called_once()

class TestTournamentsCog:
    """Test class for tournaments cog"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        return bot
    
    @pytest.fixture
    def tournaments_cog(self, mock_bot):
        """Create Tournaments cog instance"""
        return Tournaments(mock_bot)
    
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
    
    @pytest.mark.asyncio
    async def test_create_tournament_no_permissions(self, tournaments_cog, mock_interaction):
        """Test tournament creation without admin permissions"""
        mock_interaction.user.guild_permissions.administrator = False
        
        await tournaments_cog.create_tournament(
            mock_interaction, "Test", "single_elimination", "bo3", 4, None, 7
        )
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "нет прав администратора" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_create_tournament_invalid_format(self, tournaments_cog, mock_interaction):
        """Test tournament creation with invalid format"""
        await tournaments_cog.create_tournament(
            mock_interaction, "Test", "invalid_format", "bo3", 4, None, 7
        )
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "Неверный формат турнира" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_create_tournament_invalid_match_format(self, tournaments_cog, mock_interaction):
        """Test tournament creation with invalid match format"""
        await tournaments_cog.create_tournament(
            mock_interaction, "Test", "single_elimination", "invalid", 4, None, 7
        )
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "Неверный формат матчей" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_create_tournament_invalid_participants(self, tournaments_cog, mock_interaction):
        """Test tournament creation with invalid participant count"""
        await tournaments_cog.create_tournament(
            mock_interaction, "Test", "single_elimination", "bo3", 1, None, 7
        )
        
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "Минимальное количество участников должно быть не менее 2" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_create_tournament_success(self, tournaments_cog, mock_interaction):
        """Test successful tournament creation"""
        # Mock tournament service
        mock_tournament = Mock()
        mock_tournament.id = 1
        mock_tournament.name = "Test Tournament"
        mock_tournament.format = TournamentFormat.SINGLE_ELIMINATION
        mock_tournament.match_format = "bo3"
        mock_tournament.min_participants = 4
        mock_tournament.max_participants = None
        mock_tournament.registration_end = datetime.utcnow() + timedelta(days=7)
        mock_tournament.rules = None
        mock_tournament.prize_pool = None
        
        with patch.object(tournaments_cog.tournament_service, 'create_tournament') as mock_create:
            mock_create.return_value = mock_tournament
            
            await tournaments_cog.create_tournament(
                mock_interaction, "Test Tournament", "single_elimination", "bo3", 4, None, 7
            )
            
            # Verify tournament was created
            mock_create.assert_called_once()
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Турнир создан!" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_list_tournaments(self, tournaments_cog, mock_interaction):
        """Test listing tournaments"""
        # Mock tournament service
        mock_tournaments = [
            {
                "id": 1,
                "name": "Test Tournament 1",
                "status": "registration",
                "format": "single_elimination",
                "participant_count": 4,
                "max_participants": 8
            },
            {
                "id": 2,
                "name": "Test Tournament 2",
                "status": "active",
                "format": "double_elimination",
                "participant_count": 8,
                "max_participants": 16
            }
        ]
        
        with patch.object(tournaments_cog.tournament_service, 'get_guild_tournaments') as mock_get:
            mock_get.return_value = mock_tournaments
            
            await tournaments_cog.list_tournaments(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Турниры сервера" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_register_tournament(self, tournaments_cog, mock_interaction):
        """Test tournament registration"""
        # Mock database session
        with patch.object(tournaments_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_player
            
            # Mock tournament service
            with patch.object(tournaments_cog.tournament_service, 'register_player') as mock_register:
                mock_register.return_value = True
                
                await tournaments_cog.register_tournament(mock_interaction, 1)
                
                # Verify registration was successful
                mock_register.assert_called_once_with(1, 1)
                
                # Verify response
                mock_interaction.followup.send.assert_called_once()
                call_args = mock_interaction.followup.send.call_args
                assert "успешно зарегистрировались" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_register_tournament_no_player(self, tournaments_cog, mock_interaction):
        """Test tournament registration for non-existent player"""
        # Mock database session
        with patch.object(tournaments_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no player found
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            await tournaments_cog.register_tournament(mock_interaction, 1)
            
            # Verify error response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "не найдены в системе" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_tournament_info(self, tournaments_cog, mock_interaction):
        """Test tournament information display"""
        # Mock tournament service
        mock_tournament_info = {
            "id": 1,
            "name": "Test Tournament",
            "description": "Test Description",
            "status": "registration",
            "format": "single_elimination",
            "participant_count": 4,
            "match_count": 0,
            "registration_start": datetime.utcnow(),
            "registration_end": datetime.utcnow() + timedelta(days=7),
            "tournament_start": None,
            "tournament_end": None,
            "rules": "Test Rules",
            "prize_pool": "Test Prizes"
        }
        
        with patch.object(tournaments_cog.tournament_service, 'get_tournament_info') as mock_get:
            mock_get.return_value = mock_tournament_info
            
            await tournaments_cog.tournament_info(mock_interaction, 1)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Информация о турнире" in call_args[0][0]

class TestTournamentView:
    """Test class for tournament view interactions"""
    
    @pytest.fixture
    def tournament_view(self):
        """Create TournamentView instance"""
        mock_service = Mock()
        return TournamentView(1, mock_service)
    
    def test_tournament_view_initialization(self, tournament_view):
        """Test tournament view initialization"""
        assert tournament_view.tournament_id == 1
        assert tournament_view.tournament_service is not None
        assert tournament_view.timeout == 300
        
        # Verify buttons were added
        button_labels = [item.label for item in tournament_view.children if hasattr(item, 'label')]
        assert "📝 Зарегистрироваться" in button_labels
        assert "📊 Информация" in button_labels
        assert "👥 Участники" in button_labels

class TestTournamentCreationModal:
    """Test class for tournament creation modal"""
    
    @pytest.fixture
    def modal(self):
        """Create TournamentCreationModal instance"""
        mock_service = Mock()
        return TournamentCreationModal(mock_service)
    
    def test_modal_fields(self, modal):
        """Test that modal has all required fields"""
        assert hasattr(modal, 'name')
        assert hasattr(modal, 'description')
        assert hasattr(modal, 'rules')
        assert hasattr(modal, 'prize_pool')
    
    def test_modal_validation(self, modal):
        """Test modal field validation"""
        # Test name validation
        modal.name.value = "Test Tournament"
        assert modal.name.value == "Test Tournament"
        
        # Test description validation
        modal.description.value = "Test Description"
        assert modal.description.value == "Test Description"
        
        # Test rules validation
        modal.rules.value = "Test Rules"
        assert modal.rules.value == "Test Rules"
        
        # Test prize pool validation
        modal.prize_pool.value = "Test Prizes"
        assert modal.prize_pool.value == "Test Prizes"

class TestTournamentIntegration:
    """Test class for tournament system integration"""
    
    @pytest.mark.asyncio
    async def test_tournament_service_integration(self):
        """Test that tournament service integrates with other systems"""
        mock_bot = Mock()
        service = TournamentService(mock_bot)
        
        # Test service initialization
        assert service.bot == mock_bot
        assert service.check_interval > 0
        
        # Test service methods exist
        assert hasattr(service, 'check_tournaments')
        assert hasattr(service, 'create_tournament')
        assert hasattr(service, 'register_player')
    
    @pytest.mark.asyncio
    async def test_tournament_cog_integration(self):
        """Test that tournaments cog integrates with bot"""
        mock_bot = Mock()
        cog = Tournaments(mock_bot)
        
        # Test cog initialization
        assert cog.bot == mock_bot
        
        # Test cog commands exist
        assert hasattr(cog, 'create_tournament')
        assert hasattr(cog, 'list_tournaments')
        assert hasattr(cog, 'register_tournament')
        assert hasattr(cog, 'tournament_info')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])