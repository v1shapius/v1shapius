import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
from typing import Optional, List
from database.database import DatabaseManager
from models.achievement import Achievement, AchievementType, AchievementProgress
from models.player import Player
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AchievementView(View):
    """View for displaying achievements"""
    
    def __init__(self, player_id: int, achievements: List[Achievement], progress: List[AchievementProgress]):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.achievements = achievements
        self.progress = progress
        self.current_page = 0
        self.items_per_page = 5
        
        # Add navigation buttons
        self.add_item(Button(
            label="◀️",
            custom_id="prev_page",
            style=discord.ButtonStyle.secondary
        ))
        self.add_item(Button(
            label="▶️",
            custom_id="next_page",
            style=discord.ButtonStyle.secondary
        ))
        
        # Add achievement type filter
        achievement_types = [("Все", "all")] + [(at.display_name, at.value) for at in AchievementType]
        self.add_item(Select(
            placeholder="Фильтр по типу",
            options=[discord.SelectOption(label=label, value=value) for label, value in achievement_types],
            custom_id="filter_type"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "Вы можете просматривать только свои достижения.",
                ephemeral=True
            )
            return False
        return True

class Achievements(commands.Cog):
    """Cog for managing player achievements"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        
    @app_commands.command(name="achievements", description="Просмотр достижений")
    async def view_achievements(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """View achievements for yourself or another user"""
        await interaction.response.defer()
        
        try:
            target_user = user or interaction.user
            
            # Get or create player
            async with self.db.get_session() as session:
                player = await session.execute(
                    "SELECT * FROM players WHERE discord_id = :discord_id",
                    {"discord_id": target_user.id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    await interaction.followup.send(
                        f"❌ Игрок {target_user.mention} не найден в системе.",
                        ephemeral=True
                    )
                    return
                
                # Get achievements
                achievements = await session.execute(
                    "SELECT * FROM achievements WHERE player_id = :player_id ORDER BY unlocked_at DESC",
                    {"player_id": player.id}
                )
                achievements = achievements.fetchall()
                
                # Get achievement progress
                progress = await session.execute(
                    "SELECT * FROM achievement_progress WHERE player_id = :player_id",
                    {"player_id": player.id}
                )
                progress = progress.fetchall()
                
                # Create embed
                embed = self.create_achievements_embed(target_user, achievements, progress)
                
                # Create view for interaction
                view = AchievementView(target_user.id, achievements, progress)
                
                await interaction.followup.send(
                    f"🏆 **Достижения {target_user.display_name}**",
                    embed=embed,
                    view=view
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке достижений: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="achievement_progress", description="Прогресс по достижениям")
    async def view_progress(self, interaction: discord.Interaction):
        """View progress towards achievements"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                # Get player
                player = await session.execute(
                    "SELECT * FROM players WHERE discord_id = :discord_id",
                    {"discord_id": interaction.user.id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    await interaction.followup.send(
                        "❌ Вы не найдены в системе.",
                        ephemeral=True
                    )
                    return
                
                # Get achievement progress
                progress = await session.execute(
                    "SELECT * FROM achievement_progress WHERE player_id = :player_id ORDER BY current_progress DESC",
                    {"player_id": player.id}
                )
                progress = progress.fetchall()
                
                if not progress:
                    await interaction.followup.send(
                        "📊 У вас пока нет прогресса по достижениям.",
                        ephemeral=True
                    )
                    return
                
                # Create progress embed
                embed = self.create_progress_embed(interaction.user, progress)
                
                await interaction.followup.send(
                    f"📊 **Прогресс по достижениям**",
                    embed=embed
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке прогресса: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard_achievements", description="Таблица лидеров по достижениям")
    async def leaderboard_achievements(self, interaction: discord.Interaction):
        """Show leaderboard based on achievements"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                # Get top players by achievement count
                top_players = await session.execute(
                    """
                    SELECT p.discord_id, p.username, COUNT(a.id) as achievement_count
                    FROM players p
                    LEFT JOIN achievements a ON p.id = a.player_id
                    GROUP BY p.id, p.discord_id, p.username
                    ORDER BY achievement_count DESC
                    LIMIT 10
                    """
                )
                top_players = top_players.fetchall()
                
                if not top_players:
                    await interaction.followup.send(
                        "📊 Пока нет данных для таблицы лидеров.",
                        ephemeral=True
                    )
                    return
                
                # Create leaderboard embed
                embed = self.create_achievement_leaderboard_embed(top_players)
                
                await interaction.followup.send(
                    "🏆 **Таблица лидеров по достижениям**",
                    embed=embed
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке таблицы лидеров: {str(e)}",
                ephemeral=True
            )
    
    def create_achievements_embed(self, user: discord.Member, achievements: List[Achievement], progress: List[AchievementProgress]) -> discord.Embed:
        """Create embed for achievements display"""
        embed = discord.Embed(
            title=f"🏆 Достижения {user.display_name}",
            description="Ваши разблокированные достижения и прогресс",
            color=discord.Color.gold()
        )
        
        # Achievement statistics
        total_achievements = len(achievements)
        total_possible = len(AchievementType)
        completion_percentage = (total_achievements / total_possible) * 100 if total_possible > 0 else 0
        
        embed.add_field(
            name="📊 Статистика",
            value=f"**Разблокировано**: {total_achievements}/{total_possible}\n**Процент**: {completion_percentage:.1f}%",
            inline=False
        )
        
        # Show recent achievements
        if achievements:
            recent_achievements = achievements[:3]  # Show last 3
            achievement_text = ""
            
            for achievement in recent_achievements:
                achievement_text += f"{achievement.icon} **{achievement.display_name}**\n"
                achievement_text += f"└ {achievement.description}\n"
                achievement_text += f"└ Разблокировано: {achievement.unlocked_at.strftime('%d.%m.%Y')}\n\n"
            
            embed.add_field(
                name="🎯 Последние достижения",
                value=achievement_text[:1024],
                inline=False
            )
        
        # Show progress towards next achievements
        if progress:
            upcoming_achievements = [p for p in progress if not p.is_completed][:3]
            
            if upcoming_achievements:
                progress_text = ""
                
                for prog in upcoming_achievements:
                    achievement_type = AchievementType(prog.achievement_type)
                    progress_text += f"🎯 **{achievement_type.display_name}**\n"
                    progress_text += f"└ Прогресс: {prog.current_progress}/{prog.target_progress} ({prog.progress_percentage:.1f}%)\n\n"
                
                embed.add_field(
                    name="📈 Ближайшие достижения",
                    value=progress_text[:1024],
                    inline=False
                )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Используйте кнопки для навигации")
        
        return embed
    
    def create_progress_embed(self, user: discord.Member, progress: List[AchievementProgress]) -> discord.Embed:
        """Create embed for achievement progress"""
        embed = discord.Embed(
            title=f"📊 Прогресс по достижениям {user.display_name}",
            description="Ваш прогресс к разблокировке достижений",
            color=discord.Color.blue()
        )
        
        # Group progress by achievement type
        progress_by_type = {}
        for prog in progress:
            achievement_type = AchievementType(prog.achievement_type)
            if achievement_type not in progress_by_type:
                progress_by_type[achievement_type] = []
            progress_by_type[achievement_type].append(prog)
        
        # Show progress for each type
        for achievement_type, type_progress in progress_by_type.items():
            progress_text = ""
            
            for prog in type_progress:
                status_emoji = "✅" if prog.is_completed else "🔄"
                progress_text += f"{status_emoji} {prog.current_progress}/{prog.target_progress} ({prog.progress_percentage:.1f}%)\n"
            
            embed.add_field(
                name=f"{achievement_type.icon} {achievement_type.display_name}",
                value=progress_text,
                inline=True
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Продолжайте играть для разблокировки достижений!")
        
        return embed
    
    def create_achievement_leaderboard_embed(self, top_players: List) -> discord.Embed:
        """Create embed for achievement leaderboard"""
        embed = discord.Embed(
            title="🏆 Таблица лидеров по достижениям",
            description="Топ игроков по количеству разблокированных достижений",
            color=discord.Color.gold()
        )
        
        # Create leaderboard text
        leaderboard_text = ""
        
        for i, player_data in enumerate(top_players, 1):
            discord_id = player_data.discord_id
            username = player_data.username
            achievement_count = player_data.achievement_count
            
            # Get medal emoji
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"**{i}.**"
            
            leaderboard_text += f"{medal} <@{discord_id}> - {achievement_count} достижений\n"
        
        embed.add_field(
            name="🏅 Рейтинг",
            value=leaderboard_text,
            inline=False
        )
        
        embed.set_footer(text="Обновляется в реальном времени")
        
        return embed
    
    async def check_and_award_achievements(self, player_id: int, match_id: int, match_result: dict):
        """Check and award achievements based on match result"""
        try:
            async with self.db.get_session() as session:
                # Get player
                player = await session.execute(
                    "SELECT * FROM players WHERE id = :player_id",
                    {"player_id": player_id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    return
                
                # Check various achievement conditions
                await self.check_match_count_achievements(session, player_id)
                await self.check_win_streak_achievements(session, player_id)
                await self.check_rating_achievements(session, player_id)
                await self.check_perfect_match_achievements(session, player_id, match_result)
                
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    async def check_match_count_achievements(self, session, player_id: int):
        """Check achievements based on total match count"""
        try:
            # Get total matches for player
            match_count = await session.execute(
                """
                SELECT COUNT(*) as count
                FROM matches m
                JOIN players p1 ON m.player1_id = p1.id
                JOIN players p2 ON m.player2_id = p2.id
                WHERE (p1.id = :player_id OR p2.id = :player_id)
                AND m.status = 'complete'
                """,
                {"player_id": player_id}
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
                    await self.award_achievement(session, player_id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking match count achievements: {e}")
    
    async def check_win_streak_achievements(self, session, player_id: int):
        """Check achievements based on win streaks"""
        try:
            # Get recent matches for player
            recent_matches = await session.execute(
                """
                SELECT m.*, 
                       CASE WHEN m.winner_id = :player_id THEN 1 ELSE 0 END as won
                FROM matches m
                JOIN players p1 ON m.player1_id = p1.id
                JOIN players p2 ON m.player2_id = p2.id
                WHERE (p1.id = :player_id OR p2.id = :player_id)
                AND m.status = 'complete'
                ORDER BY m.updated_at DESC
                LIMIT 20
                """,
                {"player_id": player_id}
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
                    await self.award_achievement(session, player_id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking win streak achievements: {e}")
    
    async def check_rating_achievements(self, session, player_id: int):
        """Check achievements based on rating milestones"""
        try:
            # Get current rating
            current_rating = await session.execute(
                "SELECT rating FROM ratings WHERE player_id = :player_id ORDER BY updated_at DESC LIMIT 1",
                {"player_id": player_id}
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
                    await self.award_achievement(session, player_id, achievement_type)
                    
        except Exception as e:
            logger.error(f"Error checking rating achievements: {e}")
    
    async def check_perfect_match_achievements(self, session, player_id: int, match_result: dict):
        """Check achievements based on perfect match performance"""
        try:
            # Check if this was a perfect match (no restarts, clean win)
            if match_result.get("no_restarts", False) and match_result.get("clean_win", False):
                await self.award_achievement(session, player_id, AchievementType.PERFECT_MATCH)
                
        except Exception as e:
            logger.error(f"Error checking perfect match achievements: {e}")
    
    async def award_achievement(self, session, player_id: int, achievement_type: AchievementType):
        """Award an achievement to a player"""
        try:
            # Check if achievement already exists
            existing_achievement = await session.execute(
                "SELECT * FROM achievements WHERE player_id = :player_id AND achievement_type = :achievement_type",
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
            await self.notify_achievement_unlocked(player_id, achievement_type)
            
            logger.info(f"Achievement {achievement_type.value} unlocked for player {player_id}")
            
        except Exception as e:
            logger.error(f"Error awarding achievement: {e}")
    
    async def notify_achievement_unlocked(self, player_id: int, achievement_type: AchievementType):
        """Notify player about unlocked achievement"""
        try:
            # Get player's Discord ID
            async with self.db.get_session() as session:
                player = await session.execute(
                    "SELECT discord_id FROM players WHERE id = :player_id",
                    {"player_id": player_id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    return
                
                discord_id = player.discord_id
                user = self.bot.get_user(discord_id)
                
                if user:
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
                    
                    try:
                        await user.send(
                            f"🎉 **Новое достижение!**",
                            embed=embed
                        )
                    except discord.Forbidden:
                        # User has DMs disabled
                        pass
                        
        except Exception as e:
            logger.error(f"Error notifying achievement unlock: {e}")

async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(Achievements(bot))