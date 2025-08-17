import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from models.match import Match, MatchFormat, MatchStatus, MatchStage
from models.player import Player
from models.game_result import GameResult
from models.penalty_settings import PenaltySettings
from locales import get_text
from config.config import Config

logger = logging.getLogger(__name__)

class MatchCreationModal(Modal, title="Create Match"):
    """Modal for creating a new match"""
    
    def __init__(self):
        super().__init__()
        self.format_input = TextInput(
            label="Match Format",
            placeholder="bo1, bo2, or bo3",
            required=True,
            max_length=3
        )
        self.opponent_input = TextInput(
            label="Opponent Discord ID",
            placeholder="123456789012345678",
            required=True,
            max_length=20
        )
        
        self.add_item(self.format_input)
        self.add_item(self.opponent_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            format_str = self.format_input.value.lower()
            opponent_id = int(self.opponent_input.value)
            
            # Validate format
            if format_str not in ['bo1', 'bo2', 'bo3']:
                await interaction.response.send_message(
                    "❌ Invalid format. Use bo1, bo2, or bo3.",
                    ephemeral=True
                )
                return
            
            # Validate opponent
            opponent = interaction.guild.get_member(opponent_id)
            if not opponent:
                await interaction.response.send_message(
                    "❌ Opponent not found in this server.",
                    ephemeral=True
                )
                return
            
            if opponent.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You cannot create a match with yourself.",
                    ephemeral=True
                )
                return
            
            # Create match
            await self.create_match(interaction, format_str, opponent)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid opponent ID. Please enter a valid Discord user ID.",
                ephemeral=True
            )
    
    async def create_match(self, interaction: discord.Interaction, format_str: str, opponent: discord.Member):
        """Create a new match"""
        bot = interaction.client
        
        # Get or create players
        player1 = await bot.db_manager.get_or_create_player(
            interaction.user.id,
            interaction.user.name,
            interaction.user.display_name
        )
        player2 = await bot.db_manager.get_or_create_player(
            opponent.id,
            opponent.name,
            opponent.display_name
        )
        
        # Create match
        match = Match(
            discord_guild_id=interaction.guild.id,
            discord_channel_id=interaction.channel.id,
            player1_id=player1.id,
            player2_id=player2.id,
            format=MatchFormat(format_str),
            status=MatchStatus.WAITING,
            current_stage=MatchStage.WAITING_READINESS
        )
        
        async with bot.db_manager.get_session() as session:
            session.add(match)
            await session.commit()
            await session.refresh(match)
        
        # Create voice channel
        voice_channel = await interaction.guild.create_voice_channel(
            name=f"Match-{match.id}",
            user_limit=2
        )
        
        # Update match with voice channel ID
        async with bot.db_manager.get_session() as session:
            match.discord_voice_channel_id = voice_channel.id
            await session.commit()
        
        # Send match creation message
        embed = discord.Embed(
            title=get_text("MATCH_CREATION", "title"),
            description=get_text("MATCH_CREATION", "description"),
            color=discord.Color.blue()
        )
        embed.add_field(
            name=get_text("MATCH_CREATION", "player1"),
            value=interaction.user.mention,
            inline=True
        )
        embed.add_field(
            name=get_text("MATCH_CREATION", "player2"),
            value=opponent.mention,
            inline=True
        )
        embed.add_field(
            name=get_text("MATCH_CREATION", "format"),
            value=get_text("FORMATS", format_str),
            inline=True
        )
        embed.add_field(
            name=get_text("MATCH_CREATION", "status"),
            value=get_text("STATUSES", "waiting"),
            inline=True
        )
        embed.add_field(
            name=get_text("MATCH_CREATION", "created_at"),
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=True
        )
        
        # Create join buttons
        view = MatchJoinView(match.id)
        
        await interaction.response.send_message(
            content=get_text("MATCH_CREATION", "voice_channel_created", channel_name=voice_channel.mention),
            embed=embed,
            view=view
        )

