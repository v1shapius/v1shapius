from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import json

Base = declarative_base()

class RoleType(str, Enum):
    """Types of guild roles"""
    PLAYERS = "players"
    REFEREES = "referees"
    ADMINS = "admins"
    MODERATORS = "moderators"
    TOURNAMENT_ORGANIZERS = "tournament_organizers"

class GuildRoles(Base):
    """Model for guild role configuration"""
    
    __tablename__ = 'guild_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False, index=True)
    role_type = Column(String(50), nullable=False)  # RoleType enum value
    discord_role_id = Column(Integer, nullable=False)
    role_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_assign = Column(Boolean, default=False, nullable=False)  # Auto-assign to new members
    permissions = Column(Text, nullable=True)  # JSON string of permissions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    guild = relationship("Guild", back_populates="roles")
    
    def __repr__(self):
        return f"<GuildRoles(guild_id={self.guild_id}, type={self.role_type}, name='{self.role_name}')>"
    
    @property
    def permissions_dict(self):
        """Get permissions as dictionary"""
        if self.permissions:
            try:
                return json.loads(self.permissions)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @permissions_dict.setter
    def permissions_dict(self, value):
        """Set permissions from dictionary"""
        if isinstance(value, dict):
            self.permissions = json.dumps(value)
        else:
            self.permissions = None
    
    def has_permission(self, permission: str) -> bool:
        """Check if role has specific permission"""
        perms = self.permissions_dict
        return perms.get(permission, False)
    
    def add_permission(self, permission: str):
        """Add permission to role"""
        perms = self.permissions_dict
        perms[permission] = True
        self.permissions_dict = perms
    
    def remove_permission(self, permission: str):
        """Remove permission from role"""
        perms = self.permissions_dict
        if permission in perms:
            del perms[permission]
        self.permissions_dict = perms

class GuildRolePermissions(Base):
    """Model for guild role permissions"""
    
    __tablename__ = 'guild_role_permissions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False, index=True)
    role_type = Column(String(50), nullable=False)
    permission_name = Column(String(100), nullable=False)
    permission_description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<GuildRolePermissions(guild_id={self.guild_id}, type={self.role_type}, permission='{self.permission_name}')>"

class Guild(Base):
    """Model for guild configuration"""
    
    __tablename__ = 'guilds'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False, unique=True, index=True)
    guild_name = Column(String(255), nullable=False)
    prefix = Column(String(10), default='!', nullable=False)
    language = Column(String(10), default='ru', nullable=False)
    timezone = Column(String(50), default='UTC', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    roles = relationship("GuildRoles", back_populates="guild")
    
    def __repr__(self):
        return f"<Guild(guild_id={self.guild_id}, name='{self.guild_name}')>"
    
    def get_role_by_type(self, role_type: RoleType) -> 'GuildRoles':
        """Get role configuration by type"""
        for role in self.roles:
            if role.role_type == role_type.value and role.is_active:
                return role
        return None
    
    def has_role_type(self, role_type: RoleType) -> bool:
        """Check if guild has role of specific type"""
        return self.get_role_by_type(role_type) is not None

# Permission constants
class Permissions:
    """Standard permissions for roles"""
    
    # Player permissions
    PLAYER_CAN_CHALLENGE = "can_challenge"
    PLAYER_CAN_JOIN_TOURNAMENTS = "can_join_tournaments"
    PLAYER_CAN_VIEW_STATS = "can_view_stats"
    PLAYER_CAN_VIEW_LEADERBOARD = "can_view_leaderboard"
    
    # Referee permissions
    REFEREE_CAN_MODERATE_MATCHES = "can_moderate_matches"
    REFEREE_CAN_RESOLVE_DISPUTES = "can_resolve_disputes"
    REFEREE_CAN_ANNOUNCE_RESULTS = "can_announce_results"
    REFEREE_CAN_VIEW_ADMIN_PANEL = "can_view_admin_panel"
    
    # Admin permissions
    ADMIN_CAN_MANAGE_SEASONS = "can_manage_seasons"
    ADMIN_CAN_MANAGE_TOURNAMENTS = "can_manage_tournaments"
    ADMIN_CAN_MANAGE_ROLES = "can_manage_roles"
    ADMIN_CAN_VIEW_SECURITY_LOGS = "can_view_security_logs"
    
    # Tournament organizer permissions
    TOURNAMENT_ORGANIZER_CAN_CREATE = "can_create_tournaments"
    TOURNAMENT_ORGANIZER_CAN_MANAGE = "can_manage_tournaments"
    TOURNAMENT_ORGANIZER_CAN_ANNOUNCE = "can_announce_results"

# Default role configurations
DEFAULT_ROLE_CONFIGS = {
    RoleType.PLAYERS: {
        "permissions": [
            Permissions.PLAYER_CAN_CHALLENGE,
            Permissions.PLAYER_CAN_JOIN_TOURNAMENTS,
            Permissions.PLAYER_CAN_VIEW_STATS,
            Permissions.PLAYER_CAN_VIEW_LEADERBOARD
        ],
        "auto_assign": True,
        "description": "Роль для игроков рейтинговой системы"
    },
    RoleType.REFEREES: {
        "permissions": [
            Permissions.REFEREE_CAN_MODERATE_MATCHES,
            Permissions.REFEREE_CAN_RESOLVE_DISPUTES,
            Permissions.REFEREE_CAN_ANNOUNCE_RESULTS,
            Permissions.REFEREE_CAN_VIEW_ADMIN_PANEL
        ],
        "auto_assign": False,
        "description": "Роль для судей матчей"
    },
    RoleType.ADMINS: {
        "permissions": [
            Permissions.ADMIN_CAN_MANAGE_SEASONS,
            Permissions.ADMIN_CAN_MANAGE_TOURNAMENTS,
            Permissions.ADMIN_CAN_MANAGE_ROLES,
            Permissions.ADMIN_CAN_VIEW_SECURITY_LOGS
        ],
        "auto_assign": False,
        "description": "Роль администратора сервера"
    },
    RoleType.TOURNAMENT_ORGANIZERS: {
        "permissions": [
            Permissions.TOURNAMENT_ORGANIZER_CAN_CREATE,
            Permissions.TOURNAMENT_ORGANIZER_CAN_MANAGE,
            Permissions.TOURNAMENT_ORGANIZER_CAN_ANNOUNCE
        ],
        "auto_assign": False,
        "description": "Роль организатора турниров"
    }
}