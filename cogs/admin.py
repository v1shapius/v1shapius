import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from typing import Optional
from database.database import DatabaseManager
from locales import LocaleManager
from models.penalty_settings import PenaltySettings

class GuildSettingsModal(Modal, title="Настройки сервера"):
    def __init__(self, current_settings: Optional[PenaltySettings] = None):
        super().__init__()
        self.current_settings = current_settings
        
        self.restart_penalty = TextInput(
            label="Штраф за рестарт (секунды)",
            placeholder="30",
            default=str(current_settings.restart_penalty) if current_settings else "30",
            required=True,
            min_length=1,
            max_length=3
        )
        
        self.add_item(self.restart_penalty)

class ChannelSelectionView(View):
    def __init__(self, guild: discord.Guild, settings_type: str):
        super().__init__(timeout=300)
        self.guild = guild
        self.settings_type = settings_type
        self.selected_channel = None
        
        # Add channel selection buttons
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.CategoryChannel)):
                label = f"#{channel.name}" if isinstance(channel, discord.TextChannel) else f"📁 {channel.name}"
                self.add_item(Button(
                    label=label[:100],  # Discord limit
                    custom_id=f"select_{channel.id}",
                    style=discord.ButtonStyle.secondary
                ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.data.get("custom_id", "").startswith("select_"):
            return False
            
        channel_id = int(interaction.data["custom_id"].replace("select_", ""))
        channel = self.guild.get_channel(channel_id)
        
        if channel:
            self.selected_channel = channel
            await interaction.response.send_message(
                f"Выбран канал: {channel.mention}",
                ephemeral=True
            )
            self.stop()
        
        return True

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.locale = LocaleManager()
        
    @app_commands.command(name="settings", description="Настройки сервера")
    @app_commands.describe(
        penalty="Штраф за рестарт в секундах",
        match_channel="Канал для создания матчей",
        leaderboard_channel="Канал для лидерборда",
        audit_channel="Канал для аудита",
        voice_category="Категория для голосовых каналов"
    )
    async def settings(
        self, 
        interaction: discord.Interaction,
        penalty: Optional[int] = None,
        match_channel: Optional[discord.TextChannel] = None,
        leaderboard_channel: Optional[discord.TextChannel] = None,
        audit_channel: Optional[discord.TextChannel] = None,
        voice_category: Optional[discord.CategoryChannel] = None
    ):
        """Настройки сервера"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "У вас нет прав администратора для изменения настроек.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        try:
            # Get or create guild settings
            async with self.db.get_session() as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    settings = PenaltySettings(
                        guild_id=interaction.guild_id,
                        restart_penalty=30
                    )
                    session.add(settings)
                
                # Update settings if provided
                if penalty is not None:
                    settings.restart_penalty = penalty
                if match_channel is not None:
                    settings.match_channel_id = match_channel.id
                if leaderboard_channel is not None:
                    settings.leaderboard_channel_id = leaderboard_channel.id
                if audit_channel is not None:
                    settings.audit_channel_id = audit_channel.id
                if voice_category is not None:
                    settings.voice_category_id = voice_category.id
                
                await session.commit()
                
                # Create settings embed
                embed = discord.Embed(
                    title="⚙️ Настройки сервера",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Штраф за рестарт",
                    value=f"{settings.restart_penalty} секунд",
                    inline=True
                )
                
                if settings.match_channel_id:
                    channel = interaction.guild.get_channel(settings.match_channel_id)
                    embed.add_field(
                        name="Канал для матчей",
                        value=channel.mention if channel else "Не найден",
                        inline=True
                    )
                
                if settings.leaderboard_channel_id:
                    channel = interaction.guild.get_channel(settings.leaderboard_channel_id)
                    embed.add_field(
                        name="Канал лидерборда",
                        value=channel.mention if channel else "Не найден",
                        inline=True
                    )
                
                if settings.audit_channel_id:
                    channel = interaction.guild.get_channel(settings.audit_channel_id)
                    embed.add_field(
                        name="Канал аудита",
                        value=channel.mention if channel else "Не найден",
                        inline=True
                    )
                
                if settings.voice_category_id:
                    category = interaction.guild.get_channel(settings.voice_category_id)
                    embed.add_field(
                        name="Категория голосовых каналов",
                        value=f"📁 {category.name}" if category else "Не найдена",
                        inline=True
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при обновлении настроек: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="setup_channels", description="Интерактивная настройка каналов")
    async def setup_channels(self, interaction: discord.Interaction):
        """Интерактивная настройка каналов"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "У вас нет прав администратора для изменения настроек.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            "Выберите канал для создания матчей:",
            view=ChannelSelectionView(interaction.guild, "match"),
            ephemeral=True
        )

    @app_commands.command(name="post_instructions", description="Опубликовать инструкции по работе бота")
    async def post_instructions(self, interaction: discord.Interaction):
        """Опубликовать инструкции по работе бота"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "У вас нет прав администратора для публикации инструкций.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        try:
            # Create instructions embed
            embed = discord.Embed(
                title="🎮 Discord Rating Bot - Инструкция",
                description="Бот для проведения рейтинговых матчей между игроками",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📋 Основные команды",
                value="""
                `/challenge @игрок` - Вызвать игрока на матч
                `/rating` - Посмотреть свой рейтинг
                `/leaderboard` - Таблица лидеров
                `/stats` - Статистика игрока
                """,
                inline=False
            )
            
            embed.add_field(
                name="🏆 Форматы матчей",
                value="""
                **Bo1** - Одна игра, побеждает игрок с лучшим временем
                **Bo2** - Две игры, побеждает игрок с меньшей суммой времени
                **Bo3** - Три игры, побеждает игрок с большим количеством побед
                """,
                inline=False
            )
            
            embed.add_field(
                name="⚡ Штрафы",
                value="За каждый рестарт добавляется штрафное время (настраивается администратором)",
                inline=False
            )
            
            embed.add_field(
                name="📊 Рейтинговая система",
                value="Используется система Glicko-2 для расчета рейтинга игроков",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Административные команды",
                value="""
                `/settings` - Настройки сервера
                `/setup_channels` - Настройка каналов
                `/new_season` - Создать новый сезон
                """,
                inline=False
            )
            
            embed.set_footer(text="Для получения помощи обратитесь к администратору сервера")
            
            # Send instructions
            message = await interaction.channel.send(embed=embed)
            
            # Pin the message
            await message.pin()
            
            # Update database with message ID
            async with self.db.get_session() as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    settings = PenaltySettings(
                        guild_id=interaction.guild_id,
                        restart_penalty=30
                    )
                    session.add(settings)
                
                settings.instructions_message_id = message.id
                await session.commit()
            
            await interaction.followup.send(
                f"Инструкции опубликованы и закреплены в {interaction.channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при публикации инструкций: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="new_season", description="Создать новый сезон")
    async def new_season(self, interaction: discord.Interaction, name: str):
        """Создать новый сезон"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "У вас нет прав администратора для создания сезонов.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        try:
            from models.season import Season
            from datetime import date, timedelta
            
            async with self.db.get_session() as session:
                # End current active season
                current_season = await session.execute(
                    "SELECT * FROM seasons WHERE is_active = true"
                )
                current_season = current_season.scalar_one_or_none()
                
                if current_season:
                    current_season.is_active = False
                
                # Create new season
                new_season = Season(
                    name=name,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=90),
                    is_active=True
                )
                
                session.add(new_season)
                await session.commit()
                
                await interaction.followup.send(
                    f"✅ Новый сезон '{name}' создан и активирован!",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при создании сезона: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="guild_info", description="Информация о настройках сервера")
    async def guild_info(self, interaction: discord.Interaction):
        """Информация о настройках сервера"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    await interaction.followup.send(
                        "Настройки сервера не найдены. Используйте `/settings` для настройки.",
                        ephemeral=True
                    )
                    return
                
                # Get guild statistics
                from models.match import Match
                from models.player import Player
                
                total_matches = await session.execute(
                    "SELECT COUNT(*) FROM matches WHERE guild_id = :guild_id",
                    {"guild_id": interaction.guild_id}
                )
                total_matches = total_matches.scalar()
                
                active_matches = await session.execute(
                    "SELECT COUNT(*) FROM matches WHERE guild_id = :guild_id AND status != 'complete'",
                    {"guild_id": interaction.guild_id}
                )
                active_matches = active_matches.scalar()
                
                total_players = await session.execute(
                    "SELECT COUNT(DISTINCT p.id) FROM players p JOIN matches m ON p.id IN (m.player1_id, m.player2_id) WHERE m.guild_id = :guild_id",
                    {"guild_id": interaction.guild_id}
                )
                total_players = total_players.scalar()
                
                # Create info embed
                embed = discord.Embed(
                    title="ℹ️ Информация о сервере",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="📊 Статистика",
                    value=f"""
                    Всего матчей: {total_matches}
                    Активных матчей: {active_matches}
                    Участников: {total_players}
                    """,
                    inline=False
                )
                
                embed.add_field(
                    name="⚙️ Настройки",
                    value=f"Штраф за рестарт: {settings.restart_penalty} сек",
                    inline=True
                )
                
                if settings.match_channel_id:
                    channel = interaction.guild.get_channel(settings.match_channel_id)
                    embed.add_field(
                        name="🎮 Канал матчей",
                        value=channel.mention if channel else "Не найден",
                        inline=True
                    )
                
                if settings.voice_category_id:
                    category = interaction.guild.get_channel(settings.voice_category_id)
                    embed.add_field(
                        name="🔊 Категория войсов",
                        value=f"📁 {category.name}" if category else "Не найдена",
                        inline=True
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при получении информации: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))