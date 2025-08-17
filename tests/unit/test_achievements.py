import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogs.achievements import Achievements, AchievementView
from models.achievement import Achievement, AchievementType, AchievementProgress
from services.achievement_service import AchievementService

class TestAchievementTypes:
    """Test class for achievement types"""
    
    def test_achievement_type_enum_values(self):
        """Test that all achievement type enum values are correct"""
        assert AchievementType.FIRST_MATCH.value == "first_match"
        assert AchievementType.FIRST_WIN.value == "first_win"
        assert AchievementType.STREAK_3.value == "streak_3"
        assert AchievementType.STREAK_5.value == "streak_5"
        assert AchievementType.STREAK_10.value == "streak_10"
        assert AchievementType.RATING_1600.value == "rating_1600"
        assert AchievementType.RATING_1800.value == "rating_1800"
        assert AchievementType.RATING_2000.value == "rating_2000"
        assert AchievementType.SEASON_WINNER.value == "season_winner"
        assert AchievementType.MATCHES_10.value == "matches_10"
        assert AchievementType.MATCHES_50.value == "matches_50"
        assert AchievementType.MATCHES_100.value == "matches_100"
        assert AchievementType.REFEREE_HELP.value == "referee_help"
        assert AchievementType.PERFECT_MATCH.value == "perfect_match"
        assert AchievementType.COMEBACK_WIN.value == "comeback_win"
    
    def test_achievement_type_display_names(self):
        """Test achievement type display names"""
        assert AchievementType.FIRST_MATCH.display_name == "Первая игра"
        assert AchievementType.FIRST_WIN.display_name == "Первая победа"
        assert AchievementType.STREAK_3.display_name == "Серия из 3 побед"
        assert AchievementType.RATING_1600.display_name == "Рейтинг 1600+"
        assert AchievementType.SEASON_WINNER.display_name == "Победитель сезона"
    
    def test_achievement_type_descriptions(self):
        """Test achievement type descriptions"""
        assert AchievementType.FIRST_MATCH.description == "Сыграйте свою первую игру"
        assert AchievementType.FIRST_WIN.description == "Одержите первую победу"
        assert AchievementType.STREAK_3.description == "Выиграйте 3 игры подряд"
        assert AchievementType.RATING_1600.description == "Достигните рейтинга 1600"
    
    def test_achievement_type_icons(self):
        """Test achievement type icons"""
        assert AchievementType.FIRST_MATCH.icon == "🎮"
        assert AchievementType.FIRST_WIN.icon == "🏆"
        assert AchievementType.STREAK_3.icon == "🔥"
        assert AchievementType.RATING_1600.icon == "⭐"
        assert AchievementType.SEASON_WINNER.icon == "👑"

class TestAchievementProgress:
    """Test class for achievement progress tracking"""
    
    @pytest.fixture
    def progress(self):
        """Create AchievementProgress instance"""
        return AchievementProgress(
            player_id=1,
            achievement_type=AchievementType.MATCHES_10,
            current_progress=5,
            target_progress=10
        )
    
    def test_progress_initialization(self, progress):
        """Test achievement progress initialization"""
        assert progress.player_id == 1
        assert progress.achievement_type == AchievementType.MATCHES_10
        assert progress.current_progress == 5
        assert progress.target_progress == 10
        assert progress.is_completed is False
    
    def test_progress_completion(self, progress):
        """Test achievement progress completion"""
        # Update progress to complete
        progress.current_progress = 10
        assert progress.is_completed is True
        
        # Update progress beyond target
        progress.current_progress = 15
        assert progress.is_completed is True
    
    def test_progress_percentage(self, progress):
        """Test progress percentage calculation"""
        # 5/10 = 50%
        assert progress.progress_percentage == 50.0
        
        # 10/10 = 100%
        progress.current_progress = 10
        assert progress.progress_percentage == 100.0
        
        # 0/10 = 0%
        progress.current_progress = 0
        assert progress.progress_percentage == 0.0
    
    def test_progress_update(self, progress):
        """Test progress update functionality"""
        original_time = progress.last_updated
        
        # Update progress
        result = progress.update_progress(3)
        assert result is False  # Not completed yet
        assert progress.current_progress == 8
        assert progress.last_updated > original_time
        
        # Update to complete
        result = progress.update_progress(2)
        assert result is True  # Completed!
        assert progress.current_progress == 10
        assert progress.is_completed is True

