import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from database.database import DatabaseManager
from models.achievement import Achievement, AchievementType, AchievementProgress
from models.match import Match, MatchStatus
from models.player import Player
from models.rating import Rating
from config.config import Config
import discord

logger = logging.getLogger(__name__)

class AchievementService:
    """Service for managing player achievements and progress"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.check_interval = Config.ACHIEVEMENT_CHECK_INTERVAL
        
    async def start_monitoring(self):
        """Start the achievement monitoring loop"""
        logger.info("Starting achievement monitoring service")
        while True:
            try:
                await self.check_achievements()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in achievement monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_achievements(self):
        """Check and award achievements for all players"""
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get all active players
                players = await session.execute(
                    select(Player).where(Player.is_active == True)
                )
                players = players.fetchall()
                
                for player in players:
                    await self.check_player_achievements(session, player)
                    
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    async def check_player_achievements(self, session, player):
        """Check achievements for a specific player"""
        try:
            # Check match count achievements
            await self.check_match_count_achievements(session, player)
            
            # Check win streak achievements
            await self.check_win_streak_achievements(session, player)
            
            # Check rating achievements
            await self.check_rating_achievements(session, player)
            
            # Check special achievements
            await self.check_special_achievements(session, player)
            
        except Exception as e:
            logger.error(f"Error checking achievements for player {player.id}: {e}")
    
    async def check_match_count_achievements(self, session, player):
        """Check achievements based on total match count"""
        try:
            # Get total completed matches for player
            match_count = await session.execute(
                """
                SELECT COUNT(*) as count
                FROM matches m
                WHERE (m.player1_id = :player_id OR m.player2_id = :player_id)
                AND m.status = 'complete'
                """,
                {"player_id": player.id}
            )
            match_count = match_count.scalar_one_or_none()
            
            if not match_count:
                return
            
            # Check for match count achievements
            achievements_to_check = [
                (10, AchievementType.MATCHES_10),
                (50, AchievementType.MATCHES_50),
                (100, AchievementType.MATCHES_100)
            ]
            
            for threshold, achievement_type in achievements_to_check:
                if match_count >= threshold:
                    await self.award_achievement(session, player.id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking match count achievements: {e}")
    
    async def check_win_streak_achievements(self, session, player):
        """Check achievements based on win streaks"""
        try:
            # Get recent matches for player
            recent_matches = await session.execute(
                """
                SELECT m.*, 
                       CASE WHEN m.winner_id = :player_id THEN 1 ELSE 0 END as won
                FROM matches m
                WHERE (m.player1_id = :player_id OR m.player2_id = :player_id)
                AND m.status = 'complete'
                ORDER BY m.updated_at DESC
                LIMIT 20
                """,
                {"player_id": player.id}
            )
            recent_matches = recent_matches.fetchall()
            
            if not recent_matches:
                return
            
            # Calculate current win streak
            current_streak = 0
            for match in recent_matches:
                if match.won:
                    current_streak += 1
                else:
                    break
            
            # Check for streak achievements
            achievements_to_check = [
                (3, AchievementType.STREAK_3),
                (5, AchievementType.STREAK_5),
                (10, AchievementType.STREAK_10)
            ]
            
            for threshold, achievement_type in achievements_to_check:
                if current_streak >= threshold:
                    await self.award_achievement(session, player.id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking win streak achievements: {e}")
    
    async def check_rating_achievements(self, session, player):
        """Check achievements based on rating milestones"""
        try:
            # Get current rating
            current_rating = await session.execute(
                "SELECT rating FROM ratings WHERE player_id = :player_id ORDER BY updated_at DESC LIMIT 1",
                {"player_id": player.id}
            )
            current_rating = current_rating.scalar_one_or_none()
            
            if not current_rating:
                return
            
            # Check for rating achievements
            achievements_to_check = [
                (1600, AchievementType.RATING_1600),
                (1800, AchievementType.RATING_1800),
                (2000, AchievementType.RATING_2000)
            ]
            
            for threshold, achievement_type in achievements_to_check:
                if current_rating >= threshold:
                    await self.award_achievement(session, player.id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking rating achievements: {e}")
    
    async def check_special_achievements(self, session, player):
        """Check special achievements"""
        try:
            # Check first match achievement
            await self.check_first_match_achievement(session, player)
            
            # Check first win achievement
            await self.check_first_win_achievement(session, player)
            
            # Check perfect match achievements
            await self.check_perfect_match_achievements(session, player)
            
        except Exception as e:
            logger.error(f"Error checking special achievements: {e}")
    
    async def check_first_match_achievement(self, session, player):
        """Check if player should get first match achievement"""
        try:
            # Check if player already has this achievement
            existing = await session.execute(
                "SELECT id FROM achievements WHERE player_id = :player_id AND achievement_type = 'first_match'",
                {"player_id": player.id}
            )
            existing = existing.scalar_one_or_none()
            
            if existing:
                return
            
            # Check if player has played any matches
            match_count = await session.execute(
                """
                SELECT COUNT(*) FROM matches 
                WHERE (player1_id = :player_id OR player2_id = :player_id)
                AND status = 'complete'
                """,
                {"player_id": player.id}
            )
            match_count = match_count.scalar_one_or_none()
            
            if match_count > 0:
                await self.award_achievement(session, player.id, AchievementType.FIRST_MATCH)
                
        except Exception as e:
            logger.error(f"Error checking first match achievement: {e}")
    
    async def check_first_win_achievement(self, session, player):
        """Check if player should get first win achievement"""
        try:
            # Check if player already has this achievement
            existing = await session.execute(
                "SELECT id FROM achievements WHERE player_id = :player_id AND achievement_type = 'first_win'",
                {"player_id": player.id}
            )
            existing = existing.scalar_one_or_none()
            
            if existing:
                return
            
            # Check if player has won any matches
            win_count = await session.execute(
                """
                SELECT COUNT(*) FROM matches 
                WHERE winner_id = :player_id AND status = 'complete'
                """,
                {"player_id": player.id}
            )
            win_count = win_count.scalar_one_or_none()
            
            if win_count > 0:
                await self.award_achievement(session, player.id, AchievementType.FIRST_WIN)
                
        except Exception as e:
            logger.error(f"Error checking first win achievement: {e}")
    
    async def check_perfect_match_achievements(self, session, player):
        """Check for perfect match achievements"""
        try:
            # Check if player already has this achievement
            existing = await session.execute(
                "SELECT id FROM achievements WHERE player_id = :player_id AND achievement_type = 'perfect_match'",
                {"player_id": player.id}
            )
            existing = existing.scalar_one_or_none()
            
            if existing:
                return
            
            # Check for perfect matches (no restarts, clean win)
            perfect_matches = await session.execute(
                """
                SELECT m.*, COUNT(gr.id) as restart_count
                FROM matches m
                LEFT JOIN game_results gr ON m.id = gr.match_id AND gr.is_restart = true
                WHERE m.winner_id = :player_id 
                AND m.status = 'complete'
                GROUP BY m.id
                HAVING COUNT(gr.id) = 0
                """,
                {"player_id": player.id}
            )
            perfect_matches = perfect_matches.fetchall()
            
            if perfect_matches:
                await self.award_achievement(session, player.id, AchievementType.PERFECT_MATCH)
                
        except Exception as e:
            logger.error(f"Error checking perfect match achievements: {e}")
    
    async def award_achievement(self, session, player_id: int, achievement_type: AchievementType):
        """Award an achievement to a player"""
        try:
            # Check if achievement already exists
            existing_achievement = await session.execute(
                "SELECT id FROM achievements WHERE player_id = :player_id AND achievement_type = :achievement_type",
                {"player_id": player_id, "achievement_type": achievement_type.value}
            )
            existing_achievement = existing_achievement.scalar_one_or_none()
            
            if existing_achievement:
                return  # Already awarded
            
            # Create new achievement
            achievement = Achievement(
                player_id=player_id,
                achievement_type=achievement_type,
                unlocked_at=datetime.utcnow()
            )
            
            session.add(achievement)
            
            # Send notification to player
            if Config.ACHIEVEMENT_NOTIFICATIONS:
                await self.notify_achievement_unlocked(player_id, achievement_type)
            
            logger.info(f"Achievement {achievement_type.value} unlocked for player {player_id}")
            
        except Exception as e:
            logger.error(f"Error awarding achievement: {e}")
    
    async def notify_achievement_unlocked(self, player_id: int, achievement_type: AchievementType):
        """Notify player about unlocked achievement"""
        try:
            # Get player's Discord ID
            session = await self.db.get_session()
        async with session as session:
                player = await session.execute(
                    "SELECT discord_id FROM players WHERE id = :player_id",
                    {"player_id": player_id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    return
                
                discord_id = player.discord_id
                user = self.bot.get_user(discord_id)
                
                if user and Config.ACHIEVEMENT_DM_ENABLED:
                    embed = self.create_achievement_notification_embed(achievement_type)
                    
                    try:
                        await user.send(
                            f"🎉 **Новое достижение!**",
                            embed=embed
                        )
                    except discord.Forbidden:
                        # User has DMs disabled
                        logger.info(f"Could not send DM to user {discord_id} - DMs disabled")
                        
        except Exception as e:
            logger.error(f"Error notifying achievement unlock: {e}")
    
    def create_achievement_notification_embed(self, achievement_type: AchievementType):
        """Create embed for achievement notification"""
        embed = discord.Embed(
            title="🏆 Достижение разблокировано!",
            description=f"Поздравляем! Вы разблокировали достижение **{achievement_type.display_name}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Описание",
            value=achievement_type.description,
            inline=False
        )
        
        embed.set_thumbnail(url=achievement_type.icon)
        embed.set_footer(text="Продолжайте играть для разблокировки новых достижений!")
        
        return embed
    
    async def get_player_achievements(self, player_id: int) -> List[Achievement]:
        """Get all achievements for a player"""
        try:
            session = await self.db.get_session()
        async with session as session:
                achievements = await session.execute(
                    "SELECT * FROM achievements WHERE player_id = :player_id ORDER BY unlocked_at DESC",
                    {"player_id": player_id}
                )
                return achievements.fetchall()
        except Exception as e:
            logger.error(f"Error getting player achievements: {e}")
            return []
    
    async def get_player_progress(self, player_id: int) -> List[AchievementProgress]:
        """Get achievement progress for a player"""
        try:
            session = await self.db.get_session()
        async with session as session:
                progress = await session.execute(
                    "SELECT * FROM achievement_progress WHERE player_id = :player_id",
                    {"player_id": player_id}
                )
                return progress.fetchall()
        except Exception as e:
            logger.error(f"Error getting player progress: {e}")
            return []
    
    async def update_achievement_progress(self, player_id: int, achievement_type: AchievementType, increment: int = 1):
        """Update progress towards an achievement"""
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get or create progress record
                progress = await session.execute(
                    "SELECT * FROM achievement_progress WHERE player_id = :player_id AND achievement_type = :achievement_type",
                    {"player_id": player_id, "achievement_type": achievement_type.value}
                )
                progress = progress.scalar_one_or_none()
                
                if not progress:
                    # Create new progress record
                    progress = AchievementProgress(
                        player_id=player_id,
                        achievement_type=achievement_type,
                        current_progress=increment,
                        target_progress=self.get_achievement_target(achievement_type)
                    )
                    session.add(progress)
                else:
                    # Update existing progress
                    progress.current_progress += increment
                    progress.last_updated = datetime.utcnow()
                
                # Check if achievement is completed
                if progress.is_completed:
                    await self.award_achievement(session, player_id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error updating achievement progress: {e}")
    
    def get_achievement_target(self, achievement_type: AchievementType) -> int:
        """Get target progress for an achievement type"""
        targets = {
            AchievementType.MATCHES_10: 10,
            AchievementType.MATCHES_50: 50,
            AchievementType.MATCHES_100: 100,
            AchievementType.STREAK_3: 3,
            AchievementType.STREAK_5: 5,
            AchievementType.STREAK_10: 10,
            # Other achievements are unlocked immediately
        }
        return targets.get(achievement_type, 1)
    
    async def get_achievement_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard based on achievements"""
        try:
            session = await self.db.get_session()
        async with session as session:
                leaderboard = await session.execute(
                    """
                    SELECT p.discord_id, p.username, COUNT(a.id) as achievement_count
                    FROM players p
                    LEFT JOIN achievements a ON p.id = a.player_id
                    GROUP BY p.id, p.discord_id, p.username
                    ORDER BY achievement_count DESC
                    LIMIT :limit
                    """,
                    {"limit": limit}
                )
                return leaderboard.fetchall()
        except Exception as e:
            logger.error(f"Error getting achievement leaderboard: {e}")
            return []