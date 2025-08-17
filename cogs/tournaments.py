import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional, List
from database.database import DatabaseManager
from models.tournament import Tournament, TournamentStatus, TournamentFormat, TournamentParticipant
from services.tournament_service import TournamentService
import asyncio

class TournamentCreationModal(Modal, title="Создание турнира"):
    """Modal for creating a new tournament"""
    
    name = TextInput(
        label="Название турнира",
        placeholder="Введите название турнира",
        max_length=200,
        required=True
    )
    
    description = TextInput(
        label="Описание",
        placeholder="Описание турнира и правила",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    rules = TextInput(
        label="Правила",
        placeholder="Специальные правила турнира",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    prize_pool = TextInput(
        label="Призовой фонд",
        placeholder="Описание призов",
        max_length=500,
        required=False
    )
    
    def __init__(self, tournament_service: TournamentService):
        super().__init__()
        self.tournament_service = tournament_service

class TournamentView(View):
    """View for tournament interactions"""
    
    def __init__(self, tournament_id: int, tournament_service: TournamentService):
        super().__init__(timeout=300)
        self.tournament_id = tournament_id
        self.tournament_service = tournament_service
        
        # Add action buttons
        self.add_item(Button(
            label="📝 Зарегистрироваться",
            custom_id="register_tournament",
            style=discord.ButtonStyle.primary
        ))
        
        self.add_item(Button(
            label="📊 Информация",
            custom_id="tournament_info",
            style=discord.ButtonStyle.secondary
        ))
        
        self.add_item(Button(
            label="👥 Участники",
            custom_id="tournament_participants",
            style=discord.ButtonStyle.secondary
        ))

class Tournaments(commands.Cog):
    """Cog for managing tournaments"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.tournament_service = TournamentService(bot)
        
    @app_commands.command(name="create_tournament", description="Создать новый турнир")
    @app_commands.describe(
        name="Название турнира",
        format="Формат турнира",
        match_format="Формат матчей",
        min_participants="Минимальное количество участников",
        max_participants="Максимальное количество участников (необязательно)",
        registration_days="Количество дней на регистрацию"
    )
    async def create_tournament(
        self,
        interaction: discord.Interaction,
        name: str,
        format: str,
        match_format: str,
        min_participants: int,
        max_participants: Optional[int],
        registration_days: int
    ):
        """Create a new tournament"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для создания турниров.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate format
            try:
                tournament_format = TournamentFormat(format.lower())
            except ValueError:
                await interaction.followup.send(
                    f"❌ Неверный формат турнира. Доступные форматы: {', '.join([f.value for f in TournamentFormat])}",
                    ephemeral=True
                )
                return
            
            # Validate match format
            valid_match_formats = ["bo1", "bo3", "bo5"]
            if match_format.lower() not in valid_match_formats:
                await interaction.followup.send(
                    f"❌ Неверный формат матчей. Доступные форматы: {', '.join(valid_match_formats)}",
                    ephemeral=True
                )
                return
            
            # Validate participants
            if min_participants < 2:
                await interaction.followup.send(
                    "❌ Минимальное количество участников должно быть не менее 2.",
                    ephemeral=True
                )
                return
            
            if max_participants and max_participants < min_participants:
                await interaction.followup.send(
                    "❌ Максимальное количество участников должно быть больше минимального.",
                    ephemeral=True
                )
                return
            
            # Create tournament
            tournament = await self.tournament_service.create_tournament(
                name=name,
                description="",
                guild_id=interaction.guild_id,
                format=tournament_format,
                match_format=match_format.lower(),
                min_participants=min_participants,
                max_participants=max_participants,
                registration_days=registration_days
            )
            
            # Create embed
            embed = self.create_tournament_embed(tournament)
            
            # Create view
            view = TournamentView(tournament.id, self.tournament_service)
            
            await interaction.followup.send(
                f"🏅 **Турнир создан!**",
                embed=embed,
                view=view
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при создании турнира: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="tournaments", description="Список турниров")
    @app_commands.describe(status="Статус турнира (необязательно)")
    async def list_tournaments(self, interaction: discord.Interaction, status: Optional[str] = None):
        """List tournaments in the guild"""
        await interaction.response.defer()
        
        try:
            # Parse status if provided
            tournament_status = None
            if status:
                try:
                    tournament_status = TournamentStatus(status.lower())
                except ValueError:
                    await interaction.followup.send(
                        f"❌ Неверный статус турнира. Доступные статусы: {', '.join([s.value for s in TournamentStatus])}",
                        ephemeral=True
                    )
                    return
            
            # Get tournaments
            tournaments = await self.tournament_service.get_guild_tournaments(
                interaction.guild_id, 
                tournament_status
            )
            
            if not tournaments:
                await interaction.followup.send(
                    "📋 В этом сервере пока нет турниров.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = self.create_tournaments_list_embed(tournaments)
            
            await interaction.followup.send(
                f"🏅 **Турниры сервера**",
                embed=embed
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке турниров: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="register_tournament", description="Зарегистрироваться на турнир")
    @app_commands.describe(tournament_id="ID турнира")
    async def register_tournament(self, interaction: discord.Interaction, tournament_id: int):
        """Register for a tournament"""
        await interaction.response.defer()
        
        try:
            # Get player ID
            session = await self.db.get_session()
        async with session as session:
                player = await session.execute(
                    "SELECT id FROM players WHERE discord_id = :discord_id",
                    {"discord_id": interaction.user.id}
                )
                player = player.scalar_one_or_none()
                
                if not player:
                    await interaction.followup.send(
                        "❌ Вы не найдены в системе. Сначала сыграйте хотя бы один матч.",
                        ephemeral=True
                    )
                    return
                
                player_id = player.id
            
            # Register for tournament
            success = await self.tournament_service.register_player(tournament_id, player_id)
            
            if success:
                await interaction.followup.send(
                    f"✅ Вы успешно зарегистрировались на турнир!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Не удалось зарегистрироваться на турнир. Возможно, турнир не существует, закрыт для регистрации или вы уже зарегистрированы.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при регистрации: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="tournament_info", description="Информация о турнире")
    @app_commands.describe(tournament_id="ID турнира")
    async def tournament_info(self, interaction: discord.Interaction, tournament_id: int):
        """Get detailed tournament information"""
        await interaction.response.defer()
        
        try:
            # Get tournament info
            tournament_info = await self.tournament_service.get_tournament_info(tournament_id)
            
            if not tournament_info:
                await interaction.followup.send(
                    "❌ Турнир не найден.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = self.create_detailed_tournament_embed(tournament_info)
            
            await interaction.followup.send(
                f"🏅 **Информация о турнире**",
                embed=embed
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке информации о турнире: {str(e)}",
                ephemeral=True
            )
    
    def create_tournament_embed(self, tournament) -> discord.Embed:
        """Create embed for tournament display"""
        embed = discord.Embed(
            title=f"🏅 {tournament.name}",
            description="Новый турнир создан!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Статус",
            value=tournament.status.value.replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="🏆 Формат",
            value=tournament.format.value.replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="🎮 Матчи",
            value=tournament.match_format.upper(),
            inline=True
        )
        
        embed.add_field(
            name="👥 Участники",
            value=f"Минимум: {tournament.min_participants}\nМаксимум: {tournament.max_participants or 'Не ограничено'}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Регистрация",
            value=f"До: {tournament.registration_end.strftime('%d.%m.%Y %H:%M')}",
            inline=True
        )
        
        if tournament.rules:
            embed.add_field(
                name="📋 Правила",
                value=tournament.rules[:1024],
                inline=False
            )
        
        if tournament.prize_pool:
            embed.add_field(
                name="🏆 Призы",
                value=tournament.prize_pool[:1024],
                inline=False
            )
        
        embed.set_footer(text=f"ID турнира: {tournament.id}")
        
        return embed
    
    def create_tournaments_list_embed(self, tournaments: List[dict]) -> discord.Embed:
        """Create embed for tournaments list"""
        embed = discord.Embed(
            title="🏅 Турниры сервера",
            description=f"Найдено турниров: {len(tournaments)}",
            color=discord.Color.blue()
        )
        
        for tournament in tournaments[:10]:  # Show first 10
            status_emoji = {
                "registration": "📝",
                "active": "🏆",
                "completed": "✅",
                "cancelled": "❌"
            }.get(tournament["status"], "❓")
            
            embed.add_field(
                name=f"{status_emoji} {tournament['name']}",
                value=f"**Формат**: {tournament['format'].replace('_', ' ').title()}\n"
                      f"**Участники**: {tournament['participant_count']}/{tournament.get('max_participants', '∞')}\n"
                      f"**Статус**: {tournament['status'].replace('_', ' ').title()}\n"
                      f"**ID**: {tournament['id']}",
                inline=True
            )
        
        if len(tournaments) > 10:
            embed.set_footer(text=f"Показано 10 из {len(tournaments)} турниров")
        
        return embed
    
    def create_detailed_tournament_embed(self, tournament_info: dict) -> discord.Embed:
        """Create detailed embed for tournament information"""
        embed = discord.Embed(
            title=f"🏅 {tournament_info['name']}",
            description=tournament_info.get('description', 'Описание отсутствует'),
            color=discord.Color.gold()
        )
        
        # Status and format
        embed.add_field(
            name="📊 Статус",
            value=tournament_info['status'].replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="🏆 Формат",
            value=tournament_info['format'].replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="🎮 Матчи",
            value=tournament_info.get('match_format', 'N/A').upper(),
            inline=True
        )
        
        # Participants and matches
        embed.add_field(
            name="👥 Участники",
            value=f"Зарегистрировано: {tournament_info['participant_count']}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Матчи",
            value=f"Всего: {tournament_info['match_count']}",
            inline=True
        )
        
        # Timing
        if tournament_info.get('registration_start'):
            embed.add_field(
                name="⏰ Регистрация",
                value=f"Начало: {tournament_info['registration_start'].strftime('%d.%m.%Y %H:%M')}\n"
                      f"Конец: {tournament_info['registration_end'].strftime('%d.%m.%Y %H:%M')}",
                inline=False
            )
        
        if tournament_info.get('tournament_start'):
            embed.add_field(
                name="🏁 Турнир",
                value=f"Начало: {tournament_info['tournament_start'].strftime('%d.%m.%Y %H:%M')}",
                inline=True
            )
        
        if tournament_info.get('tournament_end'):
            embed.add_field(
                name="🏁 Завершение",
                value=f"Конец: {tournament_info['tournament_end'].strftime('%d.%m.%Y %H:%M')}",
                inline=True
            )
        
        # Rules and prizes
        if tournament_info.get('rules'):
            embed.add_field(
                name="📋 Правила",
                value=tournament_info['rules'][:1024],
                inline=False
            )
        
        if tournament_info.get('prize_pool'):
            embed.add_field(
                name="🏆 Призовой фонд",
                value=tournament_info['prize_pool'][:1024],
                inline=False
            )
        
        embed.set_footer(text=f"ID турнира: {tournament_info['id']}")
        
        return embed

async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(Tournaments(bot))