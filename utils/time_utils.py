"""
Time utility functions for Discord Rating Bot
"""

import re
from typing import Optional, Tuple

def parse_time(time_str: str) -> Optional[int]:
    """
    Parse time string in MM:SS or HH:MM:SS format to seconds
    
    Args:
        time_str: Time string (e.g., "1:30", "2:15:45")
        
    Returns:
        Time in seconds or None if invalid
    """
    try:
        # Remove any whitespace
        time_str = time_str.strip()
        
        # Check if it's MM:SS format
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            minutes, seconds = map(int, time_str.split(':'))
            if seconds >= 60:
                return None
            return minutes * 60 + seconds
        
        # Check if it's HH:MM:SS format
        elif re.match(r'^\d{1,2}:\d{2}:\d{2}$', time_str):
            hours, minutes, seconds = map(int, time_str.split(':'))
            if minutes >= 60 or seconds >= 60:
                return None
            return hours * 3600 + minutes * 60 + seconds
        
        # Check if it's just seconds
        elif re.match(r'^\d+$', time_str):
            return int(time_str)
        
        return None
        
    except (ValueError, AttributeError):
        return None

def format_time(seconds: int) -> str:
    """
    Format seconds to MM:SS or HH:MM:SS format
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"0:{seconds:02d}"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"

def calculate_penalty(restart_count: int, penalty_settings) -> int:
    """
    Calculate penalty time based on restart count using detailed penalty system
    
    Args:
        restart_count: Number of restarts
        penalty_settings: PenaltySettings instance with detailed configuration
        
    Returns:
        Total penalty time in seconds
    """
    if not penalty_settings or restart_count <= 0:
        return 0
    
    # Use detailed penalty system if available
    if hasattr(penalty_settings, 'calculate_total_penalty'):
        return penalty_settings.calculate_total_penalty(restart_count)
    
    # Fallback to legacy simple penalty
    return restart_count * penalty_settings.restart_penalty

def calculate_final_time(completion_time: int, restart_count: int, penalty_settings) -> int:
    """
    Calculate final time including penalties
    
    Args:
        completion_time: Raw completion time in seconds
        restart_count: Number of restarts
        penalty_settings: PenaltySettings instance
        
    Returns:
        Final time with penalties in seconds
    """
    penalty = calculate_penalty(restart_count, penalty_settings)
    return completion_time + penalty

def validate_time_range(seconds: int, min_seconds: int = 1, max_seconds: int = 86400) -> bool:
    """
    Validate if time is within acceptable range
    
    Args:
        seconds: Time in seconds
        min_seconds: Minimum allowed time (default: 1 second)
        max_seconds: Maximum allowed time (default: 24 hours)
        
    Returns:
        True if valid, False otherwise
    """
    return min_seconds <= seconds <= max_seconds

def parse_time_with_validation(time_str: str, min_seconds: int = 1, max_seconds: int = 86400) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse time string with validation
    
    Args:
        time_str: Time string to parse
        min_seconds: Minimum allowed time
        max_seconds: Maximum allowed time
        
    Returns:
        Tuple of (parsed_seconds, error_message)
    """
    parsed_time = parse_time(time_str)
    
    if parsed_time is None:
        return None, "Неверный формат времени. Используйте MM:SS или HH:MM:SS"
    
    if not validate_time_range(parsed_time, min_seconds, max_seconds):
        return None, f"Время должно быть от {format_time(min_seconds)} до {format_time(max_seconds)}"
    
    return parsed_time, None

def format_penalty_breakdown(restart_count: int, penalty_settings) -> str:
    """
    Format penalty breakdown for display
    
    Args:
        restart_count: Number of restarts
        penalty_settings: PenaltySettings instance
        
    Returns:
        Formatted penalty breakdown string
    """
    if restart_count <= 0:
        return "Нет рестартов"
    
    if not penalty_settings:
        return f"Штраф: {restart_count} рестартов"
    
    # Use detailed penalty system if available
    if hasattr(penalty_settings, 'restart_penalties'):
        penalties = penalty_settings.restart_penalties
        free_restarts = penalties.get("free_restarts", 0)
        
        if restart_count <= free_restarts:
            return f"Бесплатные рестарты: {restart_count}/{free_restarts}"
        
        breakdown = []
        total_penalty = 0
        
        for i in range(1, restart_count + 1):
            penalty = penalty_settings.get_penalty_for_restart(i)
            if penalty > 0:
                breakdown.append(f"{i}-й: +{penalty}с")
                total_penalty += penalty
        
        if breakdown:
            return f"Штраф: {' + '.join(breakdown)} = +{total_penalty}с"
        else:
            return f"Бесплатные рестарты: {restart_count}/{free_restarts}"
    
    # Fallback to simple penalty
    total_penalty = restart_count * penalty_settings.restart_penalty
    return f"Штраф: {restart_count} × {penalty_settings.restart_penalty}с = +{total_penalty}с"