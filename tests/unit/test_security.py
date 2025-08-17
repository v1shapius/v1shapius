import pytest
import asyncio
import discord
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.security_service import SecurityService
from models.security import SecurityEvent, SecurityEventType, SecurityLevel, PlayerSecurityProfile

class TestSecurityService:
    """Test class for security service"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        bot = Mock()
        bot.get_guild = Mock(return_value=Mock())
        return bot
    
    @pytest.fixture
    def security_service(self, mock_bot):
        """Create SecurityService instance"""
        return SecurityService(mock_bot)
    
    @pytest.mark.asyncio
    async def test_check_rating_spikes(self, security_service):
        """Test rating spike detection"""
        # Mock database session
        with patch.object(security_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock recent ratings with spike
            mock_ratings = [
                Mock(
                    player_id=1,
                    rating=1600,
                    previous_rating=1500,
                    updated_at=datetime.utcnow()
                )
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_ratings
            
            # Mock security event creation
            with patch.object(security_service, 'create_security_event') as mock_create:
                await security_service.check_rating_spikes(mock_session)
                
                # Verify security event was created
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[0][0] == SecurityEventType.RATING_SPIKE
                assert call_args[0][1] == SecurityLevel.MEDIUM
    
    @pytest.mark.asyncio
    async def test_check_suspicious_matches(self, security_service):
        """Test suspicious match detection"""
        # Mock database session
        with patch.object(security_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock recent matches with suspicious duration
            mock_matches = [
                Mock(
                    id=1,
                    player1_id=1,
                    status="complete",
                    created_at=datetime.utcnow() - timedelta(seconds=60),
                    updated_at=datetime.utcnow()
                )
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_matches
            
            # Mock security event creation
            with patch.object(security_service, 'create_security_event') as mock_create:
                await security_service.check_suspicious_matches(mock_session)
                
                # Verify security event was created for fast match
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[0][0] == SecurityEventType.SUSPICIOUS_MATCH
                assert call_args[0][1] == SecurityLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_check_player_win_patterns(self, security_service):
        """Test suspicious win pattern detection"""
        # Mock database session
        with patch.object(security_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock recent matches with high win rate
            mock_matches = [
                Mock(winner_id=1), Mock(winner_id=1), Mock(winner_id=1),
                Mock(winner_id=1), Mock(winner_id=1), Mock(winner_id=2)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_matches
            
            # Mock security event creation
            with patch.object(security_service, 'create_security_event') as mock_create:
                await security_service.check_player_win_patterns(mock_session, Mock(winner_id=1))
                
                # Verify security event was created for high win rate
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[0][0] == SecurityEventType.UNUSUAL_ACTIVITY
                assert call_args[0][1] == SecurityLevel.MEDIUM
    
    @pytest.mark.asyncio
    async def test_check_multiple_accounts(self, security_service):
        """Test multiple account detection"""
        # Mock database session
        with patch.object(security_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock new players
            mock_players = [Mock(id=1)]
            mock_session.execute.return_value.fetchall.return_value = mock_players
            
            # Mock ratings with suspicious gain
            mock_ratings = [
                Mock(rating=1500), Mock(rating=1750)
            ]
            mock_session.execute.return_value.fetchall.return_value = mock_ratings
            
            # Mock security event creation
            with patch.object(security_service, 'create_security_event') as mock_create:
                await security_service.check_multiple_accounts(mock_session)
                
                # Verify security event was created for suspicious rating gain
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[0][0] == SecurityEventType.MULTIPLE_ACCOUNTS
                assert call_args[0][1] == SecurityLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_perform_match_integrity_check(self, security_service):
        """Test match integrity checking"""
        # Mock database session
        with patch.object(security_service, 'db') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock match
            mock_match = Mock(id=1, player1_id=1)
            
            # Mock integrity check creation
            with patch.object(security_service, 'create_security_event') as mock_create:
                await security_service.perform_match_integrity_check(mock_session, mock_match)
                
                # Verify integrity check was created
                mock_session.add.assert_called_once()
                added_check = mock_session.add.call_args[0][0]
                assert added_check.match_id == 1
                assert added_check.check_type == "automatic"

class TestSecurityModels:
    """Test class for security models"""
    
    def test_security_event_creation(self):
        """Test security event creation"""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_MATCH,
            security_level=SecurityLevel.HIGH,
            player_id=1,
            match_id=1,
            description="Test event",
            evidence={"test": "data"},
            risk_score=0.8
        )
        
        assert event.event_type == SecurityEventType.SUSPICIOUS_MATCH
        assert event.security_level == SecurityLevel.HIGH
        assert event.risk_score == 0.8
        assert event.is_resolved is False
    
    def test_security_event_resolution(self):
        """Test security event resolution"""
        event = SecurityEvent(
            event_type=SecurityEventType.RATING_SPIKE,
            security_level=SecurityLevel.MEDIUM,
            player_id=1,
            description="Test event",
            evidence={},
            risk_score=0.6
        )
        
        event.resolve(123456789, "Test resolution")
        
        assert event.is_resolved is True
        assert event.resolved_by == 123456789
        assert event.resolution_notes == "Test resolution"
        assert event.resolution_time is not None
    
    def test_security_event_risk_assessment(self):
        """Test security event risk assessment"""
        # High risk event
        high_risk_event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_MATCH,
            security_level=SecurityLevel.HIGH,
            player_id=1,
            description="Test",
            evidence={},
            risk_score=0.9
        )
        assert high_risk_event.is_high_risk is True
        
        # Low risk event
        low_risk_event = SecurityEvent(
            event_type=SecurityEventType.RATING_SPIKE,
            security_level=SecurityLevel.LOW,
            player_id=1,
            description="Test",
            evidence={},
            risk_score=0.3
        )
        assert low_risk_event.is_high_risk is False

class TestPlayerSecurityProfile:
    """Test class for player security profiles"""
    
    def test_profile_initialization(self):
        """Test profile initialization"""
        profile = PlayerSecurityProfile(player_id=1)
        
        assert profile.player_id == 1
        assert profile.overall_risk_score == 0.0
        assert profile.risk_level == SecurityLevel.LOW
        assert profile.is_restricted is False
    
    def test_risk_score_update(self):
        """Test risk score updating"""
        profile = PlayerSecurityProfile(player_id=1)
        
        # Update risk score
        profile.update_risk_score(0.7)
        assert profile.overall_risk_score == 0.7
        assert profile.risk_level == SecurityLevel.HIGH
        
        # Update to critical
        profile.update_risk_score(0.9)
        assert profile.risk_level == SecurityLevel.CRITICAL
    
    def test_player_restriction(self):
        """Test player restriction"""
        profile = PlayerSecurityProfile(player_id=1)
        
        # Restrict player
        profile.restrict_player("Test reason", 7)
        assert profile.is_restricted is True
        assert profile.restriction_reason == "Test reason"
        assert profile.restriction_until is not None
        
        # Check if currently restricted
        assert profile.is_restricted_now is True
        
        # Lift restriction
        profile.lift_restriction()
        assert profile.is_restricted is False
        assert profile.restriction_reason is None

class TestSecurityIntegration:
    """Test class for security system integration"""
    
    @pytest.mark.asyncio
    async def test_security_service_integration(self):
        """Test that security service integrates with other systems"""
        mock_bot = Mock()
        service = SecurityService(mock_bot)
        
        # Test service initialization
        assert service.bot == mock_bot
        assert service.check_interval > 0
        
        # Test service methods exist
        assert hasattr(service, 'check_rating_spikes')
        assert hasattr(service, 'check_suspicious_matches')
        assert hasattr(service, 'create_security_event')
    
    @pytest.mark.asyncio
    async def test_security_notifications(self):
        """Test security notification system"""
        mock_bot = Mock()
        service = SecurityService(mock_bot)
        
        # Mock guild and channel
        mock_guild = Mock()
        mock_channel = Mock()
        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_channel
        
        # Mock security event
        mock_event = Mock(
            event_type=SecurityEventType.SUSPICIOUS_MATCH,
            security_level=SecurityLevel.HIGH,
            description="Test event",
            evidence={"test": "data"},
            risk_score=0.8
        )
        
        # Test notification creation
        embed = service.create_security_notification_embed(mock_event)
        assert embed.title == "🚨 Suspicious Match"
        assert embed.color == service.get_security_level_color(SecurityLevel.HIGH)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])