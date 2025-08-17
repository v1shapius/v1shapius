import asyncio
import discord
from discord.ext import commands
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from database.database import DatabaseManager
from services.season_manager import SeasonManager
from services.security_service import SecurityService
from services.achievement_service import AchievementService
from services.tournament_service import TournamentService

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RatingBot(commands.Bot):
    """Main bot class for Discord Rating Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix=Config.BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.db_manager = None
        self.season_manager = None
        self.security_service = None
        self.achievement_service = None
        self.tournament_service = None
        self.locale = Config.DEFAULT_LOCALE
        
    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        logger.info("Setting up bot...")
        
        # Initialize database
        try:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
        # Load cogs
        await self.load_extension("cogs.match_management")
        await self.load_extension("cogs.rating_system")
        await self.load_extension("cogs.voice_control")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.draft_verification")
        await self.load_extension("cogs.referee_system")
        await self.load_extension("cogs.referee_management")
        await self.load_extension("cogs.achievements")
        await self.load_extension("cogs.tournaments")
        
        logger.info("All cogs loaded successfully")
        
        # Sync commands
        try:
            await self.tree.sync()
            logger.info("Application commands synced")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="rating matches & achievements"
            )
        )
        
        # Start background services
        try:
            # Start season manager service
            self.season_manager = SeasonManager(self)
            asyncio.create_task(self.season_manager.start_monitoring())
            logger.info("Season manager service started")
            
            # Start security service
            self.security_service = SecurityService(self)
            asyncio.create_task(self.security_service.start_monitoring())
            logger.info("Security service started")
            
            # Start achievement service
            self.achievement_service = AchievementService(self)
            asyncio.create_task(self.achievement_service.start_monitoring())
            logger.info("Achievement service started")
            
            # Start tournament service
            self.tournament_service = TournamentService(self)
            asyncio.create_task(self.tournament_service.start_monitoring())
            logger.info("Tournament service started")
            
        except Exception as e:
            logger.error(f"Failed to start background services: {e}")
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Initialize guild settings
        try:
            await self.db_manager.initialize_guild_settings(guild.id)
            logger.info(f"Initialized settings for guild: {guild.name}")
        except Exception as e:
            logger.error(f"Failed to initialize guild settings: {e}")
    
    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command.")
        else:
            logger.error(f"Unhandled command error: {error}")
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    async def on_member_join(self, member):
        """Called when a member joins a guild"""
        logger.info(f"Member {member.display_name} joined guild {member.guild.name}")
        
        # Check if member should be restricted due to security concerns
        if self.security_service:
            await self.security_service.check_new_member_security(member)
    
    async def on_member_remove(self, member):
        """Called when a member leaves a guild"""
        logger.info(f"Member {member.display_name} left guild {member.guild.name}")
        
        # Log member departure for security analysis
        if self.security_service:
            await self.security_service.log_member_departure(member)
    
    async def on_message(self, message):
        """Called when a message is sent"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Process commands
        await self.process_commands(message)
        
        # Check for achievement triggers
        if self.achievement_service:
            await self.achievement_service.check_message_triggers(message)
    
    async def on_reaction_add(self, reaction, user):
        """Called when a reaction is added"""
        if user.bot:
            return
        
        # Check for achievement triggers
        if self.achievement_service:
            await self.achievement_service.check_reaction_triggers(reaction, user)

async def main():
    """Main function to run the bot"""
    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Create and run bot
    bot = RatingBot()
    
    try:
        await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
    finally:
        # Cleanup
        if bot.db_manager:
            await bot.db_manager.close()
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())