"""
Validation utility functions for Discord Rating Bot
"""

import re
from typing import Optional, Union

def validate_discord_id(discord_id: Union[str, int]) -> bool:
    """
    Validate Discord ID format
    
    Args:
        discord_id: Discord ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Convert to string and check if it's a valid Discord ID
        id_str = str(discord_id)
        
        # Discord IDs are 17-19 digit numbers
        if not re.match(r'^\d{17,19}$', id_str):
            return False
        
        # Check if it's not all zeros
        if id_str == '0' * len(id_str):
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def validate_time_format(time_str: str) -> bool:
    """
    Validate time format (MM:SS)
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    try:
        # Check MM:SS format
        pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(pattern, time_str)
        
        if not match:
            return False
        
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        
        # Validate ranges
        if minutes < 0 or minutes > 59:
            return False
        if seconds < 0 or seconds > 59:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def validate_restart_count(count: Union[str, int]) -> bool:
    """
    Validate restart count
    
    Args:
        count: Restart count to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        count_int = int(count)
        return 0 <= count_int <= 100  # Reasonable upper limit
        
    except (ValueError, TypeError):
        return False

def validate_match_format(format_str: str) -> bool:
    """
    Validate match format
    
    Args:
        format_str: Format string to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_formats = ['bo1', 'bo2', 'bo3']
    return format_str.lower() in valid_formats

def validate_draft_link(link: str) -> bool:
    """
    Validate draft link format
    
    Args:
        link: Link to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(link))
        
    except (ValueError, TypeError):
        return False

def validate_rating_value(rating: Union[str, int, float]) -> bool:
    """
    Validate rating value
    
    Args:
        rating: Rating value to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        rating_float = float(rating)
        # Rating should be positive and reasonable
        return 0 <= rating_float <= 3000
        
    except (ValueError, TypeError):
        return False

def validate_season_name(name: str) -> bool:
    """
    Validate season name
    
    Args:
        name: Season name to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Season name should not be empty and reasonable length
        if not name or len(name.strip()) == 0:
            return False
        
        if len(name.strip()) > 100:
            return False
        
        # Should not contain only whitespace
        if name.strip() == '':
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def validate_penalty_settings(penalty_seconds: Union[str, int, float], max_restarts: Union[str, int]) -> bool:
    """
    Validate penalty settings
    
    Args:
        penalty_seconds: Penalty time per restart in seconds
        max_restarts: Maximum restarts before penalty
        
    Returns:
        True if valid, False otherwise
    """
    try:
        penalty_float = float(penalty_seconds)
        max_restarts_int = int(max_restarts)
        
        # Penalty should be reasonable
        if penalty_float < 0 or penalty_float > 300:  # Max 5 minutes penalty
            return False
        
        # Max restarts should be reasonable
        if max_restarts_int < 0 or max_restarts_int > 50:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    try:
        if not input_str:
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
        
    except (ValueError, TypeError):
        return ""

def validate_guild_id(guild_id: Union[str, int]) -> bool:
    """
    Validate Discord guild ID
    
    Args:
        guild_id: Guild ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return validate_discord_id(guild_id)

def validate_channel_id(channel_id: Union[str, int]) -> bool:
    """
    Validate Discord channel ID
    
    Args:
        channel_id: Channel ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return validate_discord_id(channel_id)