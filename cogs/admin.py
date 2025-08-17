import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import logging
from typing import Optional
from datetime import datetime, timedelta

from models.penalty_settings import PenaltySettings
from models.season import Season
from locales import get_text
from config.config import Config

logger = logging.getLogger(__name__)

class AdminSettingsModal(Modal, title="Admin Settings"):
    """Modal for updating admin settings"""
    
    def __init__(self, setting_type: str):
        super().__init__()
        self.setting_type = setting_type
        
        if setting_type == "penalty":
            self.penalty_input = TextInput(
                label="Restart Penalty (seconds)",
                placeholder="30",
                required=True,
                max_length=5
            )
            self.max_restarts_input = TextInput(
                label="Max Restarts Before Penalty",
                placeholder="0",
                required=True,
                max_length=3
            )
            
            self.add_item(self.penalty_input)
            self.add_item(self.max_restarts_input)
            
        elif setting_type == "season":
            self.name_input = TextInput(
                label="Season Name",
                placeholder="Season 2",
                required=True,
                max_length=50
            )
            self.duration_input = TextInput(
                label="Duration (days)",
                placeholder="90",
                required=True,
                max_length=5
            )
            
            self.add_item(self.name_input)
            self.add_item(self.duration_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            if self.setting_type == "penalty":
                penalty = int(self.penalty_input.value)
                max_restarts = int(self.max_restarts_input.value)
                
                if penalty < 0 or max_restarts < 0:
                    await interaction.response.send_message(
                        "❌ Values must be non-negative.",
                        ephemeral=True
                    )
                    return
                
                await self.update_penalty_settings(interaction, penalty, max_restarts)
                
            elif self.setting_type == "season":
                name = self.name_input.value.strip()
                duration = int(self.duration_input.value)
                
                if duration <= 0:
                    await interaction.response.send_message(
                        "❌ Duration must be positive.",
                        ephemeral=True
                    )
                    return
                
                await self.create_new_season(interaction, name, duration)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid input. Please enter valid numbers.",
                ephemeral=True
            )
    
    async def update_penalty_settings(self, interaction: discord.Interaction, penalty: int, max_restarts: int):
        """Update penalty settings for the guild"""
        try:
            bot = interaction.client
            
            async with bot.db_manager.get_session() as session:
                # Get or create penalty settings
                penalty_settings = await session.get(PenaltySettings, interaction.guild.id)
                
                if not penalty_settings:
                    penalty_settings = PenaltySettings(
                        discord_guild_id=interaction.guild.id,
                        restart_penalty_seconds=penalty,
                        max_restarts_before_penalty=max_restarts,
                        description="Updated by admin"
                    )
                    session.add(penalty_settings)
                else:
                    penalty_settings.restart_penalty_seconds = penalty
                    penalty_settings.max_restarts_before_penalty = max_restarts
                    penalty_settings.updated_at = datetime.now()
                
                await session.commit()
            
            embed = discord.Embed(
                title="⚙️ Penalty Settings Updated",
                description="Restart penalty settings have been updated successfully.",
                color=discord.Color.green()
            )
            embed.add_field(name="Restart Penalty", value=f"{penalty} seconds", inline=True)
            embed.add_field(name="Max Restarts", value=max_restarts, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error updating penalty settings: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while updating penalty settings.",
                ephemeral=True
            )
    
    async def create_new_season(self, interaction: discord.Interaction, name: str, duration: int):
        """Create a new season"""
        try:
            bot = interaction.client
            
            async with bot.db_manager.get_session() as session:
                # End current season if exists
                current_season = await self.get_current_season(session)
                if current_season:
                    current_season.end_season()
                    await session.commit()
                
                # Create new season
                new_season = Season(
                    name=name,
                    start_date=datetime.now(),
                    is_active=True,
                    initial_rating=Config.INITIAL_RATING,
                    k_factor_new=Config.K_FACTOR_NEW,
                    k_factor_established=Config.K_FACTOR_ESTABLISHED,
                    established_threshold=Config.ESTABLISHED_THRESHOLD
                )
                
                session.add(new_season)
                await session.commit()
                await session.refresh(new_season)
            
            embed = discord.Embed(
                title="📅 New Season Created",
                description=f"Season '{name}' has been created successfully.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Start Date", value=new_season.start_date.strftime("%Y-%m-%d"), inline=True)
            embed.add_field(name="Duration", value=f"{duration} days", inline=True)
            embed.add_field(name="Status", value="Active", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating new season: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while creating the new season.",
                ephemeral=True
            )
    
    async def get_current_season(self, session) -> Optional[Season]:
        """Get current active season"""
        result = await session.execute(
            "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
        )
        return result.fetchone()

