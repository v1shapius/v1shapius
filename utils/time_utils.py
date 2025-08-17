"""
Time utility functions for Discord Rating Bot
"""

import re
from typing import Tuple, Optional

def parse_time_string(time_str: str) -> Optional[float]:
    """
    Parse time string in MM:SS format to seconds
    
    Args:
        time_str: Time string in MM:SS format (e.g., "05:30")
        
    Returns:
        Time in seconds as float, or None if invalid format
    """
    try:
        # Match MM:SS format
        pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(pattern, time_str)
        
        if not match:
            return None
        
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        
        # Validate ranges
        if minutes < 0 or minutes > 59:
            return None
        if seconds < 0 or seconds > 59:
            return None
        
        return minutes * 60 + seconds
        
    except (ValueError, TypeError):
        return None

def format_time_seconds(seconds: float) -> str:
    """
    Format seconds to MM:SS string
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string in MM:SS format
    """
    try:
        total_seconds = int(seconds)
        minutes = total_seconds // 60
        remaining_seconds = total_seconds % 60
        
        return f"{minutes:02d}:{remaining_seconds:02d}"
        
    except (ValueError, TypeError):
        return "00:00"

def parse_extended_time_string(time_str: str) -> Optional[float]:
    """
    Parse extended time string in HH:MM:SS format to seconds
    
    Args:
        time_str: Time string in HH:MM:SS format (e.g., "01:05:30")
        
    Returns:
        Time in seconds as float, or None if invalid format
    """
    try:
        # Match HH:MM:SS format
        pattern = r'^(\d{1,2}):(\d{2}):(\d{2})$'
        match = re.match(pattern, time_str)
        
        if not match:
            return None
        
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        
        # Validate ranges
        if hours < 0 or hours > 23:
            return None
        if minutes < 0 or minutes > 59:
            return None
        if seconds < 0 or seconds > 59:
            return None
        
        return hours * 3600 + minutes * 60 + seconds
        
    except (ValueError, TypeError):
        return None

def format_time_seconds_extended(seconds: float) -> str:
    """
    Format seconds to HH:MM:SS string
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string in HH:MM:SS format
    """
    try:
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        remaining_seconds = total_seconds % 3600
        minutes = remaining_seconds // 60
        final_seconds = remaining_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{final_seconds:02d}"
        else:
            return f"{minutes:02d}:{final_seconds:02d}"
        
    except (ValueError, TypeError):
        return "00:00"

def add_time_penalties(base_time: float, restart_count: int, penalty_per_restart: float) -> float:
    """
    Calculate final time with penalties
    
    Args:
        base_time: Base completion time in seconds
        restart_count: Number of restarts
        penalty_per_restart: Penalty time per restart in seconds
        
    Returns:
        Final time with penalties
    """
    try:
        penalties = restart_count * penalty_per_restart
        return base_time + penalties
        
    except (ValueError, TypeError):
        return base_time

def is_valid_time_range(time_seconds: float, min_time: float = 0, max_time: float = 3600) -> bool:
    """
    Check if time is within valid range
    
    Args:
        time_seconds: Time to check in seconds
        min_time: Minimum valid time in seconds
        max_time: Maximum valid time in seconds
        
    Returns:
        True if time is within range, False otherwise
    """
    try:
        return min_time <= time_seconds <= max_time
        
    except (ValueError, TypeError):
        return False