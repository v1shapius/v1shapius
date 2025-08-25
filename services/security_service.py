import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, or_, func
from database.database import DatabaseManager
from models.security import (
    SecurityEvent, SecurityEventType, SecurityLevel, PlayerSecurityProfile,
    MatchIntegrityCheck, SecurityRule
)
from models.match import Match, MatchStatus
from models.player import Player
from models.rating import Rating

logger = logging.getLogger(__name__)

class SecurityService:
    """Service for detecting and preventing rating manipulation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.check_interval = 300  # Check every 5 minutes
        self.suspicious_thresholds = {
            "rating_spike": 100,  # Points
            "match_frequency": 10,  # Matches per hour
            "win_rate_sudden": 0.3,  # 30% change
            "time_consistency": 0.8,  # 80% consistency required
        }
    
    async def start_monitoring(self):
        """Start the security monitoring loop"""
        logger.info("Starting security monitoring service")
        while True:
            try:
                await self.run_security_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in security monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def run_security_checks(self):
        """Run all security checks"""
        try:
            session = await self.db.get_session()
        async with session:
                # Check for rating spikes
                await self.check_rating_spikes(session)
                
                # Check for suspicious match patterns
                await self.check_suspicious_matches(session)
                
                # Check for multiple account usage
                await self.check_multiple_accounts(session)
                
                # Run integrity checks on recent matches
                await self.run_match_integrity_checks(session)
                
                # Apply security rules
                await self.apply_security_rules(session)
                
        except Exception as e:
            logger.error(f"Error running security checks: {e}")
    
    async def check_rating_spikes(self, session):
        """Check for unusual rating changes"""
        try:
            # Get recent rating changes
            recent_ratings = await session.execute(
                select(Rating).where(
                    Rating.updated_at >= datetime.utcnow() - timedelta(hours=24)
                ).order_by(Rating.updated_at.desc())
            )
            recent_ratings = recent_ratings.fetchall()
            
            for rating in recent_ratings:
                # Calculate rating change
                if rating.previous_rating:
                    change = abs(rating.rating - rating.previous_rating)
                    
                    if change > self.suspicious_thresholds["rating_spike"]:
                        await self.create_security_event(
                            session,
                            SecurityEventType.RATING_SPIKE,
                            SecurityLevel.MEDIUM,
                            rating.player_id,
                            None,
                            f"Подозрительный скачок рейтинга: {change} очков",
                            {
                                "old_rating": rating.previous_rating,
                                "new_rating": rating.rating,
                                "change": change,
                                "threshold": self.suspicious_thresholds["rating_spike"]
                            },
                            0.6
                        )
                        
        except Exception as e:
            logger.error(f"Error checking rating spikes: {e}")
    
    async def check_suspicious_matches(self, session):
        """Check for suspicious match patterns"""
        try:
            # Get recent matches
            recent_matches = await session.execute(
                select(Match).where(
                    Match.status == MatchStatus.COMPLETE,
                    Match.updated_at >= datetime.utcnow() - timedelta(hours=24)
                ).order_by(Match.updated_at.desc())
            )
            recent_matches = recent_matches.fetchall()
            
            for match in recent_matches:
                # Check match duration
                if match.created_at and match.updated_at:
                    duration = (match.updated_at - match.created_at).total_seconds()
                    
                    # Suspicious if match completed too quickly (< 2 minutes)
                    if duration < 120:
                        await self.create_security_event(
                            session,
                            SecurityEventType.SUSPICIOUS_MATCH,
                            SecurityLevel.HIGH,
                            match.player1_id,
                            match.id,
                            f"Подозрительно быстрый матч: {duration} секунд",
                            {
                                "duration_seconds": duration,
                                "match_format": match.format.value,
                                "threshold": 120
                            },
                            0.8
                        )
                
                # Check for unusual win patterns
                if match.winner_id:
                    await self.check_player_win_patterns(session, match)
                    
        except Exception as e:
            logger.error(f"Error checking suspicious matches: {e}")
    
    async def check_player_win_patterns(self, session, match):
        """Check for unusual win patterns for a player"""
        try:
            # Get player's recent matches
            player_matches = await session.execute(
                select(Match).where(
                    and_(
                        Match.status == MatchStatus.COMPLETE,
                        or_(Match.player1_id == match.winner_id, Match.player2_id == match.winner_id),
                        Match.updated_at >= datetime.utcnow() - timedelta(hours=24)
                    )
                ).order_by(Match.updated_at.desc())
            )
            player_matches = player_matches.fetchall()
            
            if len(player_matches) >= 5:
                wins = sum(1 for m in player_matches if m.winner_id == match.winner_id)
                win_rate = wins / len(player_matches)
                
                # Check if win rate is suspiciously high
                if win_rate > 0.9:  # 90%+ win rate
                    await self.create_security_event(
                        session,
                        SecurityEventType.UNUSUAL_ACTIVITY,
                        SecurityLevel.MEDIUM,
                        match.winner_id,
                        None,
                        f"Подозрительно высокий процент побед: {win_rate:.1%}",
                        {
                            "win_rate": win_rate,
                            "total_matches": len(player_matches),
                            "wins": wins,
                            "threshold": 0.9
                        },
                        0.5
                    )
                    
        except Exception as e:
            logger.error(f"Error checking player win patterns: {e}")
    
    async def check_multiple_accounts(self, session):
        """Check for potential multiple account usage"""
        try:
            # Get players with similar IP addresses or device fingerprints
            # This is a simplified check - in production you'd want more sophisticated detection
            
            # Check for players with very similar behavior patterns
            suspicious_players = await session.execute(
                select(Player).where(
                    Player.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
            suspicious_players = suspicious_players.fetchall()
            
            for player in suspicious_players:
                # Check if new player has unusually good performance
                player_ratings = await session.execute(
                    select(Rating).where(Rating.player_id == player.id)
                )
                player_ratings = player_ratings.fetchall()
                
                if player_ratings:
                    initial_rating = player_ratings[0].rating
                    current_rating = player_ratings[-1].rating
                    
                    # Suspicious if new player gained 200+ rating in first week
                    if current_rating - initial_rating > 200:
                        await self.create_security_event(
                            session,
                            SecurityEventType.MULTIPLE_ACCOUNTS,
                            SecurityLevel.HIGH,
                            player.id,
                            None,
                            f"Подозрение на множественные аккаунты: +{current_rating - initial_rating} рейтинга за неделю",
                            {
                                "initial_rating": initial_rating,
                                "current_rating": current_rating,
                                "rating_gain": current_rating - initial_rating,
                                "account_age_days": 7
                            },
                            0.7
                        )
                        
        except Exception as e:
            logger.error(f"Error checking multiple accounts: {e}")
    
    async def run_match_integrity_checks(self, session):
        """Run integrity checks on recent matches"""
        try:
            # Get matches without integrity checks
            unchecked_matches = await session.execute(
                select(Match).where(
                    and_(
                        Match.status == MatchStatus.COMPLETE,
                        Match.updated_at >= datetime.utcnow() - timedelta(hours=1)
                    )
                )
            )
            unchecked_matches = unchecked_matches.fetchall()
            
            for match in unchecked_matches:
                # Check if integrity check already exists
                existing_check = await session.execute(
                    select(MatchIntegrityCheck).where(MatchIntegrityCheck.match_id == match.id)
                )
                existing_check = existing_check.scalar_one_or_none()
                
                if not existing_check:
                    await self.perform_match_integrity_check(session, match)
                    
        except Exception as e:
            logger.error(f"Error running match integrity checks: {e}")
    
    async def perform_match_integrity_check(self, session, match):
        """Perform integrity check on a specific match"""
        try:
            # Create integrity check record
            integrity_check = MatchIntegrityCheck(
                match_id=match.id,
                check_type="automatic"
            )
            
            # Calculate time consistency score
            time_score = await self.calculate_time_consistency(session, match)
            integrity_check.time_consistency_score = time_score
            
            # Calculate result plausibility score
            result_score = await self.calculate_result_plausibility(session, match)
            integrity_check.result_plausibility_score = result_score
            
            # Calculate overall integrity score
            integrity_check.calculate_integrity_score()
            
            # Add to session
            session.add(integrity_check)
            
            # If suspicious, create security event
            if integrity_check.is_suspicious:
                await self.create_security_event(
                    session,
                    SecurityEventType.SUSPICIOUS_MATCH,
                    SecurityLevel.MEDIUM,
                    match.player1_id,
                    match.id,
                    f"Подозрительный матч: низкий показатель целостности",
                    {
                        "integrity_score": integrity_check.overall_integrity_score,
                        "time_score": integrity_check.time_consistency_score,
                        "result_score": integrity_check.result_plausibility_score
                    },
                    0.6
                )
                
        except Exception as e:
            logger.error(f"Error performing match integrity check: {e}")
    
    async def calculate_time_consistency(self, session, match) -> float:
        """Calculate time consistency score for a match"""
        try:
            # Get match states to check timing consistency
            match_states = await session.execute(
                select(MatchState).where(MatchState.match_id == match.id)
            )
            match_states = match_states.fetchall()
            
            if len(match_states) < 2:
                return 1.0  # Perfect score if not enough data
            
            # Check if state transitions make sense time-wise
            total_time = 0
            suspicious_transitions = 0
            
            for i in range(1, len(match_states)):
                time_diff = (match_states[i].created_at - match_states[i-1].created_at).total_seconds()
                
                # Suspicious if state changed too quickly (< 10 seconds)
                if time_diff < 10:
                    suspicious_transitions += 1
                
                total_time += time_diff
            
            # Calculate consistency score
            if total_time == 0:
                return 0.0
            
            consistency = 1.0 - (suspicious_transitions / len(match_states))
            return max(0.0, min(1.0, consistency))
            
        except Exception as e:
            logger.error(f"Error calculating time consistency: {e}")
            return 0.5  # Default to neutral score
    
    async def calculate_result_plausibility(self, session, match) -> float:
        """Calculate result plausibility score for a match"""
        try:
            # Get game results
            game_results = await session.execute(
                select(GameResult).where(GameResult.match_id == match.id)
            )
            game_results = game_results.fetchall()
            
            if not game_results:
                return 1.0  # Perfect score if no results to check
            
            # Check for suspicious results
            suspicious_results = 0
            
            for result in game_results:
                # Suspicious if time difference is too small (< 5 seconds)
                if abs(result.player1_time - result.player2_time) < 5:
                    suspicious_results += 1
                
                # Suspicious if times are too fast (< 30 seconds)
                if result.player1_time < 30 or result.player2_time < 30:
                    suspicious_results += 1
            
            # Calculate plausibility score
            plausibility = 1.0 - (suspicious_results / len(game_results))
            return max(0.0, min(1.0, plausibility))
            
        except Exception as e:
            logger.error(f"Error calculating result plausibility: {e}")
            return 0.5  # Default to neutral score
    
    async def apply_security_rules(self, session):
        """Apply configured security rules"""
        try:
            # Get active security rules
            active_rules = await session.execute(
                select(SecurityRule).where(SecurityRule.is_active == True)
            )
            active_rules = active_rules.fetchall()
            
            for rule in active_rules:
                await self.evaluate_security_rule(session, rule)
                
        except Exception as e:
            logger.error(f"Error applying security rules: {e}")
    
    async def evaluate_security_rule(self, session, rule):
        """Evaluate a specific security rule"""
        try:
            if rule.rule_type == "rating_spike":
                await self.evaluate_rating_spike_rule(session, rule)
            elif rule.rule_type == "match_pattern":
                await self.evaluate_match_pattern_rule(session, rule)
            elif rule.rule_type == "win_rate":
                await self.evaluate_win_rate_rule(session, rule)
                
        except Exception as e:
            logger.error(f"Error evaluating security rule {rule.id}: {e}")
    
    async def create_security_event(
        self,
        session,
        event_type: SecurityEventType,
        security_level: SecurityLevel,
        player_id: Optional[int],
        match_id: Optional[int],
        description: str,
        evidence: Dict[str, Any],
        risk_score: float
    ):
        """Create a new security event"""
        try:
            # Check if similar event already exists
            existing_event = await session.execute(
                select(SecurityEvent).where(
                    and_(
                        SecurityEvent.event_type == event_type,
                        SecurityEvent.player_id == player_id,
                        SecurityEvent.is_resolved == False,
                        SecurityEvent.created_at >= datetime.utcnow() - timedelta(hours=1)
                    )
                )
            )
            existing_event = existing_event.scalar_one_or_none()
            
            if existing_event:
                # Update existing event
                existing_event.risk_score = max(existing_event.risk_score, risk_score)
                existing_event.evidence = {**existing_event.evidence, **evidence} if existing_event.evidence else evidence
            else:
                # Create new event
                security_event = SecurityEvent(
                    event_type=event_type,
                    security_level=security_level,
                    player_id=player_id,
                    match_id=match_id,
                    description=description,
                    evidence=evidence,
                    risk_score=risk_score
                )
                session.add(security_event)
                
                # Update player security profile
                if player_id:
                    await self.update_player_security_profile(session, player_id, risk_score)
                
                # Send notifications
                await self.send_security_notifications(security_event)
            
        except Exception as e:
            logger.error(f"Error creating security event: {e}")
    
    async def update_player_security_profile(self, session, player_id: int, risk_score: float):
        """Update player security profile"""
        try:
            # Get or create security profile
            profile = await session.execute(
                select(PlayerSecurityProfile).where(PlayerSecurityProfile.player_id == player_id)
            )
            profile = profile.scalar_one_or_none()
            
            if not profile:
                profile = PlayerSecurityProfile(player_id=player_id)
                session.add(profile)
            
            # Update risk score
            profile.update_risk_score(risk_score)
            
        except Exception as e:
            logger.error(f"Error updating player security profile: {e}")
    
    async def send_security_notifications(self, security_event: SecurityEvent):
        """Send security notifications to appropriate channels"""
        try:
            # Get guild from player or match
            guild_id = None
            if security_event.player_id:
                # Get guild from player's matches
                session = await self.db.get_session()
        async with session:
                    player_match = await session.execute(
                        select(Match).where(
                            or_(Match.player1_id == security_event.player_id, Match.player2_id == security_event.player_id)
                        ).limit(1)
                    )
                    player_match = player_match.scalar_one_or_none()
                    if player_match:
                        guild_id = player_match.guild_id
            
            if guild_id:
                # Send notification to guild's audit channel
                await self.send_guild_security_notification(guild_id, security_event)
                
        except Exception as e:
            logger.error(f"Error sending security notifications: {e}")
    
    async def send_guild_security_notification(self, guild_id: int, security_event: SecurityEvent):
        """Send security notification to guild with role tagging"""
        try:
            # Determine event type for role tagging
            event_type = "security_alert"
            if security_event.event_type in [SecurityEventType.SUSPICIOUS_MATCH, SecurityEventType.MATCH_INTEGRITY_VIOLATION]:
                event_type = "referee_needed"
            elif security_event.security_level == SecurityLevel.CRITICAL:
                event_type = "admin_notification"
            
            # Create tagged message
            if hasattr(self.bot, 'role_manager'):
                tagged_message = await self.bot.role_manager.tag_role_for_event(
                    guild_id=guild_id,
                    event_type=event_type,
                    message=f"🚨 **Событие безопасности**: {security_event.description}"
                )
                
                # Send to guild's system channel or first available channel
                guild = self.bot.get_guild(guild_id)
                if guild:
                    channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                    if channel:
                        try:
                            await channel.send(tagged_message)
                        except discord.Forbidden:
                            logger.warning(f"Could not send security notification to guild {guild_id}")
                            
        except Exception as e:
            logger.error(f"Error sending guild security notification: {e}")
        """Send security notification to a specific guild"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            # Try to find audit channel
            session = await self.db.get_session()
        async with session:
                penalty_settings = await session.execute(
                    "SELECT audit_channel_id FROM penalty_settings WHERE guild_id = :guild_id",
                    {"guild_id": guild_id}
                )
                penalty_settings = penalty_settings.scalar_one_or_none()
                
                audit_channel_id = penalty_settings.audit_channel_id if penalty_settings else None
                
                if audit_channel_id:
                    channel = guild.get_channel(audit_channel_id)
                    if channel:
                        embed = self.create_security_notification_embed(security_event)
                        await channel.send(
                            f"🚨 **Событие безопасности!**",
                            embed=embed
                        )
                        
        except Exception as e:
            logger.error(f"Error sending guild security notification: {e}")
    
    def create_security_notification_embed(self, security_event: SecurityEvent):
        """Create embed for security notification"""
        embed = discord.Embed(
            title=f"🚨 {security_event.event_type.value.replace('_', ' ').title()}",
            description=security_event.description,
            color=self.get_security_level_color(security_event.security_level),
            timestamp=security_event.created_at
        )
        
        embed.add_field(
            name="Уровень угрозы",
            value=security_event.security_level.value.upper(),
            inline=True
        )
        
        embed.add_field(
            name="Оценка риска",
            value=f"{security_event.risk_score:.1%}",
            inline=True
        )
        
        if security_event.player_id:
            embed.add_field(
                name="Игрок",
                value=f"<@{security_event.player_id}>",
                inline=True
            )
        
        if security_event.evidence:
            evidence_text = "\n".join([f"• {k}: {v}" for k, v in security_event.evidence.items()][:5])
            embed.add_field(
                name="Доказательства",
                value=evidence_text[:1024],
                inline=False
            )
        
        embed.set_footer(text="Требует внимания администратора")
        
        return embed
    
    def get_security_level_color(self, security_level: SecurityLevel) -> int:
        """Get Discord color for security level"""
        colors = {
            SecurityLevel.LOW: 0x00ff00,      # Green
            SecurityLevel.MEDIUM: 0xffff00,   # Yellow
            SecurityLevel.HIGH: 0xff8800,     # Orange
            SecurityLevel.CRITICAL: 0xff0000  # Red
        }
        return colors.get(security_level, 0x808080)  # Default gray