class MatchJoinView(View):
    """View for joining a match"""
    
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
    
    @discord.ui.button(label="Join Match", style=discord.ButtonStyle.primary, custom_id="join_match")
    async def join_match(self, interaction: discord.Interaction, button: Button):
        """Handle match join button click"""
        await self.join_match_handler(interaction)
    
    async def join_match_handler(self, interaction: discord.Interaction):
        """Handle joining a match"""
        bot = interaction.client
        
        # Get match
        async with bot.db_manager.get_session() as session:
            match = await session.get(Match, self.match_id)
            if not match:
                await interaction.response.send_message(
                    get_text("ERRORS", "match_not_found"),
                    ephemeral=True
                )
                return
            
            # Check if user is one of the players
            if interaction.user.id not in [match.player1.discord_id, match.player2.discord_id]:
                await interaction.response.send_message(
                    "❌ You are not a player in this match.",
                    ephemeral=True
                )
                return
            
            # Check if already joined
            if match.status != MatchStatus.WAITING:
                await interaction.response.send_message(
                    "❌ This match is no longer accepting players.",
                    ephemeral=True
                )
                return
        
        # Update match status if both players joined
        await self.check_match_readiness(interaction, match)
    
    async def check_match_readiness(self, interaction: discord.Interaction, match: Match):
        """Check if both players are ready to proceed"""
        # Check if both players are in voice channel
        voice_channel = interaction.guild.get_channel(match.discord_voice_channel_id)
        if not voice_channel:
            await interaction.response.send_message(
                "❌ Voice channel not found.",
                ephemeral=True
                )
            return
        
        # Get player members
        player1_member = interaction.guild.get_member(match.player1.discord_id)
        player2_member = interaction.guild.get_channel(match.player2.discord_id)
        
        if not player1_member or not player2_member:
            await interaction.response.send_message(
                "❌ One or both players not found in server.",
                ephemeral=True
            )
            return
        
        # Check if both are in voice channel
        if (player1_member.voice is None or 
            player1_member.voice.channel != voice_channel or
            player2_member.voice is None or 
            player2_member.voice.channel != voice_channel):
            
            await interaction.response.send_message(
                get_text("MATCH_CREATION", "waiting_players"),
                ephemeral=True
            )
            return
        
        # Both players are in voice channel, proceed to readiness confirmation
        await self.start_readiness_confirmation(interaction, match)
    
    async def start_readiness_confirmation(self, interaction: discord.Interaction, match: Match):
        """Start the readiness confirmation process"""
        # Update match stage
        async with interaction.client.db_manager.get_session() as session:
            match.current_stage = MatchStage.WAITING_READINESS
            await session.commit()
        
        # Send readiness confirmation message
        embed = discord.Embed(
            title="⏳ Match Ready to Begin",
            description="Both players are in the voice channel. Please confirm your readiness.",
            color=discord.Color.yellow()
        )
        
        view = ReadinessConfirmationView(match.id)
        
        await interaction.response.send_message(
            content=get_text("MATCH_CREATION", "both_players_joined"),
            embed=embed,
            view=view
        )

class ReadinessConfirmationView(View):
    """View for confirming readiness"""
    
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
    
    @discord.ui.button(label="I'm Ready", style=discord.ButtonStyle.success, custom_id="ready")
    async def confirm_readiness(self, interaction: discord.Interaction, button: Button):
        """Handle readiness confirmation"""
        await self.confirm_readiness_handler(interaction)
    
    async def confirm_readiness_handler(self, interaction: discord.Interaction):
        """Handle readiness confirmation"""
        bot = interaction.client
        
        # Get match
        async with bot.db_manager.get_session() as session:
            match = await session.get(Match, self.match_id)
            if not match:
                await interaction.response.send_message(
                    get_text("ERRORS", "match_not_found"),
                    ephemeral=True
                )
                return
            
            # Check if user is one of the players
            if interaction.user.id not in [match.player1.discord_id, match.player2.discord_id]:
                await interaction.response.send_message(
                    "❌ You are not a player in this match.",
                    ephemeral=True
                )
                return
        
        # Store readiness confirmation
        # This would typically be stored in a more sophisticated way
        # For now, we'll proceed to the next stage
        
        await interaction.response.send_message(
            get_text("SUCCESS", "readiness_confirmed"),
            ephemeral=True
        )
        
        # Move to draft verification stage
        await self.proceed_to_draft_verification(interaction, match)
    
    async def proceed_to_draft_verification(self, interaction: discord.Interaction, match: Match):
        """Proceed to draft verification stage"""
        # Update match stage
        async with interaction.client.db_manager.get_session() as session:
            match.current_stage = MatchStage.WAITING_DRAFT
            await session.commit()
        
        # Send draft verification message
        embed = discord.Embed(
            title=get_text("DRAFT_VERIFICATION", "title"),
            description=get_text("DRAFT_VERIFICATION", "description"),
            color=discord.Color.blue()
        )
        
        view = DraftVerificationView(match.id)
        
        await interaction.channel.send(
            content=get_text("DRAFT_VERIFICATION", "waiting_both"),
            embed=embed,
            view=view
        )

class DraftVerificationView(View):
    """View for draft verification"""
    
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
    
    @discord.ui.button(label="Submit Draft", style=discord.ButtonStyle.primary, custom_id="submit_draft")
    async def submit_draft(self, interaction: discord.Interaction, button: Button):
        """Handle draft submission"""
        await self.submit_draft_handler(interaction)
    
    async def submit_draft_handler(self, interaction: discord.Interaction):
        """Handle draft submission"""
        # Open draft submission modal
        modal = DraftSubmissionModal(self.match_id)
        await interaction.response.send_modal(modal)

class DraftSubmissionModal(Modal, title="Submit Draft Link"):
    """Modal for submitting draft link"""
    
    def __init__(self, match_id: int):
        super().__init__()
        self.match_id = match_id
        
        self.draft_link = TextInput(
            label="Draft Link",
            placeholder="https://example.com/draft/...",
            required=True,
            max_length=500
        )
        
        self.add_item(self.draft_link)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle draft submission"""
        # This would implement the draft verification logic
        # For now, we'll just acknowledge the submission
        
        await interaction.response.send_message(
            "✅ Draft link submitted. Waiting for opponent...",
            ephemeral=True
        )

class MatchManagement(commands.Cog):
    """Cog for managing matches"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="match", description="Create a new match")
    async def create_match(self, interaction: discord.Interaction):
        """Create a new match command"""
        # Check if user is already in a match
        # This would check the database for active matches
        
        # Open match creation modal
        modal = MatchCreationModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="matches", description="View your active matches")
    async def view_matches(self, interaction: discord.Interaction):
        """View active matches command"""
        # This would query the database for active matches
        await interaction.response.send_message(
            "📋 Active matches functionality coming soon!",
            ephemeral=True
        )

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(MatchManagement(bot))