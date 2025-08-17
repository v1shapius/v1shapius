import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional, List
from database.database import DatabaseManager
from models.guild_roles import RoleType, DEFAULT_ROLE_CONFIGS, Permissions
from services.role_manager import RoleManager
import asyncio

class RoleSetupModal(Modal, title="Настройка роли"):
    """Modal for setting up a guild role"""
    
    discord_role_id = TextInput(
        label="ID Discord роли",
        placeholder="Введите ID роли Discord",
        max_length=20,
        required=True
    )
    
    role_name = TextInput(
        label="Название роли",
        placeholder="Описательное название роли",
        max_length=100,
        required=True
    )
    
    description = TextInput(
        label="Описание",
        placeholder="Описание роли и её назначения",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    def __init__(self, role_type: RoleType):
        super().__init__()
        self.role_type = role_type

class RoleAssignmentModal(Modal, title="Назначение роли"):
    """Modal for assigning roles to members"""
    
    member_id = TextInput(
        label="ID участника",
        placeholder="Введите ID участника Discord",
        max_length=20,
        required=True
    )
    
    def __init__(self, role_type: RoleType):
        super().__init__()
        self.role_type = role_type

class RoleManagementView(View):
    """View for role management interactions"""
    
    def __init__(self, guild_id: int, role_manager: RoleManager):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.role_manager = role_manager
        
        # Add action buttons
        self.add_item(Button(
            label="🔧 Настроить роли",
            custom_id="setup_roles",
            style=discord.ButtonStyle.primary
        ))
        
        self.add_item(Button(
            label="👥 Назначить роль",
            custom_id="assign_role",
            style=discord.ButtonStyle.secondary
        ))
        
        self.add_item(Button(
            label="📋 Список ролей",
            custom_id="list_roles",
            style=discord.ButtonStyle.secondary
        ))

class RoleManagement(commands.Cog):
    """Cog for managing guild roles"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.role_manager = RoleManager(bot)
        
    @app_commands.command(name="setup_roles", description="Настроить роли для сервера")
    @app_commands.describe(
        role_type="Тип роли для настройки"
    )
    async def setup_roles(self, interaction: discord.Interaction, role_type: str):
        """Setup roles for the guild"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для настройки ролей.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate role type
            try:
                role_type_enum = RoleType(role_type.lower())
            except ValueError:
                await interaction.followup.send(
                    f"❌ Неверный тип роли. Доступные типы: {', '.join([rt.value for rt in RoleType])}",
                    ephemeral=True
                )
                return
            
            # Show role setup modal
            modal = RoleSetupModal(role_type_enum)
            await interaction.followup.send(
                f"🔧 Настройка роли {role_type_enum.value}",
                view=RoleManagementView(interaction.guild_id, self.role_manager)
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при настройке ролей: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="create_role", description="Создать роль для сервера")
    @app_commands.describe(
        role_type="Тип роли",
        discord_role_id="ID Discord роли",
        role_name="Название роли",
        description="Описание роли (необязательно)",
        auto_assign="Автоматически назначать новым участникам"
    )
    async def create_role(
        self, 
        interaction: discord.Interaction, 
        role_type: str, 
        discord_role_id: int, 
        role_name: str, 
        description: Optional[str] = None,
        auto_assign: bool = False
    ):
        """Create a new guild role"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для создания ролей.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate role type
            try:
                role_type_enum = RoleType(role_type.lower())
            except ValueError:
                await interaction.followup.send(
                    f"❌ Неверный тип роли. Доступные типы: {', '.join([rt.value for rt in RoleType])}",
                    ephemeral=True
                )
                return
            
            # Validate Discord role exists
            discord_role = interaction.guild.get_role(discord_role_id)
            if not discord_role:
                await interaction.followup.send(
                    "❌ Роль с указанным ID не найдена на сервере.",
                    ephemeral=True
                )
                return
            
            # Create role
            role = await self.role_manager.create_guild_role(
                guild_id=interaction.guild_id,
                role_type=role_type_enum,
                discord_role_id=discord_role_id,
                role_name=role_name,
                description=description,
                auto_assign=auto_assign
            )
            
            if role:
                await interaction.followup.send(
                    f"✅ Роль **{role_name}** успешно создана!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Не удалось создать роль. Возможно, она уже существует.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при создании роли: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="assign_role", description="Назначить роль участнику")
    @app_commands.describe(
        role_type="Тип роли для назначения",
        member="Участник для назначения роли"
    )
    async def assign_role(
        self, 
        interaction: discord.Interaction, 
        role_type: str, 
        member: discord.Member
    ):
        """Assign a role to a member"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для назначения ролей.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate role type
            try:
                role_type_enum = RoleType(role_type.lower())
            except ValueError:
                await interaction.followup.send(
                    f"❌ Неверный тип роли. Доступные типы: {', '.join([rt.value for rt in RoleType])}",
                    ephemeral=True
                )
                return
            
            # Assign role
            success = await self.role_manager.assign_role_to_member(
                guild_id=interaction.guild_id,
                member_id=member.id,
                role_type=role_type_enum
            )
            
            if success:
                await interaction.followup.send(
                    f"✅ Роль **{role_type_enum.value}** успешно назначена участнику {member.mention}!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Не удалось назначить роль. Проверьте настройки роли.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при назначении роли: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="remove_role", description="Убрать роль у участника")
    @app_commands.describe(
        role_type="Тип роли для удаления",
        member="Участник для удаления роли"
    )
    async def remove_role(
        self, 
        interaction: discord.Interaction, 
        role_type: str, 
        member: discord.Member
    ):
        """Remove a role from a member"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для удаления ролей.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate role type
            try:
                role_type_enum = RoleType(role_type.lower())
            except ValueError:
                await interaction.followup.send(
                    f"❌ Неверный тип роли. Доступные типы: {', '.join([rt.value for rt in RoleType])}",
                    ephemeral=True
                )
                return
            
            # Remove role
            success = await self.role_manager.remove_role_from_member(
                guild_id=interaction.guild_id,
                member_id=member.id,
                role_type=role_type_enum
            )
            
            if success:
                await interaction.followup.send(
                    f"✅ Роль **{role_type_enum.value}** успешно удалена у участника {member.mention}!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Не удалось удалить роль. Проверьте настройки роли.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при удалении роли: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="list_roles", description="Список ролей сервера")
    async def list_roles(self, interaction: discord.Interaction):
        """List all guild roles"""
        await interaction.response.defer()
        
        try:
            # Get guild roles
            roles = await self.role_manager.get_guild_roles(interaction.guild_id)
            
            if not roles:
                await interaction.followup.send(
                    "📋 Роли для этого сервера не настроены.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title="🔧 Роли сервера",
                description=f"Настроено ролей: {len(roles)}",
                color=discord.Color.blue()
            )
            
            for role in roles:
                role_type_emoji = {
                    "players": "🎮",
                    "referees": "⚖️",
                    "admins": "👑",
                    "moderators": "🛡️",
                    "tournament_organizers": "🏆"
                }.get(role["type"], "❓")
                
                auto_assign_text = "✅" if role["auto_assign"] else "❌"
                
                embed.add_field(
                    name=f"{role_type_emoji} {role['name']}",
                    value=f"**Тип**: {role['type']}\n"
                          f"**ID**: {role['discord_role_id']}\n"
                          f"**Автоназначение**: {auto_assign_text}\n"
                          f"**Разрешения**: {len(role['permissions'])}",
                    inline=True
                )
            
            await interaction.followup.send(
                f"🔧 **Роли сервера**",
                embed=embed
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при загрузке ролей: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="setup_default_roles", description="Настроить роли по умолчанию")
    async def setup_default_roles(self, interaction: discord.Interaction):
        """Setup default roles for the guild"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для настройки ролей.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Setup default roles
            success = await self.role_manager.setup_default_roles(
                guild_id=interaction.guild_id,
                guild_name=interaction.guild.name
            )
            
            if success:
                await interaction.followup.send(
                    "✅ Роли по умолчанию успешно настроены!\n\n"
                    "**Созданные роли:**\n"
                    "🎮 **Игроки** - Автоматически назначается участникам\n"
                    "⚖️ **Судьи** - Для модерации матчей\n"
                    "👑 **Администраторы** - Управление системой\n"
                    "🏆 **Организаторы турниров** - Создание турниров\n\n"
                    "Теперь настройте Discord роли и укажите их ID.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Не удалось настроить роли по умолчанию.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при настройке ролей: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="test_role_tagging", description="Тест тегирования ролей")
    @app_commands.describe(
        event_type="Тип события для тестирования"
    )
    async def test_role_tagging(self, interaction: discord.Interaction, event_type: str):
        """Test role tagging for different events"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для тестирования.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Test role tagging
            tagged_message = await self.role_manager.tag_role_for_event(
                guild_id=interaction.guild_id,
                event_type=event_type,
                message="Это тестовое уведомление для проверки тегирования ролей."
            )
            
            await interaction.followup.send(
                f"🔔 **Тест тегирования ролей**\n\n"
                f"**Тип события**: {event_type}\n"
                f"**Результат**:\n{tagged_message}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при тестировании: {str(e)}",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Automatically setup default roles when bot joins a guild"""
        try:
            logger.info(f"Bot joined guild: {guild.name} (ID: {guild.id})")
            
            # Setup default roles
            await self.role_manager.setup_default_roles(
                guild_id=guild.id,
                guild_name=guild.name
            )
            
            # Send welcome message to system channel
            if guild.system_channel:
                embed = discord.Embed(
                    title="🎮 Discord Rating Bot присоединился к серверу!",
                    description="Бот автоматически настроил роли для рейтинговой системы.",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🔧 Следующие шаги:",
                    value="1. Создайте Discord роли для игроков, судей и администраторов\n"
                          "2. Используйте `/setup_default_roles` для настройки\n"
                          "3. Укажите ID созданных Discord ролей\n"
                          "4. Настройте автоматическое назначение ролей",
                    inline=False
                )
                
                embed.set_footer(text="Используйте /help для получения справки по командам")
                
                try:
                    await guild.system_channel.send(embed=embed)
                except discord.Forbidden:
                    logger.warning(f"Could not send welcome message to guild {guild.id}")
                    
        except Exception as e:
            logger.error(f"Error setting up guild {guild.id}: {e}")

async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(RoleManagement(bot))