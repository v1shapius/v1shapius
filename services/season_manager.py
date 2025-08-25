import asyncio
import logging
import discord
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_
from database.database import DatabaseManager
from models.season import Season
from models.match import Match, MatchStatus
from models.player import Player

logger = logging.getLogger(__name__)

class SeasonManager:
    """Service for managing seasons and their lifecycle"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.check_interval = 3600  # Check every hour
        self.warning_threshold = 7  # Days before season end to start warnings
        
    async def start_monitoring(self):
        """Start the season monitoring loop"""
        logger.info("Starting season monitoring service")
        while True:
            try:
                await self.check_season_status()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in season monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_season_status(self):
        """Check and update season status"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get current active season
                current_season = await session.execute(
                    select(Season).where(Season.is_active == True)
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    logger.info("No active season found")
                    return
                
                # Check if season is ending soon
                if current_season.is_ending_soon and not current_season.season_end_warning_sent:
                    await self.send_season_end_warnings(session, current_season)
                    current_season.season_end_warning_sent = True
                
                # Check if season should be marked as ending
                if current_season.days_until_end <= self.warning_threshold and not current_season.is_ending:
                    await self.mark_season_as_ending(session, current_season)
                
                # Check if season should end
                if current_season.days_until_end <= 0:
                    await self.end_season(session, current_season)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error checking season status: {e}")
    
    async def send_season_end_warnings(self, session, season: Season):
        """Send warnings to players with active matches"""
        try:
            # Get all active matches
            active_matches = await session.execute(
                select(Match).where(
                    and_(
                        Match.status.in_([
                            MatchStatus.WAITING_PLAYERS,
                            MatchStatus.WAITING_READINESS,
                            MatchStatus.DRAFT_VERIFICATION,
                            MatchStatus.FIRST_PLAYER_SELECTION,
                            MatchStatus.GAME_PREPARATION,
                            MatchStatus.GAME_IN_PROGRESS,
                            MatchStatus.RESULT_CONFIRMATION
                        ]),
                        Match.season_id == season.id
                    )
                )
            )
            active_matches = active_matches.fetchall()
            
            if not active_matches:
                logger.info("No active matches to warn about season end")
                return
            
            # Get unique player IDs from active matches
            player_ids = set()
            for match in active_matches:
                if match.player1_id:
                    player_ids.add(match.player1_id)
                if match.player2_id:
                    player_ids.add(match.player2_id)
            
            # Get player Discord IDs
            players = await session.execute(
                select(Player).where(Player.id.in_(list(player_ids)))
            )
            players = players.fetchall()
            
            # Send warnings to each player
            for player in players:
                await self.send_player_warning(player.discord_id, season)
            
            logger.info(f"Sent season end warnings to {len(players)} players")
            
            # Send guild notification with role tagging
            if hasattr(self.bot, 'role_manager'):
                guild_id = await self.get_guild_id_for_season(session, season)
                if guild_id:
                    tagged_message = await self.bot.role_manager.tag_role_for_event(
                        guild_id=guild_id,
                        event_type="season_end",
                        message="🚨 **Внимание! Сезон завершается** - Завершите активные матчи!"
                    )
                    
                    # Send to guild's system channel or first available channel
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                        if channel:
                            try:
                                await channel.send(tagged_message)
                            except discord.Forbidden:
                                logger.warning(f"Could not send season end warning to guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error sending season end warnings: {e}")
    
    async def get_guild_id_for_season(self, session, season) -> Optional[int]:
        """Get guild ID for a season"""
        try:
            # This is a placeholder - you'll need to implement based on your data structure
            # For now, return None to avoid errors
            return None
        except Exception as e:
            logger.error(f"Error getting guild ID for season: {e}")
            return None
    
    async def send_player_warning(self, discord_id: int, season: Season):
        """Send season end warning to a specific player"""
        try:
            user = self.bot.get_user(discord_id)
            if not user:
                logger.warning(f"Could not find user {discord_id} for season warning")
                return
            
            embed = self.create_season_end_warning_embed(season)
            
            try:
                await user.send(
                    "🚨 **Внимание! Сезон скоро завершается**\n\n"
                    "У вас есть активные матчи, которые должны быть завершены до окончания сезона.",
                    embed=embed
                )
            except discord.Forbidden:
                logger.warning(f"Could not send DM to user {discord_id}")
                
        except Exception as e:
            logger.error(f"Error sending player warning: {e}")
    
    def create_season_end_warning_embed(self, season: Season) -> discord.Embed:
        """Create embed for season end warning"""
        embed = discord.Embed(
            title="🚨 Завершение сезона",
            description="Сезон скоро завершится!",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="Сезон",
            value=season.name,
            inline=True
        )
        
        embed.add_field(
            name="Дней до завершения",
            value=f"**{season.days_until_end}**",
            inline=True
        )
        
        embed.add_field(
            name="Статус",
            value=season.get_status_description(),
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Важно",
            value="Завершите все активные матчи до окончания сезона, иначе они могут быть аннулированы.",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Информация",
            value="После завершения сезона:\n• Новые матчи будут заблокированы\n• Рейтинг будет зафиксирован\n• Начнется новый сезон",
            inline=False
        )
        
        embed.set_footer(text="Сезон автоматически завершится по истечении времени")
        
        return embed
    
    async def mark_season_as_ending(self, session, season: Season):
        """Mark season as ending and block new matches"""
        try:
            season.mark_as_ending()
            season.block_new_matches()
            
            logger.info(f"Season {season.name} marked as ending")
            
            # Send notification to all guilds using this season
            await self.notify_guilds_season_ending(season)
            
        except Exception as e:
            logger.error(f"Error marking season as ending: {e}")
    
    async def notify_guilds_season_ending(self, season: Season):
        """Notify all guilds that season is ending"""
        try:
            # Get unique guild IDs from matches in this season
            session = await self.db.get_session()
        async with session:
                guilds = await session.execute(
                    select(Match.guild_id).where(
                        and_(
                            Match.season_id == season.id,
                            Match.guild_id.isnot(None)
                        )
                    ).distinct()
                )
                guilds = guilds.fetchall()
                
                for guild_row in guilds:
                    guild_id = guild_row[0]
                    await self.notify_guild_season_ending(guild_id, season)
                    
        except Exception as e:
            logger.error(f"Error notifying guilds about season ending: {e}")
    
    async def notify_guild_season_ending(self, guild_id: int, season: Season):
        """Notify a specific guild that season is ending"""
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
                        embed = self.create_guild_season_ending_embed(season)
                        await channel.send(
                            "🚨 **Внимание! Сезон скоро завершается**",
                            embed=embed
                        )
                        
        except Exception as e:
            logger.error(f"Error notifying guild {guild_id}: {e}")
    
    def create_guild_season_ending_embed(self, season: Season) -> discord.Embed:
        """Create embed for guild season ending notification"""
        embed = discord.Embed(
            title="🚨 Завершение сезона",
            description="Сезон скоро завершится!",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="Сезон",
            value=season.name,
            inline=True
        )
        
        embed.add_field(
            name="Дней до завершения",
            value=f"**{season.days_until_end}**",
            inline=True
        )
        
        embed.add_field(
            name="Статус",
            value=season.get_status_description(),
            inline=True
        )
        
        embed.add_field(
            name="📋 Действия",
            value="• Новые матчи заблокированы\n• Завершите активные матчи\n• Рейтинг будет зафиксирован",
            inline=False
        )
        
        embed.set_footer(text="Сезон автоматически завершится по истечении времени")
        
        return embed
    
    async def end_season(self, session, season: Season):
        """End the season and handle cleanup"""
        try:
            # Check if there are still active matches
            active_matches = await session.execute(
                select(Match).where(
                    and_(
                        Match.season_id == season.id,
                        Match.status.in_([
                            MatchStatus.WAITING_PLAYERS,
                            MatchStatus.WAITING_READINESS,
                            MatchStatus.DRAFT_VERIFICATION,
                            MatchStatus.FIRST_PLAYER_SELECTION,
                            MatchStatus.GAME_PREPARATION,
                            MatchStatus.GAME_IN_PROGRESS,
                            MatchStatus.RESULT_CONFIRMATION
                        ])
                    )
                )
            )
            active_matches = active_matches.fetchall()
            
            if active_matches:
                # Force end active matches
                for match in active_matches:
                    match.status = MatchStatus.ANNULLED
                    match.annulment_reason = "Сезон завершен автоматически"
                
                logger.info(f"Force ended {len(active_matches)} active matches due to season end")
            
            # End the season
            season.end_season()
            
            logger.info(f"Season {season.name} ended successfully")
            
            # Notify guilds about season end
            await self.notify_guilds_season_ended(season)
            
        except Exception as e:
            logger.error(f"Error ending season: {e}")
    
    async def notify_guilds_season_ended(self, season: Season):
        """Notify all guilds that season has ended"""
        try:
            # Get unique guild IDs from matches in this season
            session = await self.db.get_session()
        async with session:
                guilds = await session.execute(
                    select(Match.guild_id).where(
                        and_(
                            Match.season_id == season.id,
                            Match.guild_id.isnot(None)
                        )
                    ).distinct()
                )
                guilds = guilds.fetchall()
                
                for guild_row in guilds:
                    guild_id = guild_row[0]
                    await self.notify_guild_season_ended(guild_id, season)
                    
        except Exception as e:
            logger.error(f"Error notifying guilds about season end: {e}")
    
    async def notify_guild_season_ended(self, guild_id: int, season: Season):
        """Notify a specific guild that season has ended"""
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
                        embed = self.create_guild_season_ended_embed(season)
                        await channel.send(
                            "🏁 **Сезон завершен!**",
                            embed=embed
                        )
                        
        except Exception as e:
            logger.error(f"Error notifying guild {guild_id}: {e}")
    
    def create_guild_season_ended_embed(self, season: Season) -> discord.Embed:
        """Create embed for guild season ended notification"""
        embed = discord.Embed(
            title="🏁 Сезон завершен",
            description="Сезон успешно завершен!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Сезон",
            value=season.name,
            inline=True
        )
        
        embed.add_field(
            name="Дата завершения",
            value=season.end_date.strftime("%d.%m.%Y %H:%M"),
            inline=True
        )
        
        embed.add_field(
            name="Статус",
            value="Завершен",
            inline=True
        )
        
        embed.add_field(
            name="📊 Результаты",
            value="• Рейтинг зафиксирован\n• Статистика сохранена\n• Новый сезон скоро начнется",
            inline=False
        )
        
        embed.set_footer(text="Спасибо за участие в сезоне!")
        
        return embed
    
    async def can_create_new_match(self, guild_id: int) -> Tuple[bool, str]:
        """Check if new matches can be created in a guild"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get current active season
                current_season = await session.execute(
                    select(Season).where(Season.is_active == True)
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    return False, "Нет активного сезона"
                
                if current_season.should_block_new_matches:
                    return False, current_season.get_blocking_reason()
                
                return True, "Нет ограничений"
                
        except Exception as e:
            logger.error(f"Error checking if new matches can be created: {e}")
            return False, "Ошибка проверки"
    
    async def get_season_status(self, guild_id: int) -> Optional[Season]:
        """Get current season status for a guild"""
        try:
            session = await self.db.get_session()
        async with session:
                current_season = await session.execute(
                    select(Season).where(Season.is_active == True)
                )
                return current_season.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Error getting season status: {e}")
            return None