import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import logging
from typing import Optional, Dict
import re

from models.match import Match, MatchStage
from locales import get_text

logger = logging.getLogger(__name__)

class DraftVerification(commands.Cog):
    """Cog for handling draft verification and confirmation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_drafts = {}  # Store pending draft submissions
    
    async def submit_draft_link(self, interaction: discord.Interaction, match_id: int, draft_link: str):
        """Submit a draft link for verification"""
        try:
            # Validate draft link format
            if not self.is_valid_draft_link(draft_link):
                await interaction.response.send_message(
                    "❌ Invalid draft link format. Please provide a valid URL.",
                    ephemeral=True
                )
                return
            
            # Get match
            session = await self.bot.db_manager.get_session()
        async with session:
                match = await session.get(Match, match_id)
                if not match:
                    await interaction.response.send_message(
                        get_text("ERRORS", "match_not_found"),
                        ephemeral=True
                    )
                    return
                
                # Check if user is one of the match players
                if interaction.user.id not in [match.player1.discord_id, match.player2.discord_id]:
                    await interaction.response.send_message(
                        "❌ You are not a player in this match.",
                        ephemeral=True
                    )
                    return
            
            # Store draft submission
            player_id = interaction.user.id
            if match_id not in self.pending_drafts:
                self.pending_drafts[match_id] = {}
            
            self.pending_drafts[match_id][player_id] = draft_link
            
            await interaction.response.send_message(
                "✅ Draft link submitted successfully. Waiting for opponent...",
                ephemeral=True
            )
            
            # Check if both players have submitted
            await self.check_draft_submissions(interaction, match_id, match)
            
        except Exception as e:
            logger.error(f"Error submitting draft link: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while submitting the draft link.",
                ephemeral=True
            )
    
    async def check_draft_submissions(self, interaction: discord.Interaction, match_id: int, match: Match):
        """Check if both players have submitted draft links"""
        try:
            if match_id not in self.pending_drafts:
                return
            
            submissions = self.pending_drafts[match_id]
            
            # Check if both players have submitted
            player1_id = match.player1.discord_id
            player2_id = match.player2.discord_id
            
            if player1_id in submissions and player2_id in submissions:
                # Both players have submitted, compare links
                link1 = submissions[player1_id]
                link2 = submissions[player2_id]
                
                if link1 == link2:
                    # Links match, confirm draft
                    await self.confirm_draft(interaction, match_id, match, link1)
                else:
                    # Links don't match, notify players
                    await self.notify_draft_mismatch(interaction, match_id, match)
                
                # Clear pending submissions
                del self.pending_drafts[match_id]
            
        except Exception as e:
            logger.error(f"Error checking draft submissions: {e}")
    
    async def confirm_draft(self, interaction: discord.Interaction, match_id: int, match: Match, draft_link: str):
        """Confirm draft when both players submit matching links"""
        try:
            # Update match with draft link
            session = await self.bot.db_manager.get_session()
        async with session:
                match.draft_link = draft_link
                match.current_stage = MatchStage.WAITING_FIRST_PLAYER
                await session.commit()
            
            # Send confirmation message
            embed = discord.Embed(
                title=get_text("DRAFT_VERIFICATION", "title"),
                description=get_text("DRAFT_VERIFICATION", "links_match"),
                color=discord.Color.green()
            )
            embed.add_field(name="Draft Link", value=draft_link, inline=False)
            
            # Create first player selection view
            view = FirstPlayerSelectionView(match_id)
            
            await interaction.channel.send(
                content=get_text("DRAFT_VERIFICATION", "draft_confirmed"),
                embed=embed,
                view=view
            )
            
        except Exception as e:
            logger.error(f"Error confirming draft: {e}")
            await interaction.channel.send(
                "❌ An error occurred while confirming the draft.",
                ephemeral=True
            )
    
    async def notify_draft_mismatch(self, interaction: discord.Interaction, match_id: int, match: Match):
        """Notify players that draft links don't match"""
        try:
            embed = discord.Embed(
                title="❌ Draft Links Don't Match",
                description=get_text("DRAFT_VERIFICATION", "links_dont_match"),
                color=discord.Color.red()
            )
            
            # Create new draft submission view
            view = DraftVerificationView(match_id)
            
            await interaction.channel.send(
                content=get_text("DRAFT_VERIFICATION", "links_dont_match"),
                embed=embed,
                view=view
            )
            
        except Exception as e:
            logger.error(f"Error notifying draft mismatch: {e}")
    
    def is_valid_draft_link(self, link: str) -> bool:
        """Validate draft link format"""
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(link))
    
    async def get_draft_status(self, match_id: int) -> Dict:
        """Get current draft submission status"""
        if match_id not in self.pending_drafts:
            return {"status": "no_submissions"}
        
        submissions = self.pending_drafts[match_id]
        return {
            "status": "pending",
            "submissions": len(submissions),
            "total_players": 2
        }

