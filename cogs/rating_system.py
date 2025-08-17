import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from datetime import datetime

from models.rating import Rating
from models.season import Season
from models.player import Player
from locales import get_text
from config.config import Config

logger = logging.getLogger(__name__)

class RatingSystem(commands.Cog):
    """Cog for managing the Glicko-2 rating system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="rating", description="View your current rating")
    async def view_rating(self, interaction: discord.Interaction):
        """View current rating command"""
        try:
            # Get or create player
            player = await self.bot.db_manager.get_or_create_player(
                interaction.user.id,
                interaction.user.name,
                interaction.user.display_name
            )
            
            # Get current rating
            async with self.bot.db_manager.get_session() as session:
                current_rating = await self.get_current_rating(session, player.id)
                
                if not current_rating:
                    # Create initial rating
                    current_rating = await self.create_initial_rating(session, player.id)
            
            # Create rating display embed
            embed = discord.Embed(
                title=get_text("RATING_SYSTEM", "title"),
                description=get_text("RATING_SYSTEM", "description"),
                color=discord.Color.green()
            )
            
            embed.add_field(
                name=get_text("RATING_SYSTEM", "new_rating"),
                value=f"{current_rating.rating:.0f}",
                inline=True
            )
            embed.add_field(
                name="Games Played",
                value=current_rating.games_played,
                inline=True
            )
            embed.add_field(
                name="Win Rate",
                value=f"{current_rating.win_rate:.1%}",
                inline=True
            )
            embed.add_field(
                name="Wins",
                value=current_rating.wins,
                inline=True
            )
            embed.add_field(
                name="Losses",
                value=current_rating.losses,
                inline=True
            )
            embed.add_field(
                name="Draws",
                value=current_rating.draws,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error viewing rating: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching your rating.",
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard", description="View the rating leaderboard")
    async def view_leaderboard(self, interaction: discord.Interaction, season: Optional[str] = None):
        """View rating leaderboard command"""
        try:
            async with self.bot.db_manager.get_session() as session:
                # Get current season if none specified
                if not season:
                    current_season = await self.get_current_season(session)
                    if not current_season:
                        await interaction.response.send_message(
                            "❌ No active season found.",
                            ephemeral=True
                        )
                        return
                    season_id = current_season.id
                else:
                    # Try to find season by name
                    season_obj = await session.execute(
                        "SELECT id FROM seasons WHERE name = :name",
                        {"name": season}
                    )
                    season_result = season_obj.fetchone()
                    if not season_result:
                        await interaction.response.send_message(
                            f"❌ Season '{season}' not found.",
                            ephemeral=True
                        )
                        return
                    season_id = season_result[0]
                
                # Get top players
                top_players = await self.get_top_players(session, season_id, limit=10)
                
                if not top_players:
                    await interaction.response.send_message(
                        "❌ No ratings found for this season.",
                        ephemeral=True
                    )
                    return
                
                # Create leaderboard embed
                embed = discord.Embed(
                    title="🏆 Rating Leaderboard",
                    description=f"Top players for season {season or 'current'}",
                    color=discord.Color.gold()
                )
                
                for i, (player, rating) in enumerate(top_players, 1):
                    member = interaction.guild.get_member(player.discord_id)
                    player_name = member.display_name if member else player.username
                    
                    embed.add_field(
                        name=f"#{i} {player_name}",
                        value=f"Rating: {rating.rating:.0f} | Games: {rating.games_played} | Win Rate: {rating.win_rate:.1%}",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error viewing leaderboard: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching the leaderboard.",
                ephemeral=True
            )
    
    @app_commands.command(name="season", description="View current season information")
    async def view_season(self, interaction: discord.Interaction):
        """View current season command"""
        try:
            async with self.bot.db_manager.get_session() as session:
                current_season = await self.get_current_season(session)
                
                if not current_season:
                    await interaction.response.send_message(
                        "❌ No active season found.",
                        ephemeral=True
                    )
                    return
                
                # Create season info embed
                embed = discord.Embed(
                    title="📅 Current Season",
                    description=f"Season: {current_season.name}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Start Date",
                    value=current_season.start_date.strftime("%Y-%m-%d"),
                    inline=True
                )
                
                if current_season.end_date:
                    embed.add_field(
                        name="End Date",
                        value=current_season.end_date.strftime("%Y-%m-%d"),
                        inline=True
                    )
                    embed.add_field(
                        name="Duration",
                        value=f"{current_season.duration_days} days",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Status",
                        value="Active",
                        inline=True
                    )
                
                embed.add_field(
                    name="Initial Rating",
                    value=current_season.initial_rating,
                    inline=True
                )
                embed.add_field(
                    name="K-Factor (New)",
                    value=current_season.k_factor_new,
                    inline=True
                )
                embed.add_field(
                    name="K-Factor (Established)",
                    value=current_season.k_factor_established,
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error viewing season: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching season information.",
                ephemeral=True
            )
    
    async def get_current_rating(self, session, player_id: int) -> Optional[Rating]:
        """Get current rating for a player"""
        result = await session.execute(
            """
            SELECT r.* FROM ratings r
            JOIN seasons s ON r.season_id = s.id
            WHERE r.player_id = :player_id AND s.is_active = true
            ORDER BY r.created_at DESC
            LIMIT 1
            """,
            {"player_id": player_id}
        )
        return result.fetchone()
    
    async def create_initial_rating(self, session, player_id: int) -> Rating:
        """Create initial rating for a new player"""
        # Get current active season
        current_season = await self.get_current_season(session)
        if not current_season:
            # Create default season if none exists
            current_season = await self.create_default_season(session)
        
        # Create initial rating
        rating = Rating(
            player_id=player_id,
            season_id=current_season.id,
            rating=current_season.initial_rating,
            games_played=0,
            wins=0,
            losses=0,
            draws=0,
            rating_change=0.0
        )
        
        session.add(rating)
        await session.commit()
        await session.refresh(rating)
        
        return rating
    
    async def get_current_season(self, session) -> Optional[Season]:
        """Get current active season"""
        result = await session.execute(
            "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
        )
        return result.fetchone()
    
    async def create_default_season(self, session) -> Season:
        """Create a default season if none exists"""
        season = Season(
            name="Season 1",
            start_date=datetime.now(),
            is_active=True,
            initial_rating=Config.INITIAL_RATING,
            k_factor_new=Config.K_FACTOR_NEW,
            k_factor_established=Config.K_FACTOR_ESTABLISHED,
            established_threshold=Config.ESTABLISHED_THRESHOLD
        )
        
        session.add(season)
        await session.commit()
        await session.refresh(season)
        
        return season
    
    async def get_top_players(self, session, season_id: int, limit: int = 10):
        """Get top players by rating for a season"""
        result = await session.execute(
            """
            SELECT p.*, r.* FROM players p
            JOIN ratings r ON p.id = r.player_id
            WHERE r.season_id = :season_id
            ORDER BY r.rating DESC, r.games_played DESC
            LIMIT :limit
            """,
            {"season_id": season_id, "limit": limit}
        )
        
        # Process results to separate player and rating data
        players_with_ratings = []
        for row in result.fetchall():
            # This is a simplified approach - in practice you'd use proper ORM mapping
            player_data = {k: v for k, v in row._mapping.items() if not k.startswith('rating_')}
            rating_data = {k: v for k, v in row._mapping.items() if k.startswith('rating_')}
            
            player = Player(**player_data)
            rating = Rating(**rating_data)
            players_with_ratings.append((player, rating))
        
        return players_with_ratings
    
    async def calculate_rating_change(self, player_rating: float, opponent_rating: float, 
                                    result: float, k_factor: int) -> float:
        """
        Calculate rating change using Glicko-2 system
        
        Args:
            player_rating: Current player rating
            opponent_rating: Opponent rating
            result: 1 for win, 0.5 for draw, 0 for loss
            k_factor: K-factor for the player
            
        Returns:
            Rating change
        """
        # Expected score calculation
        expected_score = 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))
        
        # Rating change calculation
        rating_change = k_factor * (result - expected_score)
        
        return rating_change

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(RatingSystem(bot))