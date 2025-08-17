from typing import Dict, Any
from .en import *
from .ru import *

class LocaleManager:
    """Manager for handling multiple language localizations"""
    
    def __init__(self):
        self.locales = {
            'en': {
                'MATCH_CREATION': MATCH_CREATION,
                'MATCH_STAGES': MATCH_STAGES,
                'DRAFT_VERIFICATION': DRAFT_VERIFICATION,
                'FIRST_PLAYER_SELECTION': FIRST_PLAYER_SELECTION,
                'GAME_PREPARATION': GAME_PREPARATION,
                'GAME_RESULTS': GAME_RESULTS,
                'MATCH_COMPLETION': MATCH_COMPLETION,
                'RATING_SYSTEM': RATING_SYSTEM,
                'ERRORS': ERRORS,
                'SUCCESS': SUCCESS,
                'BUTTONS': BUTTONS,
                'FORMATS': FORMATS,
                'STATUSES': STATUSES
            },
            'ru': {
                'MATCH_CREATION': MATCH_CREATION,
                'MATCH_STAGES': MATCH_STAGES,
                'DRAFT_VERIFICATION': DRAFT_VERIFICATION,
                'FIRST_PLAYER_SELECTION': FIRST_PLAYER_SELECTION,
                'GAME_PREPARATION': GAME_PREPARATION,
                'GAME_RESULTS': GAME_RESULTS,
                'MATCH_COMPLETION': MATCH_COMPLETION,
                'RATING_SYSTEM': RATING_SYSTEM,
                'ERRORS': ERRORS,
                'SUCCESS': SUCCESS,
                'BUTTONS': BUTTONS,
                'FORMATS': FORMATS,
                'STATUSES': STATUSES
            }
        }
        self.default_locale = 'en'
    
    def get_text(self, category: str, key: str, locale: str = 'en', **kwargs) -> str:
        """
        Get localized text with optional formatting
        
        Args:
            category: Text category (e.g., 'MATCH_CREATION')
            key: Text key within category
            locale: Language code
            **kwargs: Format parameters for string formatting
            
        Returns:
            Localized and formatted text
        """
        if locale not in self.locales:
            locale = self.default_locale
            
        if category not in self.locales[locale]:
            # Fallback to default locale
            if category in self.locales[self.default_locale]:
                text = self.locales[self.default_locale][category].get(key, key)
            else:
                return key
        else:
            text = self.locales[locale][category].get(key, key)
        
        # Apply string formatting if kwargs provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                # If formatting fails, return original text
                pass
                
        return text
    
    def get_button_text(self, button_key: str, locale: str = 'en') -> str:
        """Get localized button text"""
        return self.get_text('BUTTONS', button_key, locale)
    
    def get_format_name(self, format_key: str, locale: str = 'en') -> str:
        """Get localized format name"""
        return self.get_text('FORMATS', format_key, locale)
    
    def get_status_name(self, status_key: str, locale: str = 'en') -> str:
        """Get localized status name"""
        return self.get_text('STATUSES', status_key, locale)
    
    def get_error_text(self, error_key: str, locale: str = 'en', **kwargs) -> str:
        """Get localized error text"""
        return self.get_text('ERRORS', error_key, locale, **kwargs)
    
    def get_success_text(self, success_key: str, locale: str = 'en') -> str:
        """Get localized success text"""
        return self.get_text('SUCCESS', success_key, locale)

# Global instance
locale_manager = LocaleManager()

def get_text(category: str, key: str, locale: str = 'en', **kwargs) -> str:
    """Convenience function to get localized text"""
    return locale_manager.get_text(category, key, locale, **kwargs)