class DraftVerificationView(View):
    """View for draft verification"""
    
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
    
    @discord.ui.button(label="Submit Draft", style=discord.ButtonStyle.primary, custom_id="submit_draft")
    async def submit_draft(self, interaction: discord.Interaction, button: Button):
        """Handle draft submission button click"""
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
        """Handle modal submission"""
        # Get the cog instance
        cog = interaction.client.get_cog("DraftVerification")
        if cog:
            await cog.submit_draft_link(interaction, self.match_id, self.draft_link.value)
        else:
            await interaction.response.send_message(
                "❌ Draft verification system not available.",
                ephemeral=True
            )

class FirstPlayerSelectionView(View):
    """View for selecting who goes first"""
    
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.player1_choice = None
        self.player2_choice = None
    
    @discord.ui.button(label="Player 1 Goes First", style=discord.ButtonStyle.primary, custom_id="player1_first")
    async def player1_first(self, interaction: discord.Interaction, button: Button):
        """Handle player 1 first choice"""
        await self.handle_player_choice(interaction, "player1_first")
    
    @discord.ui.button(label="Player 2 Goes First", style=discord.ButtonStyle.secondary, custom_id="player2_first")
    async def player2_first(self, interaction: discord.Interaction, button: Button):
        """Handle player 2 first choice"""
        await self.handle_player_choice(interaction, "player2_first")
    
    async def handle_player_choice(self, interaction: discord.Interaction, choice: str):
        """Handle player choice for first player"""
        try:
            # Get match
            session = await interaction.client.db_manager.get_session()
        async with session:
                match = await session.get(Match, self.match_id)
                if not match:
                    await interaction.response.send_message(
                        get_text("ERRORS", "match_not_found"),
                        ephemeral=True
                    )
                    return
                
                # Check if user is one of the match players
                if interaction.user.id not in [match.player1.discord_id, match.player2.discord_id]:
                    await interaction.response.send_message(
                        "❌ You are not a player in this match.",
                        ephemeral=True
                    )
                    return
                
                # Store player choice
                if interaction.user.id == match.player1.discord_id:
                    self.player1_choice = choice
                else:
                    self.player2_choice = choice
                
                await interaction.response.send_message(
                    f"✅ You chose: {choice}",
                    ephemeral=True
                )
                
                # Check if both players have made their choice
                await self.check_both_choices(interaction, match)
                
        except Exception as e:
            logger.error(f"Error handling player choice: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your choice.",
                ephemeral=True
            )
    
    async def check_both_choices(self, interaction: discord.Interaction, match: Match):
        """Check if both players have made their choice"""
        try:
            if self.player1_choice and self.player2_choice:
                if self.player1_choice == self.player2_choice:
                    # Choices match, proceed to game preparation
                    await self.proceed_to_game_preparation(interaction, match, self.player1_choice)
                else:
                    # Choices don't match, ask players to coordinate
                    await self.notify_choice_mismatch(interaction, match)
                    
                    # Reset choices for next attempt
                    self.player1_choice = None
                    self.player2_choice = None
            
        except Exception as e:
            logger.error(f"Error checking both choices: {e}")
    
    async def proceed_to_game_preparation(self, interaction: discord.Interaction, match: Match, choice: str):
        """Proceed to game preparation stage"""
        try:
            # Determine first player
            if choice == "player1_first":
                first_player_id = match.player1_id
                first_player_name = "Player 1"
            else:
                first_player_id = match.player2_id
                first_player_name = "Player 2"
            
            # Update match
            session = await interaction.client.db_manager.get_session()
        async with session:
                match.first_player_id = first_player_id
                match.current_stage = MatchStage.PREPARING_GAME
                await session.commit()
            
            # Send confirmation
            embed = discord.Embed(
                title=get_text("FIRST_PLAYER_SELECTION", "title"),
                description=get_text("FIRST_PLAYER_SELECTION", "choices_match"),
                color=discord.Color.green()
            )
            embed.add_field(
                name="First Player",
                value=first_player_name,
                inline=True
            )
            
            # Create game preparation view
            view = GamePreparationView(self.match_id, first_player_id)
            
            await interaction.channel.send(
                content=get_text("FIRST_PLAYER_SELECTION", "first_player_selected", player_name=first_player_name),
                embed=embed,
                view=view
            )
            
        except Exception as e:
            logger.error(f"Error proceeding to game preparation: {e}")
            await interaction.channel.send(
                "❌ An error occurred while preparing the game.",
                ephemeral=True
            )
    
    async def notify_choice_mismatch(self, interaction: discord.Interaction, match: Match):
        """Notify that player choices don't match"""
        embed = discord.Embed(
            title="❌ Choices Don't Match",
            description=get_text("FIRST_PLAYER_SELECTION", "choices_dont_match"),
            color=discord.Color.red()
        )
        
        await interaction.channel.send(
            content=get_text("FIRST_PLAYER_SELECTION", "choices_dont_match"),
            embed=embed
        )

