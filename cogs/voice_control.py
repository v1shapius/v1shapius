import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta

from models.match import Match, MatchStage
from models.penalty_settings import PenaltySettings
from locales import get_text
from config.config import Config

logger = logging.getLogger(__name__)

class VoiceControl(commands.Cog):
    """Cog for controlling voice channels and streams"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_channel_timers = {}  # Track deletion timers
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates"""
        # Check if someone joined or left a match voice channel
        if before.channel != after.channel:
            await self.handle_voice_channel_change(member, before.channel, after.channel)
    
    async def handle_voice_channel_change(self, member: discord.Member, before_channel: Optional[discord.VoiceChannel], 
                                        after_channel: Optional[discord.VoiceChannel]):
        """Handle voice channel changes"""
        try:
            # Check if this is a match voice channel
            if before_channel and before_channel.name.startswith("Match-"):
                await self.handle_voice_channel_leave(member, before_channel)
            
            if after_channel and after_channel.name.startswith("Match-"):
                await self.handle_voice_channel_join(member, after_channel)
                
        except Exception as e:
            logger.error(f"Error handling voice channel change: {e}")
    
    async def handle_voice_channel_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """Handle when someone joins a match voice channel"""
        try:
            # Extract match ID from channel name
            match_id = int(channel.name.split("-")[1])
            
            # Get match from database
            async with self.bot.db_manager.get_session() as session:
                match = await session.get(Match, match_id)
                if not match:
                    return
                
                # Check if this is one of the match players
                if member.id not in [match.player1.discord_id, match.player2.discord_id]:
                    # Kick non-player from voice channel
                    await member.move_to(None)
                    logger.info(f"Kicked non-player {member.name} from match voice channel {channel.name}")
                    return
                
                # Check if both players are now in the channel
                await self.check_both_players_in_channel(match, channel)
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing match ID from channel name {channel.name}: {e}")
        except Exception as e:
            logger.error(f"Error handling voice channel join: {e}")
    
    async def handle_voice_channel_leave(self, member: discord.Member, channel: discord.VoiceChannel):
        """Handle when someone leaves a match voice channel"""
        try:
            # Extract match ID from channel name
            match_id = int(channel.name.split("-")[1])
            
            # Get match from database
            async with self.bot.db_manager.get_session() as session:
                match = await session.get(Match, match_id)
                if not match:
                    return
                
                # Check if this is one of the match players
                if member.id not in [match.player1.discord_id, match.player2.discord_id]:
                    return  # Not a match player
                
                # Check if channel is now empty
                if len(channel.members) == 0:
                    # Schedule channel deletion
                    await self.schedule_voice_channel_deletion(channel, match_id)
                    
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing match ID from channel name {channel.name}: {e}")
        except Exception as e:
            logger.error(f"Error handling voice channel leave: {e}")
    
    async def check_both_players_in_channel(self, match: Match, channel: discord.VoiceChannel):
        """Check if both match players are in the voice channel"""
        try:
            player1_member = channel.guild.get_member(match.player1.discord_id)
            player2_member = channel.guild.get_member(match.player2.discord_id)
            
            if not player1_member or not player2_member:
                return
            
            # Check if both are in the channel
            if (player1_member.voice and player1_member.voice.channel == channel and
                player2_member.voice and player2_member.voice.channel == channel):
                
                # Both players are in the channel
                await self.notify_both_players_ready(match, channel)
                
        except Exception as e:
            logger.error(f"Error checking both players in channel: {e}")
    
    async def notify_both_players_ready(self, match: Match, channel: discord.VoiceChannel):
        """Notify that both players are ready in voice channel"""
        try:
            # Send notification to text channel
            text_channel = channel.guild.get_channel(match.discord_channel_id)
            if text_channel:
                embed = discord.Embed(
                    title="🎧 Voice Channel Ready",
                    description="Both players are now in the voice channel. You can proceed with the match.",
                    color=discord.Color.green()
                )
                
                await text_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error notifying both players ready: {e}")
    
    async def schedule_voice_channel_deletion(self, channel: discord.VoiceChannel, match_id: int):
        """Schedule voice channel deletion after delay"""
        try:
            # Cancel existing timer if any
            if match_id in self.voice_channel_timers:
                self.voice_channel_timers[match_id].cancel()
            
            # Create new timer
            timer = asyncio.create_task(self.delete_voice_channel_after_delay(channel, match_id))
            self.voice_channel_timers[match_id] = timer
            
            logger.info(f"Scheduled deletion of voice channel {channel.name} in {Config.VOICE_CHANNEL_DELETE_DELAY} seconds")
            
        except Exception as e:
            logger.error(f"Error scheduling voice channel deletion: {e}")
    
    async def delete_voice_channel_after_delay(self, channel: discord.VoiceChannel, match_id: int):
        """Delete voice channel after specified delay"""
        try:
            # Wait for the specified delay
            await asyncio.sleep(Config.VOICE_CHANNEL_DELETE_DELAY)
            
            # Check if channel still exists and is empty
            if channel and len(channel.members) == 0:
                await channel.delete()
                logger.info(f"Deleted empty voice channel {channel.name}")
                
                # Remove timer reference
                if match_id in self.voice_channel_timers:
                    del self.voice_channel_timers[match_id]
                
                # Notify in text channel if possible
                await self.notify_voice_channel_deleted(channel.guild, match_id)
                
        except discord.NotFound:
            # Channel already deleted
            logger.info(f"Voice channel {channel.name} was already deleted")
        except Exception as e:
            logger.error(f"Error deleting voice channel: {e}")
    
    async def notify_voice_channel_deleted(self, guild: discord.Guild, match_id: int):
        """Notify that voice channel was deleted"""
        try:
            # Get match to find text channel
            async with self.bot.db_manager.get_session() as session:
                match = await session.get(Match, match_id)
                if not match:
                    return
                
                text_channel = guild.get_channel(match.discord_channel_id)
                if text_channel:
                    embed = discord.Embed(
                        title="🗑️ Voice Channel Deleted",
                        description="The voice channel has been automatically deleted as it was empty.",
                        color=discord.Color.orange()
                    )
                    
                    await text_channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error notifying voice channel deletion: {e}")
    
    async def check_stream_status(self, member: discord.Member) -> bool:
        """Check if a member is currently streaming"""
        try:
            if not member.voice:
                return False
            
            # Check if member is streaming
            return member.voice.self_stream or member.voice.self_video
            
        except Exception as e:
            logger.error(f"Error checking stream status: {e}")
            return False
    
    async def force_stream_check(self, member: discord.Member, match_id: int) -> bool:
        """Force check stream status and return result"""
        try:
            stream_active = await self.check_stream_status(member)
            
            if stream_active:
                # Send warning about active stream
                text_channel = await self.get_match_text_channel(match_id)
                if text_channel:
                    embed = discord.Embed(
                        title="⚠️ Stream Still Active",
                        description=f"{member.mention} still has an active stream. Please turn it off to continue.",
                        color=discord.Color.red()
                    )
                    
                    await text_channel.send(embed=embed)
            
            return not stream_active  # Return True if stream is OFF
            
        except Exception as e:
            logger.error(f"Error in force stream check: {e}")
            return False
    
    async def get_match_text_channel(self, match_id: int) -> Optional[discord.TextChannel]:
        """Get the text channel for a match"""
        try:
            async with self.bot.db_manager.get_session() as session:
                match = await session.get(Match, match_id)
                if not match:
                    return None
                
                # Get guild from any available context
                # This is a simplified approach - in practice you'd store guild reference
                for guild in self.bot.guilds:
                    if guild.id == match.discord_guild_id:
                        return guild.get_channel(match.discord_channel_id)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting match text channel: {e}")
            return None
    
    @app_commands.command(name="stream", description="Check stream status")
    async def check_stream(self, interaction: discord.Interaction):
        """Check stream status command"""
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice:
                await interaction.response.send_message(
                    "❌ You are not in a voice channel.",
                    ephemeral=True
                )
                return
            
            # Check stream status
            stream_active = await self.check_stream_status(interaction.user)
            
            if stream_active:
                embed = discord.Embed(
                    title="📺 Stream Status",
                    description="You currently have an active stream.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="📺 Stream Status",
                    description="No active stream detected.",
                    color=discord.Color.green()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error checking stream status: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while checking stream status.",
                ephemeral=True
            )
    
    async def cleanup_timers(self):
        """Clean up voice channel deletion timers"""
        try:
            # Cancel all active timers
            for match_id, timer in self.voice_channel_timers.items():
                if not timer.done():
                    timer.cancel()
            
            self.voice_channel_timers.clear()
            logger.info("Cleaned up voice channel deletion timers")
            
        except Exception as e:
            logger.error(f"Error cleaning up timers: {e}")

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(VoiceControl(bot))