class Admin(commands.Cog):
    """Cog for administrative functions"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="admin", description="Access admin settings")
    @app_commands.default_permissions(administrator=True)
    async def admin_settings(self, interaction: discord.Interaction):
        """Admin settings command"""
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.",
                ephemeral=True
            )
            return
        
        # Create admin settings view
        view = AdminSettingsView()
        await interaction.response.send_message(
            "⚙️ Admin Settings - Choose an option:",
            view=view,
            ephemeral=True
        )
    
    @app_commands.command(name="settings", description="View current guild settings")
    async def view_settings(self, interaction: discord.Interaction):
        """View current settings command"""
        try:
            async with self.bot.db_manager.get_session() as session:
                # Get penalty settings
                penalty_settings = await session.get(PenaltySettings, interaction.guild.id)
                
                # Get current season
                current_season = await self.get_current_season(session)
                
                # Create settings display embed
                embed = discord.Embed(
                    title="⚙️ Guild Settings",
                    description=f"Current settings for {interaction.guild.name}",
                    color=discord.Color.blue()
                )
                
                if penalty_settings:
                    embed.add_field(
                        name="Restart Penalty",
                        value=f"{penalty_settings.restart_penalty_seconds} seconds",
                        inline=True
                    )
                    embed.add_field(
                        name="Max Restarts Before Penalty",
                        value=penalty_settings.max_restarts_before_penalty,
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Restart Penalty",
                        value=f"{Config.DEFAULT_RESTART_PENALTY} seconds (default)",
                        inline=True
                    )
                    embed.add_field(
                        name="Max Restarts Before Penalty",
                        value="0 (default)",
                        inline=True
                    )
                
                if current_season:
                    embed.add_field(
                        name="Current Season",
                        value=current_season.name,
                        inline=True
                    )
                    embed.add_field(
                        name="Season Start",
                        value=current_season.start_date.strftime("%Y-%m-%d"),
                        inline=True
                    )
                    embed.add_field(
                        name="Season Status",
                        value="Active" if current_season.is_active else "Ended",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Current Season",
                        value="No active season",
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error viewing settings: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching settings.",
                ephemeral=True
            )
    
    @app_commands.command(name="stats", description="View bot statistics")
    async def view_stats(self, interaction: discord.Interaction):
        """View bot statistics command"""
        try:
            async with self.bot.db_manager.get_session() as session:
                # Get basic statistics
                stats = await self.get_guild_stats(session, interaction.guild.id)
                
                embed = discord.Embed(
                    title="📊 Bot Statistics",
                    description=f"Statistics for {interaction.guild.name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="Total Players", value=stats['total_players'], inline=True)
                embed.add_field(name="Total Matches", value=stats['total_matches'], inline=True)
                embed.add_field(name="Active Matches", value=stats['active_matches'], inline=True)
                embed.add_field(name="Completed Matches", value=stats['completed_matches'], inline=True)
                embed.add_field(name="Current Season", value=stats['current_season'], inline=True)
                embed.add_field(name="Total Games", value=stats['total_games'], inline=True)
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error viewing stats: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching statistics.",
                ephemeral=True
            )
    
    async def get_guild_stats(self, session, guild_id: int) -> dict:
        """Get statistics for a guild"""
        try:
            # Get player count
            player_result = await session.execute(
                "SELECT COUNT(*) FROM players WHERE discord_id IN (SELECT DISTINCT player1_id FROM matches WHERE discord_guild_id = :guild_id UNION SELECT DISTINCT player2_id FROM matches WHERE discord_guild_id = :guild_id)",
                {"guild_id": guild_id}
            )
            total_players = player_result.fetchone()[0]
            
            # Get match counts
            match_result = await session.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed FROM matches WHERE discord_guild_id = :guild_id",
                {"guild_id": guild_id}
            )
            match_row = match_result.fetchone()
            total_matches = match_row[0] if match_row[0] else 0
            active_matches = match_row[1] if match_row[1] else 0
            completed_matches = match_row[2] if match_row[2] else 0
            
            # Get current season
            season_result = await session.execute(
                "SELECT name FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
            )
            season_row = season_result.fetchone()
            current_season = season_row[0] if season_row else "None"
            
            # Get total games
            game_result = await session.execute(
                "SELECT COUNT(*) FROM game_results gr JOIN matches m ON gr.match_id = m.id WHERE m.discord_guild_id = :guild_id",
                {"guild_id": guild_id}
            )
            total_games = game_result.fetchone()[0] if game_result.fetchone() else 0
            
            return {
                'total_players': total_players,
                'total_matches': total_matches,
                'active_matches': active_matches,
                'completed_matches': completed_matches,
                'current_season': current_season,
                'total_games': total_games
            }
            
        except Exception as e:
            logger.error(f"Error getting guild stats: {e}")
            return {
                'total_players': 0,
                'total_matches': 0,
                'active_matches': 0,
                'completed_matches': 0,
                'current_season': "Error",
                'total_games': 0
            }
    
    async def get_current_season(self, session) -> Optional[Season]:
        """Get current active season"""
        result = await session.execute(
            "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
        )
        return result.fetchone()

class AdminSettingsView(View):
    """View for admin settings options"""
    
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes timeout
    
    @discord.ui.button(label="Penalty Settings", style=discord.ButtonStyle.primary, custom_id="penalty_settings")
    async def penalty_settings(self, interaction: discord.Interaction, button: Button):
        """Open penalty settings modal"""
        modal = AdminSettingsModal("penalty")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="New Season", style=discord.ButtonStyle.success, custom_id="new_season")
    async def new_season(self, interaction: discord.Interaction, button: Button):
        """Open new season modal"""
        modal = AdminSettingsModal("season")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="View Settings", style=discord.ButtonStyle.secondary, custom_id="view_settings")
    async def view_settings(self, interaction: discord.Interaction, button: Button):
        """View current settings"""
        # This would call the view_settings command
        await interaction.response.send_message(
            "Use `/settings` to view current settings.",
            ephemeral=True
        )

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Admin(bot))