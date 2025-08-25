import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, List
import math
from database.database import DatabaseManager
from locales import LocaleManager
from models.rating import Rating
from models.season import Season
from models.penalty_settings import PenaltySettings
from datetime import datetime

class LeaderboardView(View):
    def __init__(self, current_page: int = 0, total_pages: int = 1):
        super().__init__(timeout=300)
        self.current_page = current_page
        self.total_pages = total_pages
        
        # Add navigation buttons
        if total_pages > 1:
            self.add_item(Button(
                label="◀️ Предыдущая",
                custom_id="prev_page",
                style=discord.ButtonStyle.secondary,
                disabled=current_page == 0
            ))
            self.add_item(Button(
                label="▶️ Следующая",
                custom_id="next_page",
                style=discord.ButtonStyle.secondary,
                disabled=current_page == total_pages - 1
            ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "prev_page" and self.current_page > 0:
            self.current_page -= 1
            await self.update_leaderboard(interaction)
        elif custom_id == "next_page" and self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_leaderboard(interaction)
            
        return True
    
    async def update_leaderboard(self, interaction: discord.Interaction):
        """Update the leaderboard display"""
        try:
            db_manager = DatabaseManager()
            session = await db_manager.get_session()
            async with session as session:
                # Get current season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    await interaction.response.send_message(
                        "❌ Нет активного сезона.",
                        ephemeral=True
                    )
                    return
                
                # Get ratings for current season
                ratings = await session.execute(
                    """
                    SELECT r.*, p.username, p.discord_id 
                    FROM ratings r 
                    JOIN players p ON r.player_id = p.id 
                    WHERE r.season_id = :season_id 
                    ORDER BY r.rating DESC 
                    LIMIT 10 OFFSET :offset
                    """,
                    {
                        "season_id": current_season.id,
                        "offset": self.current_page * 10
                    }
                )
                ratings = ratings.fetchall()
                
                if not ratings:
                    await interaction.response.send_message(
                        "❌ Нет данных для отображения.",
                        ephemeral=True
                    )
                    return
                
                # Create leaderboard embed
                embed = discord.Embed(
                    title=f"🏆 Лидерборд - {current_season.name}",
                    description=f"Страница {self.current_page + 1} из {self.total_pages}",
                    color=discord.Color.gold()
                )
                
                for i, rating in enumerate(ratings):
                    position = self.current_page * 10 + i + 1
                    medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else f"{position}."
                    
                    embed.add_field(
                        name=f"{medal} {rating.username}",
                        value=f"Рейтинг: {rating.rating:.0f} | Игр: {rating.games_played} | Победы: {rating.wins}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Обновлено: {current_season.updated_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Update the message
                await interaction.response.edit_message(embed=embed, view=self)
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при обновлении лидерборда: {str(e)}",
                ephemeral=True
            )

class RatingSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.locale = LocaleManager()
        
    @app_commands.command(name="rating", description="Посмотреть свой рейтинг")
    async def view_rating(self, interaction: discord.Interaction):
        """Посмотреть свой рейтинг"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get current season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    await interaction.followup.send(
                        "❌ Нет активного сезона.",
                        ephemeral=True
                    )
                    return
                
                # Get or create player
                player = await session.execute(
                    "SELECT * FROM players WHERE discord_id = :discord_id",
                    {"discord_id": interaction.user.id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    # Create new player with default rating
                    player = await self.create_new_player(session, interaction.user.id, interaction.user.display_name)
                
                # Get rating for current season
                rating = await session.execute(
                    "SELECT * FROM ratings WHERE player_id = :player_id AND season_id = :season_id",
                    {"player_id": player.id, "season_id": current_season.id}
                )
                rating = rating.scalar_one_or_none()
                
                if not rating:
                    # Create default rating for new player
                    rating = await self.create_default_rating(session, player.id, current_season.id)
                
                # Create rating embed
                embed = discord.Embed(
                    title="📊 Ваш рейтинг",
                    description=f"Сезон: {current_season.name}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Рейтинг",
                    value=f"{rating.rating:.0f}",
                    inline=True
                )
                
                embed.add_field(
                    name="RD (надежность)",
                    value=f"{rating.rd:.0f}",
                    inline=True
                )
                
                embed.add_field(
                    name="Волатильность",
                    value=f"{rating.volatility:.3f}",
                    inline=True
                )
                
                embed.add_field(
                    name="Статистика",
                    value=f"Игр: {rating.games_played} | Победы: {rating.wins} | Поражения: {rating.losses} | Ничьи: {rating.draws}",
                    inline=False
                )
                
                if rating.rating_change != 0:
                    change_text = f"+{rating.rating_change:.0f}" if rating.rating_change > 0 else f"{rating.rating_change:.0f}"
                    embed.add_field(
                        name="Изменение рейтинга",
                        value=change_text,
                        inline=True
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении рейтинга: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard", description="Таблица лидеров")
    async def view_leaderboard(self, interaction: discord.Interaction):
        """Показать таблицу лидеров"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get current season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    await interaction.followup.send(
                        "❌ Нет активного сезона.",
                        ephemeral=True
                    )
                    return
                
                # Get total count for pagination
                total_count = await session.execute(
                    "SELECT COUNT(*) FROM ratings WHERE season_id = :season_id",
                    {"season_id": current_season.id}
                )
                total_count = total_count.scalar()
                
                if total_count == 0:
                    await interaction.followup.send(
                        "❌ Нет данных для лидерборда.",
                        ephemeral=True
                    )
                    return
                
                # Calculate total pages
                total_pages = math.ceil(total_count / 10)
                
                # Get first page of ratings
                ratings = await session.execute(
                    """
                    SELECT r.*, p.username, p.discord_id 
                    FROM ratings r 
                    JOIN players p ON r.player_id = p.id 
                    WHERE r.season_id = :season_id 
                    ORDER BY r.rating DESC 
                    LIMIT 10
                    """,
                    {"season_id": current_season.id}
                )
                ratings = ratings.fetchall()
                
                # Create leaderboard embed
                embed = discord.Embed(
                    title=f"🏆 Лидерборд - {current_season.name}",
                    description=f"Страница 1 из {total_pages}",
                    color=discord.Color.gold()
                )
                
                for i, rating in enumerate(ratings):
                    position = i + 1
                    medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else f"{position}."
                    
                    embed.add_field(
                        name=f"{medal} {rating.username}",
                        value=f"Рейтинг: {rating.rating:.0f} | Игр: {rating.games_played} | Победы: {rating.wins}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Обновлено: {current_season.updated_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Create view with navigation
                view = LeaderboardView(0, total_pages)
                
                await interaction.followup.send(embed=embed, view=view)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении лидерборда: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="stats", description="Статистика игрока")
    async def view_stats(self, interaction: discord.Interaction, player: Optional[discord.Member] = None):
        """Посмотреть статистику игрока"""
        if not player:
            player = interaction.user
            
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get player
                player_data = await session.execute(
                    "SELECT * FROM players WHERE discord_id = :discord_id",
                    {"discord_id": player.id}
                )
                player_data = player_data.scalar_one_or_none()
                
                if not player_data:
                    await interaction.followup.send(
                        f"❌ Игрок {player.display_name} не найден в базе данных.",
                        ephemeral=True
                    )
                    return
                
                # Get current season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
                )
                current_season = current_season.scalar_one_or_none()
                
                # Get rating for current season
                rating = None
                if current_season:
                    rating = await session.execute(
                        "SELECT * FROM ratings WHERE player_id = :player_id AND season_id = :season_id",
                        {"player_id": player_data.id, "season_id": current_season.id}
                    )
                    rating = rating.scalar_one_or_none()
                
                # Get overall statistics
                overall_stats = await session.execute(
                    """
                    SELECT 
                        COUNT(*) as total_matches,
                        SUM(CASE WHEN m.player1_id = :player_id THEN 1 ELSE 0 END) as as_player1,
                        SUM(CASE WHEN m.player2_id = :player_id THEN 1 ELSE 0 END) as as_player2
                    FROM matches m 
                    WHERE m.guild_id = :guild_id 
                    AND (m.player1_id = :player_id OR m.player2_id = :player_id)
                    AND m.status = 'complete'
                    """,
                    {"player_id": player_data.id, "guild_id": interaction.guild_id}
                )
                overall_stats = overall_stats.scalar_one_or_none()
                
                # Create stats embed
                embed = discord.Embed(
                    title=f"📊 Статистика {player.display_name}",
                    color=discord.Color.green()
                )
                
                if rating:
                    embed.add_field(
                        name="Текущий сезон",
                        value=f"Рейтинг: {rating.rating:.0f} | Игр: {rating.games_played}",
                        inline=False
                    )
                    
                    win_rate = (rating.wins / rating.games_played * 100) if rating.games_played > 0 else 0
                    embed.add_field(
                        name="Результаты",
                        value=f"Победы: {rating.wins} | Поражения: {rating.losses} | Ничьи: {rating.draws} | Винрейт: {win_rate:.1f}%",
                        inline=False
                    )
                
                if overall_stats:
                    embed.add_field(
                        name="Общая статистика",
                        value=f"Всего матчей: {overall_stats.total_matches}",
                        inline=True
                    )
                
                embed.add_field(
                    name="Дата регистрации",
                    value=player_data.created_at.strftime("%Y-%m-%d"),
                    inline=True
                )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении статистики: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="season", description="Информация о текущем сезоне")
    async def season_info(self, interaction: discord.Interaction):
        """Показать информацию о текущем сезоне"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session as session:
                # Get current active season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true ORDER BY start_date DESC LIMIT 1"
                )
                current_season = current_season.scalar_one_or_none()
                
                if not current_season:
                    await interaction.followup.send(
                        "❌ Нет активного сезона.",
                        ephemeral=True
                    )
                    return
                
                # Get season statistics
                total_matches = await session.execute(
                    "SELECT COUNT(*) FROM matches WHERE season_id = :season_id",
                    {"season_id": current_season.id}
                )
                total_matches = total_matches.scalar()
                
                completed_matches = await session.execute(
                    "SELECT COUNT(*) FROM matches WHERE season_id = :season_id AND status = 'complete'",
                    {"season_id": current_season.id}
                )
                completed_matches = completed_matches.scalar()
                
                active_matches = await session.execute(
                    "SELECT COUNT(*) FROM matches WHERE season_id = :season_id AND status NOT IN ('complete', 'annulled')",
                    {"season_id": current_season.id}
                )
                active_matches = active_matches.scalar()
                
                # Calculate days until end
                days_until_end = (current_season.end_date - datetime.utcnow()).days
                
                # Create season info embed
                embed = discord.Embed(
                    title=f"📅 Сезон: {current_season.name}",
                    description="Информация о текущем сезоне",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📊 Статистика",
                    value=f"Всего матчей: {total_matches}\nЗавершено: {completed_matches}\nАктивных: {active_matches}",
                    inline=True
                )
                
                embed.add_field(
                    name="⏰ Время",
                    value=f"Начало: {current_season.start_date.strftime('%d.%m.%Y')}\nКонец: {current_season.end_date.strftime('%d.%m.%Y')}",
                    inline=True
                )
                
                embed.add_field(
                    name="📈 Статус",
                    value=current_season.get_status_description(),
                    inline=True
                )
                
                # Add season end information
                if current_season.is_ending_soon or current_season.is_ending:
                    embed.color = discord.Color.orange()
                    
                    if days_until_end > 0:
                        embed.add_field(
                            name="⚠️ Внимание!",
                            value=f"Сезон завершается через **{days_until_end}** дней!",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🚨 Срочно!",
                            value="Сезон завершается сегодня!",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="📋 Действия",
                        value="• Завершите все активные матчи\n• Новые матчи заблокированы\n• Рейтинг будет зафиксирован",
                        inline=False
                    )
                
                # Add blocking information
                if current_season.should_block_new_matches:
                    embed.color = discord.Color.red()
                    embed.add_field(
                        name="🚫 Ограничения",
                        value=f"**Причина**: {current_season.get_blocking_reason()}",
                        inline=False
                    )
                
                embed.set_footer(text=f"ID сезона: {current_season.id}")
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении информации о сезоне: {str(e)}",
                ephemeral=True
            )
    
    async def create_new_player(self, session, discord_id: int, username: str):
        """Create a new player"""
        from models.player import Player
        
        player = Player(
            discord_id=discord_id,
            username=username
        )
        session.add(player)
        await session.commit()
        await session.refresh(player)
        return player
    
    async def create_default_rating(self, session, player_id: int, season_id: int):
        """Create default rating for a player"""
        from models.season import Season
        
        # Get season for default values
        season = await session.get(Season, season_id)
        
        rating = Rating(
            player_id=player_id,
            season_id=season_id,
            rating=season.glicko2_rd_initial if season else 1500.0,
            rd=season.glicko2_rd_initial if season else 350.0,
            volatility=season.glicko2_volatility_initial if season else 0.06
        )
        
        session.add(rating)
        await session.commit()
        await session.refresh(rating)
        return rating

async def setup(bot: commands.Bot):
    await bot.add_cog(RatingSystem(bot))