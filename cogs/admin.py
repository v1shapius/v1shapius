import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from typing import Optional
from database.database import DatabaseManager
from locales import LocaleManager
from models.penalty_settings import PenaltySettings
from datetime import datetime

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

class DetailedPenaltyModal(Modal, title="Детальная настройка штрафов за рестарты"):
    def __init__(self, current_settings: Optional[PenaltySettings] = None):
        super().__init__()
        self.current_settings = current_settings
        
        # Get current values or defaults
        penalties = current_settings.restart_penalties if current_settings else {
            "free_restarts": 2,
            "penalty_tiers": {"3": 5, "4": 15, "5": 999}
        }
        
        self.free_restarts = TextInput(
            label="Количество бесплатных рестартов",
            placeholder="2",
            default=str(penalties.get("free_restarts", 2)),
            required=True,
            min_length=1,
            max_length=2
        )
        
        self.tier3_penalty = TextInput(
            label="Штраф за 3-й рестарт (секунды)",
            placeholder="5",
            default=str(penalties.get("penalty_tiers", {}).get("3", 5)),
            required=True,
            min_length=1,
            max_length=3
        )
        
        self.tier4_penalty = TextInput(
            label="Штраф за 4-й рестарт (секунды)",
            placeholder="15",
            default=str(penalties.get("penalty_tiers", {}).get("4", 15)),
            required=True,
            min_length=1,
            max_length=3
        )
        
        self.tier5_penalty = TextInput(
            label="Штраф за 5-й рестарт (секунды)",
            placeholder="999",
            default=str(penalties.get("penalty_tiers", {}).get("5", 999)),
            required=True,
            min_length=1,
            max_length=3
        )
        
        self.add_item(self.free_restarts)
        self.add_item(self.tier3_penalty)
        self.add_item(self.tier4_penalty)
        self.add_item(self.tier5_penalty)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            # Validate input
            free_restarts = int(self.free_restarts.value)
            tier3_penalty = int(self.tier3_penalty.value)
            tier4_penalty = int(self.tier4_penalty.value)
            tier5_penalty = int(self.tier5_penalty.value)
            
            if free_restarts < 0 or tier3_penalty < 0 or tier4_penalty < 0 or tier5_penalty < 0:
                await interaction.response.send_message(
                    "❌ Штрафы не могут быть отрицательными.",
                    ephemeral=True
                )
                return
            
            # Update penalty settings
            db_manager = DatabaseManager()
        session = await db_manager.get_session()
        async with session as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    await interaction.response.send_message(
                        "❌ Настройки сервера не найдены.",
                        ephemeral=True
                    )
                    return
                
                # Update detailed penalties
                settings.restart_penalties = {
                    "free_restarts": free_restarts,
                    "penalty_tiers": {
                        "3": tier3_penalty,
                        "4": tier4_penalty,
                        "5": tier5_penalty
                    }
                }
                
                await session.commit()
                
                # Create confirmation embed
                embed = discord.Embed(
                    title="✅ Штрафы за рестарты обновлены",
                    description="Новая конфигурация штрафов",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🆓 Бесплатные рестарты",
                    value=f"Первые {free_restarts} рестарта бесплатны",
                    inline=False
                )
                
                embed.add_field(
                    name="💰 Штрафные рестарты",
                    value=f"""
                    3-й рестарт: +{tier3_penalty} секунд
                    4-й рестарт: +{tier4_penalty} секунд
                    5-й рестарт: +{tier5_penalty} секунд
                    """,
                    inline=False
                )
                
                # Add examples
                examples = []
                for i in range(1, 6):
                    total_penalty = settings.calculate_total_penalty(i)
                    examples.append(f"{i} рестарт: +{total_penalty}с")
                
                embed.add_field(
                    name="📊 Примеры расчета",
                    value="\n".join(examples),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Пожалуйста, введите корректные числовые значения.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при обновлении штрафов: {str(e)}",
                ephemeral=True
            )

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
        penalty="Штраф за рестарт в секундах (упрощенная настройка)",
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
            session = await self.db.get_session()
            async with session as session:
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
                    name="Штраф за рестарт (упрощенный)",
                    value=f"{settings.restart_penalty} секунд",
                    inline=True
                )
                
                # Show detailed penalty info
                penalties = settings.restart_penalties
                free_restarts = penalties.get("free_restarts", 2)
                penalty_tiers = penalties.get("penalty_tiers", {})
                
                detailed_penalty_text = f"Бесплатных: {free_restarts}\n"
                for tier, penalty in sorted(penalty_tiers.items(), key=lambda x: int(x[0])):
                    detailed_penalty_text += f"{tier}-й: +{penalty}с\n"
                
                embed.add_field(
                    name="Детальные штрафы",
                    value=detailed_penalty_text.strip(),
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

    @app_commands.command(name="penalties", description="Детальная настройка штрафов за рестарты")
    async def configure_penalties(self, interaction: discord.Interaction):
        """Детальная настройка штрафов за рестарты"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "У вас нет прав администратора для изменения настроек.",
                ephemeral=True
            )
            return
            
        try:
            # Get current settings
            session = await self.db.get_session()
            async with session as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    await interaction.response.send_message(
                        "Сначала настройте базовые параметры сервера командой `/settings`",
                        ephemeral=True
                    )
                    return
                
                # Open detailed penalty modal
                modal = DetailedPenaltyModal(settings)
                await interaction.response.send_modal(modal)
                
        except Exception as e:
            await interaction.response.send_message(
                f"Ошибка при открытии настроек штрафов: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="penalty_info", description="Информация о текущих штрафах за рестарты")
    async def penalty_info(self, interaction: discord.Interaction):
        """Показать информацию о текущих штрафах за рестарты"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
            async with session as session:
                settings = await session.get(PenaltySettings, interaction.guild_id)
                
                if not settings:
                    await interaction.followup.send(
                        "Настройки сервера не найдены. Используйте `/settings` для настройки.",
                        ephemeral=True
                    )
                    return
                
                # Create penalty info embed
                embed = discord.Embed(
                    title="⚡ Штрафы за рестарты",
                    description="Текущая конфигурация штрафов",
                    color=discord.Color.orange()
                )
                
                penalties = settings.restart_penalties
                free_restarts = penalties.get("free_restarts", 2)
                penalty_tiers = penalties.get("penalty_tiers", {})
                
                embed.add_field(
                    name="🆓 Бесплатные рестарты",
                    value=f"Первые {free_restarts} рестарта бесплатны",
                    inline=False
                )
                
                if penalty_tiers:
                    penalty_text = ""
                    for tier, penalty in sorted(penalty_tiers.items(), key=lambda x: int(x[0])):
                        penalty_text += f"**{tier}-й рестарт**: +{penalty} секунд\n"
                    embed.add_field(
                        name="💰 Штрафные рестарты",
                        value=penalty_text,
                        inline=False
                    )
                
                # Add examples
                examples = []
                for i in range(1, 6):
                    total_penalty = settings.calculate_total_penalty(i)
                    examples.append(f"{i} рестарт: +{total_penalty}с")
                
                embed.add_field(
                    name="📊 Примеры расчета",
                    value="\n".join(examples),
                    inline=False
                )
                
                embed.add_field(
                    name="⚙️ Упрощенная настройка",
                    value=f"Общий штраф: {settings.restart_penalty}с за каждый рестарт",
                    inline=False
                )
                
                embed.set_footer(text="Используйте /penalties для изменения настроек")
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"Ошибка при получении информации о штрафах: {str(e)}",
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
                name="⚡ Штрафы за рестарты",
                value="Гибкая система штрафов с бесплатными рестартами и настраиваемыми уровнями",
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
                `/penalties` - Детальная настройка штрафов
                `/penalty_info` - Информация о штрафах
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
            session = await self.db.get_session()
            async with session as session:
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
            
            session = await self.db.get_session()
            async with session as session:
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
            session = await self.db.get_session()
            async with session as session:
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
                
                # Show detailed penalty info
                penalties = settings.restart_penalties
                free_restarts = penalties.get("free_restarts", 2)
                embed.add_field(
                    name="⚡ Штрафы",
                    value=f"Бесплатных: {free_restarts}",
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

    @app_commands.command(name="season_management", description="Управление сезонами")
    @app_commands.describe(action="Действие с сезоном")
    async def season_management(
        self, 
        interaction: discord.Interaction,
        action: str
    ):
        """Управление сезонами"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для управления сезонами.",
                ephemeral=True
            )
            return
        
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
                        "❌ Нет активного сезона для управления.",
                        ephemeral=True
                    )
                    return
                
                action_lower = action.lower()
                
                if action_lower == "block_matches":
                    # Block new matches
                    current_season.block_new_matches()
                    await session.commit()
                    
                    embed = discord.Embed(
                        title="🚫 Создание матчей заблокировано",
                        description=f"Сезон: {current_season.name}",
                        color=discord.Color.red()
                    )
                    
                    embed.add_field(
                        name="Статус",
                        value="Новые матчи заблокированы",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Причина",
                        value="Администратор заблокировал создание матчей",
                        inline=True
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                elif action_lower == "unblock_matches":
                    # Unblock new matches
                    current_season.new_matches_blocked = False
                    await session.commit()
                    
                    embed = discord.Embed(
                        title="✅ Создание матчей разблокировано",
                        description=f"Сезон: {current_season.name}",
                        color=discord.Color.green()
                    )
                    
                    embed.add_field(
                        name="Статус",
                        value="Новые матчи разрешены",
                        inline=True
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                elif action_lower == "mark_ending":
                    # Mark season as ending
                    current_season.mark_as_ending()
                    await session.commit()
                    
                    embed = discord.Embed(
                        title="⚠️ Сезон помечен как завершающийся",
                        description=f"Сезон: {current_season.name}",
                        color=discord.Color.orange()
                    )
                    
                    embed.add_field(
                        name="Статус",
                        value="Сезон завершается",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Действия",
                        value="• Новые матчи заблокированы\n• Рейтинг заблокирован\n• Игроки получат уведомления",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                elif action_lower == "force_end":
                    # Force end season
                    current_season.end_season()
                    await session.commit()
                    
                    embed = discord.Embed(
                        title="🏁 Сезон принудительно завершен",
                        description=f"Сезон: {current_season.name}",
                        color=discord.Color.red()
                    )
                    
                    embed.add_field(
                        name="Статус",
                        value="Сезон завершен",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Внимание",
                        value="Все активные матчи будут аннулированы!",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                elif action_lower == "status":
                    # Show detailed season status
                    embed = discord.Embed(
                        title=f"📊 Статус сезона: {current_season.name}",
                        description="Детальная информация о сезоне",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(
                        name="Основная информация",
                        value=f"**Название**: {current_season.name}\n**Начало**: {current_season.start_date.strftime('%d.%m.%Y %H:%M')}\n**Конец**: {current_season.end_date.strftime('%d.%m.%Y %H:%M')}",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="Статус",
                        value=f"**Активен**: {'Да' if current_season.is_active else 'Нет'}\n**Завершается**: {'Да' if current_season.is_ending else 'Нет'}\n**Рейтинг заблокирован**: {'Да' if current_season.is_rating_locked else 'Нет'}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Блокировки",
                        value=f"**Матчи заблокированы**: {'Да' if current_season.new_matches_blocked else 'Нет'}\n**Расчет рейтинга заблокирован**: {'Да' if current_season.rating_calculation_locked else 'Нет'}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Уведомления",
                        value=f"**Предупреждение отправлено**: {'Да' if current_season.season_end_warning_sent else 'Нет'}",
                        inline=True
                    )
                    
                    # Calculate days until end
                    days_until_end = (current_season.end_date - datetime.utcnow()).days
                    embed.add_field(
                        name="Время до завершения",
                        value=f"**Дней**: {days_until_end}\n**Статус**: {current_season.get_status_description()}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Блокировка матчей",
                        value=f"**Причина**: {current_season.get_blocking_reason()}",
                        inline=True
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                else:
                    await interaction.followup.send(
                        f"❌ Неизвестное действие: {action}\n\n"
                        "Доступные действия:\n"
                        "• `block_matches` - Заблокировать создание матчей\n"
                        "• `unblock_matches` - Разблокировать создание матчей\n"
                        "• `mark_ending` - Пометить сезон как завершающийся\n"
                        "• `force_end` - Принудительно завершить сезон\n"
                        "• `status` - Показать статус сезона",
                        ephemeral=True
                    )
                    
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при управлении сезоном: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))