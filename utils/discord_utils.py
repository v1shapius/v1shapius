"""
Discord utility functions for Discord Rating Bot
"""

import discord
from typing import Optional, Union
from .validation import validate_discord_id

def get_member_display_name(member: discord.Member) -> str:
    """
    Get the display name of a Discord member
    
    Args:
        member: Discord member object
        
    Returns:
        Display name or username if display name is not set
    """
    try:
        if member.display_name and member.display_name != member.name:
            return member.display_name
        return member.name
    except (AttributeError, TypeError):
        return "Unknown User"

def check_member_permissions(member: discord.Member, required_permissions: list) -> bool:
    """
    Check if a member has required permissions
    
    Args:
        member: Discord member object
        required_permissions: List of required permission names
        
    Returns:
        True if member has all required permissions, False otherwise
    """
    try:
        if not member or not member.guild_permissions:
            return False
        
        member_permissions = member.guild_permissions
        
        for permission_name in required_permissions:
            if not hasattr(member_permissions, permission_name):
                continue
            
            permission_value = getattr(member_permissions, permission_name)
            if not permission_value:
                return False
        
        return True
        
    except (AttributeError, TypeError):
        return False

def get_guild_from_context(context) -> Optional[discord.Guild]:
    """
    Extract guild from various context types
    
    Args:
        context: Discord context (interaction, message, etc.)
        
    Returns:
        Guild object or None if not found
    """
    try:
        if hasattr(context, 'guild'):
            return context.guild
        elif hasattr(context, 'channel') and hasattr(context.channel, 'guild'):
            return context.channel.guild
        elif hasattr(context, 'interaction') and hasattr(context.interaction, 'guild'):
            return context.interaction.guild
        return None
        
    except (AttributeError, TypeError):
        return None

def get_channel_from_context(context) -> Optional[Union[discord.TextChannel, discord.VoiceChannel]]:
    """
    Extract channel from various context types
    
    Args:
        context: Discord context (interaction, message, etc.)
        
    Returns:
        Channel object or None if not found
    """
    try:
        if hasattr(context, 'channel'):
            return context.channel
        elif hasattr(context, 'interaction') and hasattr(context.interaction, 'channel'):
            return context.interaction.channel
        return None
        
    except (AttributeError, TypeError):
        return None

def get_user_from_context(context) -> Optional[Union[discord.Member, discord.User]]:
    """
    Extract user from various context types
    
    Args:
        context: Discord context (interaction, message, etc.)
        
    Returns:
        User/Member object or None if not found
    """
    try:
        if hasattr(context, 'author'):
            return context.author
        elif hasattr(context, 'user'):
            return context.user
        elif hasattr(context, 'interaction') and hasattr(context.interaction, 'user'):
            return context.interaction.user
        return None
        
    except (AttributeError, TypeError):
        return None

def is_member_in_voice_channel(member: discord.Member, voice_channel: discord.VoiceChannel) -> bool:
    """
    Check if a member is in a specific voice channel
    
    Args:
        member: Discord member object
        voice_channel: Voice channel to check
        
    Returns:
        True if member is in the channel, False otherwise
    """
    try:
        if not member.voice:
            return False
        
        return member.voice.channel == voice_channel
        
    except (AttributeError, TypeError):
        return False

def get_member_voice_state(member: discord.Member) -> Optional[discord.VoiceState]:
    """
    Get voice state of a member
    
    Args:
        member: Discord member object
        
    Returns:
        Voice state object or None if not in voice
    """
    try:
        return member.voice
    except (AttributeError, TypeError):
        return None

def is_member_streaming(member: discord.Member) -> bool:
    """
    Check if a member is currently streaming
    
    Args:
        member: Discord member object
        
    Returns:
        True if streaming, False otherwise
    """
    try:
        if not member.voice:
            return False
        
        return member.voice.self_stream or member.voice.self_video
        
    except (AttributeError, TypeError):
        return False

def can_member_manage_channels(member: discord.Member) -> bool:
    """
    Check if a member can manage channels
    
    Args:
        member: Discord member object
        
    Returns:
        True if can manage channels, False otherwise
    """
    return check_member_permissions(member, ['manage_channels'])

def can_member_manage_guild(member: discord.Member) -> bool:
    """
    Check if a member can manage the guild
    
    Args:
        member: Discord member object
        
    Returns:
        True if can manage guild, False otherwise
    """
    return check_member_permissions(member, ['administrator'])

def get_guild_member(guild: discord.Guild, user_id: Union[str, int]) -> Optional[discord.Member]:
    """
    Get a guild member by user ID
    
    Args:
        guild: Discord guild object
        user_id: User ID to look up
        
    Returns:
        Member object or None if not found
    """
    try:
        if not validate_discord_id(user_id):
            return None
        
        return guild.get_member(int(user_id))
        
    except (ValueError, TypeError):
        return None

def create_embed(title: str, description: str = "", color: int = 0x00ff00) -> discord.Embed:
    """
    Create a Discord embed with common formatting
    
    Args:
        title: Embed title
        description: Embed description
        color: Embed color (hex)
        
    Returns:
        Formatted Discord embed
    """
    try:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Add footer
        embed.set_footer(text="Discord Rating Bot")
        
        return embed
        
    except Exception:
        # Fallback to basic embed
        return discord.Embed(title=title, description=description, color=color)

def add_embed_field(embed: discord.Embed, name: str, value: str, inline: bool = True) -> discord.Embed:
    """
    Safely add a field to an embed
    
    Args:
        embed: Discord embed object
        name: Field name
        value: Field value
        inline: Whether field should be inline
        
    Returns:
        Updated embed
    """
    try:
        # Truncate if too long
        if len(name) > 256:
            name = name[:253] + "..."
        
        if len(value) > 1024:
            value = value[:1021] + "..."
        
        embed.add_field(name=name, value=value, inline=inline)
        
    except Exception as e:
        # Log error but don't fail
        print(f"Error adding embed field: {e}")
    
    return embed

def format_user_mention(user_id: Union[str, int]) -> str:
    """
    Format a user ID as a Discord mention
    
    Args:
        user_id: User ID to format
        
    Returns:
        Formatted mention string
    """
    try:
        if validate_discord_id(user_id):
            return f"<@{user_id}>"
        return f"User {user_id}"
        
    except (ValueError, TypeError):
        return f"User {user_id}"

def format_channel_mention(channel_id: Union[str, int]) -> str:
    """
    Format a channel ID as a Discord mention
    
    Args:
        channel_id: Channel ID to format
        
    Returns:
        Formatted mention string
    """
    try:
        if validate_discord_id(channel_id):
            return f"<#{channel_id}>"
        return f"Channel {channel_id}"
        
    except (ValueError, TypeError):
        return f"Channel {channel_id}"