class TestAchievementService:
    """Test class for achievement service"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        bot.get_user = Mock(return_value=Mock())
        return bot
    
    @pytest.fixture
    def achievement_service(self, mock_bot):
        """Create AchievementService instance"""
        return AchievementService(mock_bot)
    
    @pytest.mark.asyncio
    async def test_check_match_count_achievements(self, achievement_service):
        """Test match count achievement checking"""
        # Mock database session
        with patch.object(achievement_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            
            # Mock match count query
            mock_session.execute.return_value.scalar_one_or_none.return_value = 15
            
            # Mock award achievement
            with patch.object(achievement_service, 'award_achievement') as mock_award:
                await achievement_service.check_match_count_achievements(mock_session, mock_player)
                
                # Should award matches_10 and matches_50 achievements
                assert mock_award.call_count == 2
                call_args = [call[0] for call in mock_award.call_args_list]
                assert (1, AchievementType.MATCHES_10) in call_args
                assert (1, AchievementType.MATCHES_50) not in call_args  # 15 < 50
    
    @pytest.mark.asyncio
    async def test_check_win_streak_achievements(self, achievement_service):
        """Test win streak achievement checking"""
        # Mock database session
        with patch.object(achievement_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            
            # Mock recent matches with 5 wins in a row
            mock_matches = [
                Mock(won=1), Mock(won=1), Mock(won=1), Mock(won=1), Mock(won=1),
                Mock(won=0), Mock(won=1), Mock(won=0), Mock(won=1), Mock(won=0)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_matches
            
            # Mock award achievement
            with patch.object(achievement_service, 'award_achievement') as mock_award:
                await achievement_service.check_win_streak_achievements(mock_session, mock_player)
                
                # Should award streak_3 and streak_5 achievements
                assert mock_award.call_count == 2
                call_args = [call[0] for call in mock_award.call_args_list]
                assert (1, AchievementType.STREAK_3) in call_args
                assert (1, AchievementType.STREAK_5) in call_args
                assert (1, AchievementType.STREAK_10) not in call_args  # 5 < 10
    
    @pytest.mark.asyncio
    async def test_check_rating_achievements(self, achievement_service):
        """Test rating achievement checking"""
        # Mock database session
        with patch.object(achievement_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            
            # Mock current rating
            mock_session.execute.return_value.scalar_one_or_none.return_value = 1850
            
            # Mock award achievement
            with patch.object(achievement_service, 'award_achievement') as mock_award:
                await achievement_service.check_rating_achievements(mock_session, mock_player)
                
                # Should award rating_1600 and rating_1800 achievements
                assert mock_award.call_count == 2
                call_args = [call[0] for call in mock_award.call_args_list]
                assert (1, AchievementType.RATING_1600) in call_args
                assert (1, AchievementType.RATING_1800) in call_args
                assert (1, AchievementType.RATING_2000) not in call_args  # 1850 < 2000
    
    @pytest.mark.asyncio
    async def test_award_achievement_new(self, achievement_service):
        """Test awarding new achievement"""
        # Mock database session
        with patch.object(achievement_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no existing achievement
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Mock notification
            with patch.object(achievement_service, 'notify_achievement_unlocked') as mock_notify:
                await achievement_service.award_achievement(mock_session, 1, AchievementType.FIRST_WIN)
                
                # Verify achievement was created
                mock_session.add.assert_called_once()
                added_achievement = mock_session.add.call_args[0][0]
                assert added_achievement.player_id == 1
                assert added_achievement.achievement_type == AchievementType.FIRST_WIN
                
                # Verify notification was sent
                mock_notify.assert_called_once_with(1, AchievementType.FIRST_WIN)
    
    @pytest.mark.asyncio
    async def test_award_achievement_existing(self, achievement_service):
        """Test awarding existing achievement (should not duplicate)"""
        # Mock database session
        with patch.object(achievement_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock existing achievement
            mock_session.execute.return_value.scalar_one_or_none.return_value = Mock()
            
            # Mock notification
            with patch.object(achievement_service, 'notify_achievement_unlocked') as mock_notify:
                await achievement_service.award_achievement(mock_session, 1, AchievementType.FIRST_WIN)
                
                # Verify no new achievement was created
                mock_session.add.assert_not_called()
                
                # Verify no notification was sent
                mock_notify.assert_not_called()

class TestAchievementsCog:
    """Test class for achievements cog"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        return bot
    
    @pytest.fixture
    def achievements_cog(self, mock_bot):
        """Create Achievements cog instance"""
        return Achievements(mock_bot)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction"""
        interaction = Mock()
        interaction.user = Mock()
        interaction.user.id = 123456789
        interaction.user.display_name = "TestUser"
        interaction.user.display_avatar = Mock()
        interaction.user.display_avatar.url = "https://example.com/avatar.png"
        interaction.response = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_view_achievements_self(self, achievements_cog, mock_interaction):
        """Test viewing own achievements"""
        # Mock database session
        with patch.object(achievements_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_player
            
            # Mock achievements
            mock_achievements = [
                Mock(
                    achievement_type=AchievementType.FIRST_WIN,
                    unlocked_at=datetime.utcnow()
                )
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_achievements
            
            # Mock progress
            mock_session.execute.return_value.fetchall.return_value = []
            
            await achievements_cog.view_achievements(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Достижения TestUser" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_view_achievements_other_user(self, achievements_cog, mock_interaction):
        """Test viewing another user's achievements"""
        # Mock other user
        other_user = Mock()
        other_user.id = 987654321
        other_user.display_name = "OtherUser"
        other_user.display_avatar = Mock()
        other_user.display_avatar.url = "https://example.com/other_avatar.png"
        
        # Mock database session
        with patch.object(achievements_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_player
            
            # Mock achievements
            mock_session.execute.return_value.fetchall.return_value = []
            
            # Mock progress
            mock_session.execute.return_value.fetchall.return_value = []
            
            await achievements_cog.view_achievements(mock_interaction, other_user)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Достижения OtherUser" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_view_achievements_no_player(self, achievements_cog, mock_interaction):
        """Test viewing achievements for non-existent player"""
        # Mock database session
        with patch.object(achievements_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no player found
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            await achievements_cog.view_achievements(mock_interaction)
            
            # Verify error response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "не найден в системе" in call_args[0][0]
            assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_view_progress(self, achievements_cog, mock_interaction):
        """Test viewing achievement progress"""
        # Mock database session
        with patch.object(achievements_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock player
            mock_player = Mock()
            mock_player.id = 1
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_player
            
            # Mock progress
            mock_progress = [
                Mock(
                    achievement_type=AchievementType.MATCHES_10,
                    current_progress=5,
                    target_progress=10
                )
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_progress
            
            await achievements_cog.view_progress(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Прогресс по достижениям" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_leaderboard_achievements(self, achievements_cog, mock_interaction):
        """Test achievement leaderboard"""
        # Mock database session
        with patch.object(achievements_cog, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock top players
            mock_top_players = [
                Mock(discord_id=123, username="Player1", achievement_count=15),
                Mock(discord_id=456, username="Player2", achievement_count=12),
                Mock(discord_id=789, username="Player3", achievement_count=8)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_top_players
            
            await achievements_cog.leaderboard_achievements(mock_interaction)
            
            # Verify response
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            assert "Таблица лидеров по достижениям" in call_args[0][0]

class TestAchievementView:
    """Test class for achievement view interactions"""
    
    @pytest.fixture
    def achievement_view(self):
        """Create AchievementView instance"""
        achievements = [
            Mock(
                achievement_type=AchievementType.FIRST_WIN,
                unlocked_at=datetime.utcnow()
            )
        ]
        progress = []
        return AchievementView(123456789, achievements, progress)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create mock Discord interaction"""
        interaction = Mock()
        interaction.user = Mock()
        interaction.user.id = 123456789
        interaction.response = Mock()
        interaction.response.send_message = AsyncMock()
        return interaction
    
    @pytest.mark.asyncio
    async def test_interaction_check_valid_user(self, achievement_view, mock_interaction):
        """Test interaction check for valid user"""
        result = await achievement_view.interaction_check(mock_interaction)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_interaction_check_invalid_user(self, achievement_view, mock_interaction):
        """Test interaction check for invalid user"""
        mock_interaction.user.id = 111111111
        
        result = await achievement_view.interaction_check(mock_interaction)
        assert result is False
        
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "только свои достижения" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

class TestAchievementIntegration:
    """Test class for achievement system integration"""
    
    @pytest.mark.asyncio
    async def test_achievement_service_integration(self):
        """Test that achievement service integrates with other systems"""
        mock_bot = Mock()
        service = AchievementService(mock_bot)
        
        # Test service initialization
        assert service.bot == mock_bot
        assert service.check_interval > 0
        
        # Test service methods exist
        assert hasattr(service, 'check_achievements')
        assert hasattr(service, 'award_achievement')
        assert hasattr(service, 'notify_achievement_unlocked')
    
    @pytest.mark.asyncio
    async def test_achievement_cog_integration(self):
        """Test that achievements cog integrates with bot"""
        mock_bot = Mock()
        cog = Achievements(mock_bot)
        
        # Test cog initialization
        assert cog.bot == mock_bot
        
        # Test cog commands exist
        assert hasattr(cog, 'view_achievements')
        assert hasattr(cog, 'view_progress')
        assert hasattr(cog, 'leaderboard_achievements')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])