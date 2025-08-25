import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional
import asyncio
import logging
from database.database import DatabaseManager
from models.penalty_settings import PenaltySettings
from models.match import Match

logger = logging.getLogger(__name__)

class VoiceChannelView(View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
        
        self.add_item(Button(
            label="🎮 Присоединиться к матчу",
            custom_id="join_match_voice",
            style=discord.ButtonStyle.primary
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.data.get("custom_id") == "join_match_voice":
            return False
            
        try:
            # Get match and create voice channel
            db_manager = DatabaseManager()
        session = await db_manager.get_session()
        async with session:
                match = await session.get(Match, self.match_id)
                if not match:
                    await interaction.response.send_message(
                        "❌ Матч не найден.",
                        ephemeral=True
                    )
                    return False
                
                # Check if voice channel already exists
                if match.voice_channel_id:
                    voice_channel = interaction.guild.get_channel(match.voice_channel_id)
                    if voice_channel:
                        await interaction.response.send_message(
                            f"🎮 Голосовой канал уже создан: {voice_channel.mention}",
                            ephemeral=True
                        )
                        return False
                
                # Get guild settings for voice category
                settings = await session.get(PenaltySettings, interaction.guild_id)
                voice_category = None
                
                if settings and settings.voice_category_id:
                    voice_category = interaction.guild.get_channel(settings.voice_category_id)
                
                # Create voice channel
                channel_name = f"Матч-{match.id}"
                if voice_category:
                    voice_channel = await interaction.guild.create_voice_channel(
                        name=channel_name,
                        category=voice_category,
                        user_limit=2,
                        reason=f"Voice channel for match {match.id}"
                    )
                else:
                    voice_channel = await interaction.guild.create_voice_channel(
                        name=channel_name,
                        user_limit=2,
                        reason=f"Voice channel for match {match.id}"
                    )
                
                # Update match with voice channel ID
                match.voice_channel_id = voice_channel.id
                await session.commit()
                
                await interaction.response.send_message(
                    f"🎮 Голосовой канал создан: {voice_channel.mention}",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error creating voice channel: {e}")
            await interaction.response.send_message(
                f"❌ Ошибка при создании голосового канала: {str(e)}",
                ephemeral=True
            )
            
        return True

class VoiceControl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.voice_channels_to_delete = {}  # {channel_id: task}
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates"""
        # Check if member joined a match voice channel
        if (before.channel != after.channel and 
            after.channel and 
            after.channel.name.startswith("Матч-")):
            
            await self.handle_player_joined_voice(member, after.channel)
            
        # Check if member left a match voice channel
        elif (before.channel and 
              before.channel.name.startswith("Матч-") and 
              after.channel != before.channel):
            
            await self.handle_player_left_voice(member, before.channel)
    
    async def handle_player_joined_voice(self, member: discord.Member, voice_channel: discord.VoiceChannel):
        """Handle when a player joins a match voice channel"""
        try:
            # Extract match ID from channel name
            match_id = int(voice_channel.name.split("-")[1])
            
            session = await self.db.get_session()
        async with session:
                match = await session.get(Match, match_id)
                if not match:
                    return
                
                # Check if this is one of the match players
                player1 = await session.execute(
                    "SELECT * FROM players WHERE id = :player_id",
                    {"player_id": match.player1_id}
                )
                player1 = player1.scalar_one_or_none()
                
                player2 = await session.execute(
                    "SELECT * FROM players WHERE id = :player_id",
                    {"player_id": match.player2_id}
                )
                player2 = player2.scalar_one_or_none()
                
                if not player1 or not player2:
                    return
                
                # Check if member is one of the players
                if member.id not in [player1.discord_id, player2.discord_id]:
                    # Kick non-player from voice channel
                    try:
                        await member.move_to(None, reason="Not a match player")
                        await member.send(
                            f"❌ Вы не являетесь участником матча в канале {voice_channel.name}"
                        )
                    except discord.Forbidden:
                        logger.warning(f"Cannot kick {member.name} from voice channel {voice_channel.id}")
                    return
                
                # Check if both players are now in the voice channel
                player1_member = voice_channel.guild.get_member(player1.discord_id)
                player2_member = voice_channel.guild.get_member(player2.discord_id)
                
                if (player1_member and player1_member.voice and 
                    player1_member.voice.channel == voice_channel and
                    player2_member and player2_member.voice and 
                    player2_member.voice.channel == voice_channel):
                    
                    # Both players are in voice channel, check stream status
                    await self.check_stream_status(match, voice_channel)
                    
        except Exception as e:
            logger.error(f"Error handling player joined voice: {e}")
    
    async def handle_player_left_voice(self, member: discord.Member, voice_channel: discord.VoiceChannel):
        """Handle when a player leaves a match voice channel"""
        try:
            # Extract match ID from channel name
            match_id = int(voice_channel.name.split("-")[1])
            
            session = await self.db.get_session()
        async with session:
                match = await session.get(Match, match_id)
                if not match:
                    return
                
                # Check if channel is empty
                if len(voice_channel.members) == 0:
                    # Schedule channel deletion
                    await self.schedule_voice_channel_deletion(voice_channel.id, match.id)
                    
        except Exception as e:
            logger.error(f"Error handling player left voice: {e}")
    
    async def check_stream_status(self, match: Match, voice_channel: discord.VoiceChannel):
        """Check stream status of both players"""
        try:
            # Get player members
            session = await self.db.get_session()
        async with session:
                player1 = await session.execute(
                    "SELECT * FROM players WHERE id = :player_id",
                    {"player_id": match.player1_id}
                )
                player1 = player1.scalar_one_or_none()
                
                player2 = await session.execute(
                    "SELECT * FROM players WHERE id = :player_id",
                    {"player_id": match.player2_id}
                )
                player2 = player2.scalar_one_or_none()
                
                if not player1 or not player2:
                    return
                
                player1_member = voice_channel.guild.get_member(player1.discord_id)
                player2_member = voice_channel.guild.get_member(player2.discord_id)
                
                if not player1_member or not player2_member:
                    return
                
                # Check who is streaming
                player1_streaming = player1_member.voice and player1_member.voice.self_stream
                player2_streaming = player2_member.voice and player2_member.voice.self_stream
                
                # Send stream status to match thread
                if match.thread_id:
                    thread = voice_channel.guild.get_thread(match.thread_id)
                    if thread:
                        embed = discord.Embed(
                            title="📺 Статус трансляций",
                            description="Проверка трансляций игроков",
                            color=discord.Color.blue()
                        )
                        
                        embed.add_field(
                            name=f"{player1_member.display_name}",
                            value="🔴 Транслирует" if player1_streaming else "⚫ Не транслирует",
                            inline=True
                        )
                        
                        embed.add_field(
                            name=f"{player2_member.display_name}",
                            value="🔴 Транслирует" if player2_streaming else "⚫ Не транслирует",
                            inline=True
                        )
                        
                        await thread.send(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error checking stream status: {e}")
    
    async def schedule_voice_channel_deletion(self, channel_id: int, match_id: int):
        """Schedule voice channel deletion after delay"""
        try:
            # Cancel existing deletion task if exists
            if channel_id in self.voice_channels_to_delete:
                self.voice_channels_to_delete[channel_id].cancel()
            
            # Create new deletion task
            task = asyncio.create_task(self.delete_voice_channel_after_delay(channel_id, match_id))
            self.voice_channels_to_delete[channel_id] = task
            
        except Exception as e:
            logger.error(f"Error scheduling voice channel deletion: {e}")
    
    async def delete_voice_channel_after_delay(self, channel_id: int, match_id: int):
        """Delete voice channel after specified delay"""
        try:
            # Wait for deletion delay
            await asyncio.sleep(300)  # 5 minutes
            
            # Get the channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            # Check if channel is still empty
            if len(channel.members) > 0:
                return
            
            # Delete the channel
            await channel.delete(reason=f"Match {match_id} voice channel cleanup")
            
            # Remove from tracking
            if channel_id in self.voice_channels_to_delete:
                del self.voice_channels_to_delete[channel_id]
                
            # Update match in database
            session = await self.db.get_session()
        async with session:
                match = await session.get(Match, match_id)
                if match:
                    match.voice_channel_id = None
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Error deleting voice channel: {e}")
            # Remove from tracking even if error occurred
            if channel_id in self.voice_channels_to_delete:
                del self.voice_channels_to_delete[channel_id]

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceControl(bot))