class GamePreparationView(View):
    """View for game preparation"""
    
    def __init__(self, match_id: int, first_player_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.first_player_id = first_player_id
        self.first_player_ready = False
        self.second_player_confirmed = False
    
    @discord.ui.button(label="I'm Ready", style=discord.ButtonStyle.success, custom_id="ready")
    async def ready(self, interaction: discord.Interaction, button: Button):
        """Handle ready button click"""
        await self.handle_ready(interaction)
    
    @discord.ui.button(label="Confirm Draft & Stream", style=discord.ButtonStyle.primary, custom_id="confirm_draft")
    async def confirm_draft(self, interaction: discord.Interaction, button: Button):
        """Handle draft confirmation button click"""
        await self.handle_draft_confirmation(interaction)
    
    async def handle_ready(self, interaction: discord.Interaction):
        """Handle first player ready button"""
        try:
            # Get match
            session = await interaction.client.db_manager.get_session()
        async with session:
                match = await session.get(Match, self.match_id)
                if not match:
                    await interaction.response.send_message(
                        get_text("ERRORS", "match_not_found"),
                        ephemeral=True
                    )
                    return
                
                # Check if user is the first player
                if interaction.user.id != self.first_player_id:
                    await interaction.response.send_message(
                        "❌ Only the first player can use this button.",
                        ephemeral=True
                    )
                    return
                
                # Check stream status
                voice_cog = interaction.client.get_cog("VoiceControl")
                if voice_cog:
                    stream_off = await voice_cog.force_stream_check(interaction.user, self.match_id)
                    if not stream_off:
                        return  # Stream check failed, message already sent
                
                # Mark first player as ready
                self.first_player_ready = True
                
                await interaction.response.send_message(
                    get_text("SUCCESS", "readiness_confirmed"),
                    ephemeral=True
                )
                
                # Check if both players are ready
                await self.check_both_ready(interaction, match)
                
        except Exception as e:
            logger.error(f"Error handling ready: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your readiness.",
                ephemeral=True
            )
    
    async def handle_draft_confirmation(self, interaction: discord.Interaction):
        """Handle second player draft confirmation"""
        try:
            # Get match
            session = await interaction.client.db_manager.get_session()
        async with session:
                match = await session.get(Match, self.match_id)
                if not match:
                    await interaction.response.send_message(
                        get_text("ERRORS", "match_not_found"),
                        ephemeral=True
                    )
                    return
                
                # Check if user is the second player
                if interaction.user.id == self.first_player_id:
                    await interaction.response.send_message(
                        "❌ Only the second player can use this button.",
                        ephemeral=True
                    )
                    return
                
                # Mark second player as confirmed
                self.second_player_confirmed = True
                
                await interaction.response.send_message(
                    "✅ Draft and stream confirmed.",
                    ephemeral=True
                )
                
                # Check if both players are ready
                await self.check_both_ready(interaction, match)
                
        except Exception as e:
            logger.error(f"Error handling draft confirmation: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your confirmation.",
                ephemeral=True
            )
    
    async def check_both_ready(self, interaction: discord.Interaction, match: Match):
        """Check if both players are ready to proceed"""
        try:
            if self.first_player_ready and self.second_player_confirmed:
                # Both players are ready, start the game
                await self.start_game(interaction, match)
            
        except Exception as e:
            logger.error(f"Error checking both ready: {e}")
    
    async def start_game(self, interaction: discord.Interaction, match: Match):
        """Start the game"""
        try:
            # Update match stage
            session = await interaction.client.db_manager.get_session()
        async with session:
                match.current_stage = MatchStage.GAME_IN_PROGRESS
                await session.commit()
            
            # Send game start message
            embed = discord.Embed(
                title="🎮 Game Started",
                description="The game is now in progress. Good luck!",
                color=discord.Color.green()
            )
            
            await interaction.channel.send(
                content=get_text("SUCCESS", "game_started"),
                embed=embed
            )
            
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            await interaction.channel.send(
                "❌ An error occurred while starting the game.",
                ephemeral=True
            )

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(DraftVerification(bot))