import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
from typing import Optional, List
import time
from database.database import DatabaseManager
from models.match import Match, MatchStatus, MatchStage
from models.referee_case import RefereeCase, CaseType, CaseStatus, ResolutionType
from models.referee import Referee
from models.penalty_settings import PenaltySettings

class RefereeCallModal(Modal, title="Вызов судьи"):
    def __init__(self, match_id: int, stage: str):
        super().__init__()
        self.match_id = match_id
        self.stage = stage
        
        self.problem_description = TextInput(
            label="Описание проблемы",
            placeholder="Подробно опишите проблему, которая возникла во время матча...",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        
        self.evidence = TextInput(
            label="Доказательства (необязательно)",
            placeholder="Ссылки на скриншоты, видео или другие доказательства...",
            required=False,
            max_length=500
        )
        
        self.add_item(self.problem_description)
        self.add_item(self.evidence)

class RefereeCaseView(View):
    def __init__(self, case: RefereeCase, match: Match, is_referee: bool = False):
        super().__init__(timeout=None)
        self.case = case
        self.match = match
        self.is_referee = is_referee
        
        if is_referee:
            # Referee actions
            self.add_item(Button(
                label="📝 Начать рассмотрение",
                custom_id="start_resolution",
                style=discord.ButtonStyle.primary
            ))
            self.add_item(Button(
                label="✅ Продолжить матч",
                custom_id="continue_match",
                style=discord.ButtonStyle.success
            ))
            self.add_item(Button(
                label="🔄 Переиграть игру",
                custom_id="replay_game",
                style=discord.ButtonStyle.secondary
            ))
            self.add_item(Button(
                label="❌ Аннулировать матч",
                custom_id="annull_match",
                style=discord.ButtonStyle.danger
            ))
        else:
            # Player view
            self.add_item(Button(
                label="📋 Статус дела",
                custom_id="case_status",
                style=discord.ButtonStyle.secondary
            ))

class RefereeResolutionModal(Modal, title="Решение судьи"):
    def __init__(self, case: RefereeCase, resolution_type: str):
        super().__init__()
        self.case = case
        self.resolution_type = resolution_type
        
        self.resolution_details = TextInput(
            label="Детали решения",
            placeholder="Подробно опишите, как вы решили проблему...",
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        
        self.referee_notes = TextInput(
            label="Заметки судьи (необязательно)",
            placeholder="Дополнительные комментарии или предупреждения...",
            required=False,
            max_length=500
        )
        
        self.add_item(self.resolution_details)
        self.add_item(self.referee_notes)

class RefereeSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        
    @app_commands.command(name="call_referee", description="Вызвать судью для разрешения проблемы")
    @app_commands.describe(
        problem_type="Тип проблемы",
        description="Краткое описание проблемы"
    )
    async def call_referee(
        self, 
        interaction: discord.Interaction,
        problem_type: str,
        description: str
    ):
        """Вызвать судью для разрешения проблемы"""
        await interaction.response.defer()
        
        try:
            # Check if user is in an active match
            async with self.db.get_session() as session:
                # Find active match for this user
                match = await session.execute(
                    """
                    SELECT m.* FROM matches m 
                    JOIN players p1 ON m.player1_id = p1.id 
                    JOIN players p2 ON m.player2_id = p2.id 
                    WHERE m.guild_id = :guild_id 
                    AND m.status NOT IN ('complete', 'annulled')
                    AND (p1.discord_id = :user_id OR p2.discord_id = :user_id)
                    """,
                    {
                        "guild_id": interaction.guild_id,
                        "user_id": interaction.user.id
                    }
                )
                match = match.scalar_one_or_none()
                
                if not match:
                    await interaction.followup.send(
                        "❌ У вас нет активного матча для вызова судьи.",
                        ephemeral=True
                    )
                    return
                
                if match.status == MatchStatus.REFEREE_INTERVENTION:
                    await interaction.followup.send(
                        "❌ Судья уже вызван для этого матча.",
                        ephemeral=True
                    )
                    return
                
                # Determine case type based on problem description
                case_type = self.determine_case_type(problem_type, match.current_stage)
                
                # Create referee case
                referee_case = RefereeCase(
                    match_id=match.id,
                    case_type=case_type,
                    reported_by=interaction.user.id,
                    problem_description=description,
                    stage_when_reported=match.current_stage.value
                )
                
                session.add(referee_case)
                
                # Update match status
                match.call_referee(None, description)
                
                await session.commit()
                
                # Create case view
                view = RefereeCaseView(referee_case, match)
                
                # Send notification to match thread
                if match.thread_id:
                    thread = interaction.guild.get_thread(match.thread_id)
                    if thread:
                        embed = discord.Embed(
                            title="🚨 Вызов судьи!",
                            description="Игрок вызвал судью для разрешения проблемы",
                            color=discord.Color.red()
                        )
                        
                        embed.add_field(
                            name="Проблема",
                            value=description,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Этап матча",
                            value=match.current_stage.value,
                            inline=True
                        )
                        
                        embed.add_field(
                            name="Заявитель",
                            value=interaction.user.mention,
                            inline=True
                        )
                        
                        embed.add_field(
                            name="Статус",
                            value="⏳ Ожидает назначения судьи",
                            inline=True
                        )
                        
                        await thread.send(
                            f"🚨 **ВНИМАНИЕ!** Матч приостановлен. Требуется судья.\n\n{interaction.user.mention} вызвал судью для разрешения проблемы.",
                            embed=embed,
                            view=view
                        )
                        
                        await interaction.followup.send(
                            f"✅ Судья вызван! Матч приостановлен. Ожидайте назначения судьи в {thread.mention}",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "❌ Ошибка: не удалось найти ветку матча.",
                            ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        "❌ Ошибка: матч не имеет ветки для уведомлений.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при вызове судьи: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="referee_cases", description="Просмотр активных случаев судейства")
    async def view_referee_cases(self, interaction: discord.Interaction):
        """Просмотр активных случаев судейства"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                # Check if user is a referee
                referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id AND is_active = true",
                    {"discord_id": interaction.user.id, "guild_id": interaction.guild_id}
                )
                referee = referee.scalar_one_or_none()
                
                if not referee:
                    await interaction.followup.send(
                        "❌ У вас нет прав судьи для просмотра случаев.",
                        ephemeral=True
                    )
                    return
                
                # Get active cases
                active_cases = await session.execute(
                    """
                    SELECT rc.*, m.thread_id, p1.username as player1_name, p2.username as player2_name
                    FROM referee_cases rc
                    JOIN matches m ON rc.match_id = m.id
                    JOIN players p1 ON m.player1_id = p1.id
                    JOIN players p2 ON m.player2_id = p2.id
                    WHERE rc.status IN ('opened', 'assigned', 'in_progress')
                    AND m.guild_id = :guild_id
                    ORDER BY rc.created_at DESC
                    """,
                    {"guild_id": interaction.guild_id}
                )
                active_cases = active_cases.fetchall()
                
                if not active_cases:
                    await interaction.followup.send(
                        "✅ Нет активных случаев судейства.",
                        ephemeral=True
                    )
                    return
                
                # Create cases embed
                embed = discord.Embed(
                    title="📋 Активные случаи судейства",
                    description=f"Найдено {len(active_cases)} активных случаев",
                    color=discord.Color.orange()
                )
                
                for case in active_cases[:5]:  # Show first 5 cases
                    status_emoji = {
                        "opened": "⏳",
                        "assigned": "👨‍⚖️",
                        "in_progress": "🔍"
                    }.get(case.status, "❓")
                    
                    embed.add_field(
                        name=f"{status_emoji} Дело #{case.id}",
                        value=f"""
                        **Матч**: {case.player1_name} vs {case.player2_name}
                        **Тип**: {case.case_type.value}
                        **Статус**: {case.status.value}
                        **Этап**: {case.stage_when_reported}
                        """,
                        inline=False
                    )
                
                if len(active_cases) > 5:
                    embed.set_footer(text=f"Показано 5 из {len(active_cases)} случаев")
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при получении случаев: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="take_case", description="Взять дело на рассмотрение")
    @app_commands.describe(case_id="ID дела для рассмотрения")
    async def take_case(self, interaction: discord.Interaction, case_id: int):
        """Взять дело на рассмотрение"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                # Check if user is a referee
                referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id AND is_active = true",
                    {"discord_id": interaction.user.id, "guild_id": interaction.guild_id}
                )
                referee = referee.scalar_one_or_none()
                
                if not referee:
                    await interaction.followup.send(
                        "❌ У вас нет прав судьи для рассмотрения дел.",
                        ephemeral=True
                    )
                    return
                
                # Get the case
                case = await session.execute(
                    "SELECT * FROM referee_cases WHERE id = :case_id",
                    {"case_id": case_id}
                )
                case = case.scalar_one_or_none()
                
                if not case:
                    await interaction.followup.send(
                        "❌ Дело не найдено.",
                        ephemeral=True
                    )
                    return
                
                if not case.can_be_assigned():
                    await interaction.followup.send(
                        "❌ Это дело уже назначено или не может быть назначено.",
                        ephemeral=True
                    )
                    return
                
                # Get match for guild check
                match = await session.execute(
                    "SELECT * FROM matches WHERE id = :match_id",
                    {"match_id": case.match_id}
                )
                match = match.scalar_one_or_none()
                
                if not match or match.guild_id != interaction.guild_id:
                    await interaction.followup.send(
                        "❌ Дело не принадлежит этому серверу.",
                        ephemeral=True
                    )
                    return
                
                # Assign case to referee
                case.assign_referee(interaction.user.id)
                case.start_resolution()
                
                await session.commit()
                
                await interaction.followup.send(
                    f"✅ Дело #{case_id} назначено вам на рассмотрение.",
                    ephemeral=True
                )
                
                # Notify in match thread
                if match.thread_id:
                    thread = interaction.guild.get_thread(match.thread_id)
                    if thread:
                        embed = discord.Embed(
                            title="👨‍⚖️ Судья назначен!",
                            description=f"Дело назначено судье {interaction.user.mention}",
                            color=discord.Color.blue()
                        )
                        
                        embed.add_field(
                            name="Статус",
                            value="🔍 Рассматривается судьей",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="Судья",
                            value=interaction.user.mention,
                            inline=True
                        )
                        
                        await thread.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при назначении дела: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="resolve_case", description="Разрешить случай судейства")
    @app_commands.describe(
        case_id="ID дела для разрешения",
        resolution_type="Тип решения",
        details="Детали решения"
    )
    async def resolve_case(
        self, 
        interaction: discord.Interaction,
        case_id: int,
        resolution_type: str,
        details: str
    ):
        """Разрешить случай судейства"""
        await interaction.response.defer()
        
        try:
            async with self.db.get_session() as session:
                # Check if user is a referee
                referee = await session.execute(
                    "SELECT * FROM referees WHERE discord_id = :discord_id AND guild_id = :guild_id AND is_active = true",
                    {"discord_id": interaction.user.id, "guild_id": interaction.guild_id}
                )
                referee = referee.scalar_one_or_none()
                
                if not referee:
                    await interaction.followup.send(
                        "❌ У вас нет прав судьи для разрешения дел.",
                        ephemeral=True
                    )
                    return
                
                # Get the case
                case = await session.execute(
                    "SELECT * FROM referee_cases WHERE id = :case_id AND referee_id = :referee_id",
                    {"case_id": case_id, "referee_id": interaction.user.id}
                )
                case = case.scalar_one_or_none()
                
                if not case:
                    await interaction.followup.send(
                        "❌ Дело не найдено или не назначено вам.",
                        ephemeral=True
                    )
                    return
                
                # Get match
                match = await session.execute(
                    "SELECT * FROM matches WHERE id = :match_id",
                    {"match_id": case.match_id}
                )
                match = match.scalar_one_or_none()
                
                if not match:
                    await interaction.followup.send(
                        "❌ Матч не найден.",
                        ephemeral=True
                    )
                    return
                
                # Parse resolution type
                try:
                    resolution_enum = ResolutionType(resolution_type.lower())
                except ValueError:
                    await interaction.followup.send(
                        "❌ Неверный тип решения. Доступные типы: continue_match, modify_results, replay_game, annull_match, warning_issued, other",
                        ephemeral=True
                    )
                    return
                
                # Resolve the case
                case.resolve_case(resolution_enum, details)
                
                # Handle match based on resolution
                if resolution_enum == ResolutionType.ANNULL_MATCH:
                    match.annul_match(details)
                elif resolution_enum == ResolutionType.CONTINUE_MATCH:
                    match.resolve_referee_intervention(details)
                
                # Update referee statistics
                referee.increment_cases_resolved()
                if resolution_enum == ResolutionType.ANNULL_MATCH:
                    referee.increment_matches_annulled()
                
                await session.commit()
                
                await interaction.followup.send(
                    f"✅ Дело #{case_id} успешно разрешено.",
                    ephemeral=True
                )
                
                # Notify in match thread
                if match.thread_id:
                    thread = interaction.guild.get_thread(match.thread_id)
                    if thread:
                        embed = discord.Embed(
                            title="✅ Случай судейства разрешен",
                            description=f"Судья {interaction.user.mention} разрешил проблему",
                            color=discord.Color.green()
                        )
                        
                        embed.add_field(
                            name="Решение",
                            value=resolution_enum.value,
                            inline=True
                        )
                        
                        embed.add_field(
                            name="Детали",
                            value=details,
                            inline=False
                        )
                        
                        if resolution_enum == ResolutionType.ANNULL_MATCH:
                            embed.add_field(
                                name="Статус матча",
                                value="❌ Матч аннулирован",
                                inline=True
                            )
                        elif resolution_enum == ResolutionType.CONTINUE_MATCH:
                            embed.add_field(
                                name="Статус матча",
                                value="▶️ Матч продолжается",
                                inline=True
                            )
                        
                        await thread.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при разрешении дела: {str(e)}",
                ephemeral=True
            )
    
    def determine_case_type(self, problem_type: str, match_stage: MatchStage) -> CaseType:
        """Determine case type based on problem description and match stage"""
        problem_lower = problem_type.lower()
        
        if "драфт" in problem_lower or "draft" in problem_lower:
            return CaseType.DRAFT_DISPUTE
        elif "трансляция" in problem_lower or "стрим" in problem_lower or "stream" in problem_lower:
            return CaseType.STREAM_ISSUE
        elif "время" in problem_lower or "time" in problem_lower:
            return CaseType.TIME_DISPUTE
        elif "результат" in problem_lower or "result" in problem_lower:
            return CaseType.RESULT_DISPUTE
        elif "правила" in problem_lower or "rules" in problem_lower:
            return CaseType.RULE_VIOLATION
        elif "техническая" in problem_lower or "technical" in problem_lower:
            return CaseType.TECHNICAL_ISSUE
        else:
            return CaseType.OTHER

async def setup(bot: commands.Bot):
    await bot.add_cog(RefereeSystem(bot))