import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
from typing import Optional, List
from database.database import DatabaseManager
from models.referee import Referee
from models.referee_case import RefereeCase, CaseStatus

class RefereePermissionsModal(Modal, title="Настройка прав судьи"):
    def __init__(self, current_referee: Optional[Referee] = None):
        super().__init__()
        self.current_referee = current_referee
        
        self.username = TextInput(
            label="Имя пользователя",
            placeholder="Имя пользователя",
            default=current_referee.username if current_referee else "",
            required=True,
            max_length=100
        )
        
        self.can_annul_matches = TextInput(
            label="Может аннулировать матчи (да/нет)",
            placeholder="да",
            default="да" if current_referee and current_referee.can_annul_matches else "нет",
            required=True,
            max_length=3
        )
        
        self.can_modify_results = TextInput(
            label="Может изменять результаты (да/нет)",
            placeholder="да",
            default="да" if current_referee and current_referee.can_modify_results else "нет",
            required=True,
            max_length=3
        )
        
        self.can_resolve_disputes = TextInput(
            label="Может разрешать споры (да/нет)",
            placeholder="да",
            default="да" if current_referee and current_referee.can_resolve_disputes else "нет",
            required=True,
            max_length=3
        )
        
        self.notes = TextInput(
            label="Заметки (необязательно)",
            placeholder="Дополнительная информация о судье...",
            default=current_referee.notes if current_referee else "",
            required=False,
            max_length=500
        )
        
        self.add_item(self.username)
        self.add_item(self.can_annul_matches)
        self.add_item(self.can_modify_results)
        self.add_item(self.can_resolve_disputes)
        self.add_item(self.notes)

class RefereeManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        
    @app_commands.command(name="add_referee", description="Добавить нового судью")
    @app_commands.describe(user="Пользователь для назначения судьей")
    async def add_referee(self, interaction: discord.Interaction, user: discord.Member):
        """Добавить нового судью"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для управления судьями.",
                ephemeral=True
            )
            return
            
        try:
            session = await self.db.get_session()
        async with session:
                # Check if user is already a referee
                existing_referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id",
                    {"discord_id": user.id, "guild_id": interaction.guild_id}
                )
                existing_referee = existing_referee.scalar_one_or_none()
                
                if existing_referee:
                    if existing_referee.is_active:
                        await interaction.response.send_message(
                            f"❌ {user.mention} уже является активным судьей.",
                            ephemeral=True
                        )
                        return
                    else:
                        # Reactivate existing referee
                        existing_referee.is_active = True
                        await session.commit()
                        
                        await interaction.response.send_message(
                            f"✅ Судья {user.mention} восстановлен в правах.",
                            ephemeral=True
                        )
                        return
                
                # Create new referee with default permissions
                new_referee = Referee(
                    discord_id=user.id,
                    username=user.display_name,
                    guild_id=interaction.guild_id,
                    is_active=True,
                    can_annul_matches=True,
                    can_modify_results=True,
                    can_resolve_disputes=True
                )
                
                session.add(new_referee)
                await session.commit()
                
                await interaction.response.send_message(
                    f"✅ {user.mention} назначен судьей с полными правами.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при добавлении судьи: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="remove_referee", description="Убрать права судьи")
    @app_commands.describe(user="Пользователь для снятия прав судьи")
    async def remove_referee(self, interaction: discord.Interaction, user: discord.Member):
        """Убрать права судьи"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для управления судьями.",
                ephemeral=True
            )
            return
            
        try:
            session = await self.db.get_session()
        async with session:
                # Check if user is a referee
                referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id",
                    {"discord_id": user.id, "guild_id": interaction.guild_id}
                )
                referee = referee.scalar_one_or_none()
                
                if not referee:
                    await interaction.response.send_message(
                        f"❌ {user.mention} не является судьей.",
                        ephemeral=True
                    )
                    return
                
                # Deactivate referee
                referee.is_active = False
                await session.commit()
                
                await interaction.response.send_message(
                    f"✅ Права судьи у {user.mention} отозваны.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при отзыве прав судьи: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="referee_permissions", description="Настроить права судьи")
    @app_commands.describe(user="Пользователь для настройки прав")
    async def referee_permissions(self, interaction: discord.Interaction, user: discord.Member):
        """Настроить права судьи"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для управления судьями.",
                ephemeral=True
            )
            return
            
        try:
            session = await self.db.get_session()
        async with session:
                # Check if user is a referee
                referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id",
                    {"discord_id": user.id, "guild_id": interaction.guild_id}
                )
                referee = referee.scalar_one_or_none()
                
                if not referee:
                    await interaction.response.send_message(
                        f"❌ {user.mention} не является судьей. Сначала добавьте его командой `/add_referee`.",
                        ephemeral=True
                    )
                    return
                
                # Open permissions modal
                modal = RefereePermissionsModal(referee)
                await interaction.response.send_modal(modal)
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при настройке прав судьи: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="referee_list", description="Список всех судей")
    async def referee_list(self, interaction: discord.Interaction):
        """Список всех судей"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session:
                # Get all referees for this guild
                referees = await session.execute(
                    "SELECT * FROM referees WHERE guild_id = :guild_id ORDER BY is_active DESC, username ASC",
                    {"guild_id": interaction.guild_id}
                )
                referees = referees.fetchall()
                
                if not referees:
                    await interaction.followup.send(
                        "❌ На этом сервере нет назначенных судей.",
                        ephemeral=True
                    )
                    return
                
                # Create referee list embed
                embed = discord.Embed(
                    title="👨‍⚖️ Список судей",
                    description=f"Всего судей: {len(referees)}",
                    color=discord.Color.blue()
                )
                
                active_referees = []
                inactive_referees = []
                
                for referee in referees:
                    if referee.is_active:
                        active_referees.append(referee)
                    else:
                        inactive_referees.append(referee)
                
                # Active referees
                if active_referees:
                    active_text = ""
                    for referee in active_referees:
                        permissions = []
                        if referee.can_annul_matches:
                            permissions.append("❌ Аннулировать матчи")
                        if referee.can_modify_results:
                            permissions.append("✏️ Изменять результаты")
                        if referee.can_resolve_disputes:
                            permissions.append("🔍 Разрешать споры")
                        
                        active_text += f"**{referee.username}**\n"
                        active_text += f"Права: {', '.join(permissions)}\n"
                        active_text += f"Дела: {referee.cases_resolved} | Аннулировано: {referee.matches_annulled}\n\n"
                    
                    embed.add_field(
                        name="🟢 Активные судьи",
                        value=active_text.strip(),
                        inline=False
                    )
                
                # Inactive referees
                if inactive_referees:
                    inactive_text = ""
                    for referee in inactive_referees:
                        inactive_text += f"**{referee.username}**\n"
                        inactive_text += f"Дела: {referee.cases_resolved} | Аннулировано: {referee.matches_annulled}\n\n"
                    
                    embed.add_field(
                        name="🔴 Неактивные судьи",
                        value=inactive_text.strip(),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении списка судей: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="referee_stats", description="Статистика судейства")
    async def referee_stats(self, interaction: discord.Interaction):
        """Статистика судейства"""
        await interaction.response.defer()
        
        try:
            session = await self.db.get_session()
        async with session:
                # Get referee statistics
                stats = await session.execute(
                    """
                    SELECT 
                        COUNT(*) as total_referees,
                        SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active_referees,
                        SUM(cases_resolved) as total_cases_resolved,
                        SUM(matches_annulled) as total_matches_annulled
                    FROM referees 
                    WHERE guild_id = :guild_id
                    """,
                    {"guild_id": interaction.guild_id}
                )
                stats = stats.scalar_one_or_none()
                
                if not stats:
                    await interaction.followup.send(
                        "❌ Нет данных о судействе на этом сервере.",
                        ephemeral=True
                    )
                    return
                
                # Get active cases count
                active_cases = await session.execute(
                    """
                    SELECT COUNT(*) FROM referee_cases rc
                    JOIN matches m ON rc.match_id = m.id
                    WHERE m.guild_id = :guild_id AND rc.status IN ('opened', 'assigned', 'in_progress')
                    """,
                    {"guild_id": interaction.guild_id}
                )
                active_cases = active_cases.scalar()
                
                # Get top referees
                top_referees = await session.execute(
                    """
                    SELECT username, cases_resolved, matches_annulled
                    FROM referees 
                    WHERE guild_id = :guild_id AND is_active = true
                    ORDER BY cases_resolved DESC, matches_annulled DESC
                    LIMIT 5
                    """,
                    {"guild_id": interaction.guild_id}
                )
                top_referees = top_referees.fetchall()
                
                # Create stats embed
                embed = discord.Embed(
                    title="📊 Статистика судейства",
                    description=f"Общая статистика по серверу",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="👨‍⚖️ Судьи",
                    value=f"Всего: {stats.total_referees} | Активных: {stats.active_referees}",
                    inline=True
                )
                
                embed.add_field(
                    name="📋 Дела",
                    value=f"Разрешено: {stats.total_cases_resolved} | Активных: {active_cases}",
                    inline=True
                )
                
                embed.add_field(
                    name="❌ Аннулировано",
                    value=f"Матчей: {stats.total_matches_annulled}",
                    inline=True
                )
                
                # Top referees
                if top_referees:
                    top_text = ""
                    for i, referee in enumerate(top_referees, 1):
                        top_text += f"{i}. **{referee.username}**\n"
                        top_text += f"   Дела: {referee.cases_resolved} | Аннулировано: {referee.matches_annulled}\n"
                    
                    embed.add_field(
                        name="🏆 Топ судей",
                        value=top_text.strip(),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении статистики: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(RefereeManagement(bot))