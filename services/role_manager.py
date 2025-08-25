import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, and_, or_, func
from database.database import DatabaseManager
from models.guild_roles import GuildRoles, RoleType, Guild, DEFAULT_ROLE_CONFIGS, Permissions
from config.config import Config
import discord

logger = logging.getLogger(__name__)

class RoleManager:
    """Service for managing guild roles and automatic role assignment"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.check_interval = Config.ROLE_CHECK_INTERVAL if hasattr(Config, 'ROLE_CHECK_INTERVAL') else 300
        
    async def start_monitoring(self):
        """Start the role monitoring loop"""
        logger.info("Starting role management service")
        while True:
            try:
                await self.check_role_assignments()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in role monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_role_assignments(self):
        """Check and assign roles to new members"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get all active guilds
                guilds = await session.execute(
                    select(Guild).where(Guild.is_active == True)
                )
                guilds = guilds.fetchall()
                
                for guild in guilds:
                    await self.check_guild_role_assignments(session, guild)
                    
        except Exception as e:
            logger.error(f"Error checking role assignments: {e}")
    
    async def check_guild_role_assignments(self, session, guild):
        """Check role assignments for a specific guild"""
        try:
            # Get auto-assign roles for this guild
            auto_assign_roles = await session.execute(
                select(GuildRoles).where(
                    and_(
                        GuildRoles.guild_id == guild.guild_id,
                        GuildRoles.is_active == True,
                        GuildRoles.auto_assign == True
                    )
                )
            )
            auto_assign_roles = auto_assign_roles.fetchall()
            
            if not auto_assign_roles:
                return
            
            # Get Discord guild object
            discord_guild = self.bot.get_guild(guild.guild_id)
            if not discord_guild:
                logger.warning(f"Could not find Discord guild: {guild.guild_id}")
                return
            
            # Check each member for missing auto-assign roles
            for member in discord_guild.members:
                if member.bot:
                    continue
                
                await self.assign_auto_roles(session, guild, member, auto_assign_roles)
                
        except Exception as e:
            logger.error(f"Error checking guild role assignments for {guild.guild_id}: {e}")
    
    async def assign_auto_roles(self, session, guild, member, auto_assign_roles):
        """Assign auto-assign roles to a member"""
        try:
            for role_config in auto_assign_roles:
                # Check if member already has this role
                discord_role = member.guild.get_role(role_config.discord_role_id)
                if not discord_role:
                    logger.warning(f"Could not find Discord role: {role_config.discord_role_id}")
                    continue
                
                if discord_role in member.roles:
                    continue  # Member already has this role
                
                # Check if member meets requirements for this role
                if await self.member_meets_role_requirements(session, guild, member, role_config):
                    try:
                        await member.add_roles(discord_role, reason="Auto-assign role")
                        logger.info(f"Auto-assigned role {role_config.role_name} to {member.display_name}")
                    except discord.Forbidden:
                        logger.warning(f"Bot lacks permission to assign role {role_config.role_name}")
                    except Exception as e:
                        logger.error(f"Error assigning role {role_config.role_name}: {e}")
                        
        except Exception as e:
            logger.error(f"Error assigning auto roles to {member.display_name}: {e}")
    
    async def member_meets_role_requirements(self, session, guild, member, role_config) -> bool:
        """Check if member meets requirements for a role"""
        try:
            if role_config.role_type == RoleType.PLAYERS.value:
                # Players need to have played at least one match
                match_count = await session.execute(
                    """
                    SELECT COUNT(*) FROM matches m
                    JOIN players p ON (m.player1_id = p.id OR m.player2_id = p.id)
                    WHERE p.discord_id = :discord_id AND m.status = 'complete'
                    """,
                    {"discord_id": member.id}
                )
                match_count = match_count.scalar_one_or_none()
                return match_count and match_count > 0
                
            elif role_config.role_type == RoleType.REFEREES.value:
                # Referees need to be manually assigned by admins
                return False
                
            elif role_config.role_type == RoleType.ADMINS.value:
                # Admins need Discord administrator permission
                return member.guild_permissions.administrator
                
            elif role_config.role_type == RoleType.TOURNAMENT_ORGANIZERS.value:
                # Tournament organizers need to be manually assigned
                return False
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking role requirements: {e}")
            return False
    
    async def tag_role_for_event(self, guild_id: int, event_type: str, message: str = "") -> str:
        """Tag appropriate role for different events"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get guild role configuration
                guild_roles = await session.execute(
                    select(GuildRoles).where(
                        and_(
                            GuildRoles.guild_id == guild_id,
                            GuildRoles.is_active == True
                        )
                    )
                )
                guild_roles = guild_roles.fetchall()
                
                if not guild_roles:
                    return message
                
                # Determine which role to tag based on event type
                role_to_tag = None
                
                if event_type in ["referee_needed", "dispute_resolution", "match_moderation"]:
                    # Tag referees
                    role_to_tag = next(
                        (role for role in guild_roles if role.role_type == RoleType.REFEREES.value),
                        None
                    )
                    
                elif event_type in ["season_start", "season_end", "tournament_start", "tournament_end"]:
                    # Tag players
                    role_to_tag = next(
                        (role for role in guild_roles if role.role_type == RoleType.PLAYERS.value),
                        None
                    )
                    
                elif event_type in ["admin_notification", "security_alert"]:
                    # Tag admins
                    role_to_tag = next(
                        (role for role in guild_roles if role.role_type == RoleType.ADMINS.value),
                        None
                    )
                
                if role_to_tag:
                    # Create Discord role mention
                    role_mention = f"<@&{role_to_tag.discord_role_id}>"
                    
                    if message:
                        return f"{role_mention} {message}"
                    else:
                        return role_mention
                
                return message
                
        except Exception as e:
            logger.error(f"Error tagging role for event: {e}")
            return message
    
    async def get_guild_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all roles for a guild"""
        try:
            session = await self.db.get_session()
        async with session:
                roles = await session.execute(
                    select(GuildRoles).where(
                        and_(
                            GuildRoles.guild_id == guild_id,
                            GuildRoles.is_active == True
                        )
                    )
                )
                roles = roles.fetchall()
                
                result = []
                for role in roles:
                    result.append({
                        "id": role.id,
                        "type": role.role_type,
                        "discord_role_id": role.discord_role_id,
                        "name": role.role_name,
                        "description": role.description,
                        "auto_assign": role.auto_assign,
                        "permissions": role.permissions_dict,
                        "created_at": role.created_at,
                        "updated_at": role.updated_at
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting guild roles: {e}")
            return []
    
    async def create_guild_role(self, guild_id: int, role_type: RoleType, discord_role_id: int, 
                               role_name: str, description: str = None, auto_assign: bool = False) -> Optional[GuildRoles]:
        """Create a new guild role configuration"""
        try:
            session = await self.db.get_session()
        async with session:
                # Check if role already exists
                existing_role = await session.execute(
                    select(GuildRoles).where(
                        and_(
                            GuildRoles.guild_id == guild_id,
                            GuildRoles.role_type == role_type.value
                        )
                    )
                )
                existing_role = existing_role.scalar_one_or_none()
                
                if existing_role:
                    logger.warning(f"Role {role_type.value} already exists for guild {guild_id}")
                    return None
                
                # Create new role
                role = GuildRoles(
                    guild_id=guild_id,
                    role_type=role_type.value,
                    discord_role_id=discord_role_id,
                    role_name=role_name,
                    description=description,
                    auto_assign=auto_assign
                )
                
                # Set default permissions
                if role_type in DEFAULT_ROLE_CONFIGS:
                    default_config = DEFAULT_ROLE_CONFIGS[role_type]
                    role.permissions_dict = {perm: True for perm in default_config["permissions"]}
                
                session.add(role)
                await session.commit()
                
                logger.info(f"Created role {role_name} for guild {guild_id}")
                return role
                
        except Exception as e:
            logger.error(f"Error creating guild role: {e}")
            return None
    
    async def update_guild_role(self, role_id: int, **kwargs) -> bool:
        """Update a guild role configuration"""
        try:
            session = await self.db.get_session()
        async with session:
                role = await session.execute(
                    select(GuildRoles).where(GuildRoles.id == role_id)
                )
                role = role.scalar_one_or_none()
                
                if not role:
                    logger.warning(f"Role {role_id} not found")
                    return False
                
                # Update fields
                for key, value in kwargs.items():
                    if hasattr(role, key):
                        setattr(role, key, value)
                
                role.updated_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"Updated role {role.role_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating guild role: {e}")
            return False
    
    async def delete_guild_role(self, role_id: int) -> bool:
        """Delete a guild role configuration"""
        try:
            session = await self.db.get_session()
        async with session:
                role = await session.execute(
                    select(GuildRoles).where(GuildRoles.id == role_id)
                )
                role = role.scalar_one_or_none()
                
                if not role:
                    logger.warning(f"Role {role_id} not found")
                    return False
                
                # Soft delete - mark as inactive
                role.is_active = False
                await session.commit()
                
                logger.info(f"Deleted role {role.role_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting guild role: {e}")
            return False
    
    async def assign_role_to_member(self, guild_id: int, member_id: int, role_type: RoleType) -> bool:
        """Manually assign a role to a member"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get role configuration
                role = await session.execute(
                    select(GuildRoles).where(
                        and_(
                            GuildRoles.guild_id == guild_id,
                            GuildRoles.role_type == role_type.value,
                            GuildRoles.is_active == True
                        )
                    )
                )
                role = role.scalar_one_or_none()
                
                if not role:
                    logger.warning(f"Role {role_type.value} not found for guild {guild_id}")
                    return False
                
                # Get Discord guild and member
                discord_guild = self.bot.get_guild(guild_id)
                if not discord_guild:
                    logger.warning(f"Could not find Discord guild: {guild_id}")
                    return False
                
                member = discord_guild.get_member(member_id)
                if not member:
                    logger.warning(f"Could not find Discord member: {member_id}")
                    return False
                
                # Get Discord role
                discord_role = discord_guild.get_role(role.discord_role_id)
                if not discord_role:
                    logger.warning(f"Could not find Discord role: {role.discord_role_id}")
                    return False
                
                # Assign role
                await member.add_roles(discord_role, reason="Manual role assignment")
                logger.info(f"Assigned role {role.role_name} to {member.display_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error assigning role to member: {e}")
            return False
    
    async def remove_role_from_member(self, guild_id: int, member_id: int, role_type: RoleType) -> bool:
        """Remove a role from a member"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get role configuration
                role = await session.execute(
                    select(GuildRoles).where(
                        and_(
                            GuildRoles.guild_id == guild_id,
                            GuildRoles.role_type == role_type.value,
                            GuildRoles.is_active == True
                        )
                    )
                )
                role = role.scalar_one_or_none()
                
                if not role:
                    logger.warning(f"Role {role_type.value} not found for guild {guild_id}")
                    return False
                
                # Get Discord guild and member
                discord_guild = self.bot.get_guild(guild_id)
                if not discord_guild:
                    logger.warning(f"Could not find Discord guild: {guild_id}")
                    return False
                
                member = discord_guild.get_member(member_id)
                if not member:
                    logger.warning(f"Could not find Discord member: {member_id}")
                    return False
                
                # Get Discord role
                discord_role = discord_guild.get_role(role.discord_role_id)
                if not discord_role:
                    logger.warning(f"Could not find Discord role: {role.discord_role_id}")
                    return False
                
                # Remove role
                await member.remove_roles(discord_role, reason="Manual role removal")
                logger.info(f"Removed role {role.role_name} from {member.display_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error removing role from member: {e}")
            return False
    
    async def check_member_permissions(self, guild_id: int, member_id: int, permission: str) -> bool:
        """Check if a member has a specific permission"""
        try:
            session = await self.db.get_session()
        async with session:
                # Get member's roles
                member_roles = await session.execute(
                    """
                    SELECT gr.* FROM guild_roles gr
                    JOIN guild_member_roles gmr ON gr.id = gmr.role_id
                    WHERE gr.guild_id = :guild_id AND gmr.member_id = :member_id
                    AND gr.is_active = True
                    """,
                    {"guild_id": guild_id, "member_id": member_id}
                )
                member_roles = member_roles.fetchall()
                
                # Check if any role has the permission
                for role in member_roles:
                    if role.has_permission(permission):
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking member permissions: {e}")
            return False
    
    async def setup_default_roles(self, guild_id: int, guild_name: str) -> bool:
        """Setup default roles for a new guild"""
        try:
            session = await self.db.get_session()
        async with session:
                # Check if guild already exists
                existing_guild = await session.execute(
                    select(Guild).where(Guild.guild_id == guild_id)
                )
                existing_guild = existing_guild.scalar_one_or_none()
                
                if not existing_guild:
                    # Create guild record
                    guild = Guild(
                        guild_id=guild_id,
                        guild_name=guild_name
                    )
                    session.add(guild)
                    await session.commit()
                
                # Create default roles
                for role_type, config in DEFAULT_ROLE_CONFIGS.items():
                    await self.create_guild_role(
                        guild_id=guild_id,
                        role_type=role_type,
                        discord_role_id=0,  # Will be set later
                        role_name=config["description"],
                        description=config["description"],
                        auto_assign=config["auto_assign"]
                    )
                
                logger.info(f"Setup default roles for guild {guild_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting up default roles: {e}")
            return False