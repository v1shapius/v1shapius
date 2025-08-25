import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from database.database import DatabaseManager
from models.tournament import Tournament, TournamentStatus, TournamentFormat, TournamentParticipant, TournamentMatch
from models.match import Match, MatchStatus
from models.player import Player
from config.config import Config
import discord

logger = logging.getLogger(__name__)

class TournamentService:
    """Service for managing tournaments and their lifecycle"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.check_interval = Config.TOURNAMENT_CHECK_INTERVAL
        
    async def start_monitoring(self):
        """Start the tournament monitoring loop"""
        logger.info("Starting tournament monitoring service")
        while True:
            try:
                await self.check_tournaments()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in tournament monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_tournaments(self):
        """Check and update tournament statuses"""
        try:
            session = await self.db.get_session()
        async with session as session:
                # Check tournaments that can start
                await self.check_tournaments_ready_to_start(session)
                
                # Check tournaments that can end
                await self.check_tournaments_ready_to_end(session)
                
                # Update tournament progress
                await self.update_tournament_progress(session)
                
        except Exception as e:
            logger.error(f"Error checking tournaments: {e}")
    
    async def check_tournaments_ready_to_start(self, session):
        """Check if any tournaments are ready to start"""
        try:
            # Get tournaments in registration that can start
            ready_tournaments = await session.execute(
                """
                SELECT t.* FROM tournaments t
                WHERE t.status = 'registration'
                AND t.registration_end <= NOW()
                AND EXISTS (
                    SELECT 1 FROM tournament_participants tp
                    WHERE tp.tournament_id = t.id
                    AND tp.is_active = true
                    HAVING COUNT(*) >= t.min_participants
                )
                """
            )
            ready_tournaments = ready_tournaments.fetchall()
            
            for tournament in ready_tournaments:
                await self.start_tournament(session, tournament)
                
        except Exception as e:
            logger.error(f"Error checking tournaments ready to start: {e}")
    
    async def check_tournaments_ready_to_end(self, session):
        """Check if any tournaments are ready to end"""
        try:
            # Get active tournaments that should end
            active_tournaments = await session.execute(
                """
                SELECT t.* FROM tournaments t
                WHERE t.status = 'active'
                AND t.tournament_start IS NOT NULL
                AND t.tournament_start + INTERVAL '7 days' <= NOW()
                """
            )
            active_tournaments = active_tournaments.fetchall()
            
            for tournament in active_tournaments:
                await self.end_tournament(session, tournament)
                
        except Exception as e:
            logger.error(f"Error checking tournaments ready to end: {e}")
    
    async def update_tournament_progress(self, session):
        """Update tournament progress and advance rounds"""
        try:
            # Get active tournaments
            active_tournaments = await session.execute(
                "SELECT * FROM tournaments WHERE status = 'active'"
            )
            active_tournaments = active_tournaments.fetchall()
            
            for tournament in active_tournaments:
                await self.advance_tournament_round(session, tournament)
                
        except Exception as e:
            logger.error(f"Error updating tournament progress: {e}")
    
    async def start_tournament(self, session, tournament):
        """Start a tournament"""
        try:
            logger.info(f"Starting tournament: {tournament.name}")
            
            # Update tournament status
            tournament.status = TournamentStatus.ACTIVE
            tournament.tournament_start = datetime.utcnow()
            tournament.current_round = 1
            
            # Generate tournament bracket
            await self.generate_tournament_bracket(session, tournament)
            
            # Notify participants
            await self.notify_tournament_started(tournament)
            
            logger.info(f"Tournament {tournament.name} started successfully")
            
        except Exception as e:
            logger.error(f"Error starting tournament {tournament.name}: {e}")
    
    async def end_tournament(self, session, tournament):
        """End a tournament"""
        try:
            logger.info(f"Ending tournament: {tournament.name}")
            
            # Update tournament status
            tournament.status = TournamentStatus.COMPLETED
            tournament.tournament_end = datetime.utcnow()
            
            # Calculate final standings
            await self.calculate_final_standings(session, tournament)
            
            # Notify participants
            await self.notify_tournament_ended(tournament)
            
            logger.info(f"Tournament {tournament.name} ended successfully")
            
        except Exception as e:
            logger.error(f"Error ending tournament {tournament.name}: {e}")
    
    async def generate_tournament_bracket(self, session, tournament):
        """Generate tournament bracket based on format"""
        try:
            if tournament.format == TournamentFormat.SINGLE_ELIMINATION:
                await self.generate_single_elimination_bracket(session, tournament)
            elif tournament.format == TournamentFormat.DOUBLE_ELIMINATION:
                await self.generate_double_elimination_bracket(session, tournament)
            elif tournament.format == TournamentFormat.SWISS_SYSTEM:
                await self.generate_swiss_system_bracket(session, tournament)
            elif tournament.format == TournamentFormat.ROUND_ROBIN:
                await self.generate_round_robin_bracket(session, tournament)
                
        except Exception as e:
            logger.error(f"Error generating tournament bracket: {e}")
    
    async def generate_single_elimination_bracket(self, session, tournament):
        """Generate single elimination bracket"""
        try:
            # Get active participants
            participants = await session.execute(
                "SELECT * FROM tournament_participants WHERE tournament_id = :tournament_id AND is_active = true",
                {"tournament_id": tournament.id}
            )
            participants = participants.fetchall()
            
            if len(participants) < 2:
                logger.warning(f"Not enough participants for tournament {tournament.id}")
                return
            
            # Calculate rounds needed
            import math
            total_rounds = math.ceil(math.log2(len(participants)))
            tournament.total_rounds = total_rounds
            
            # Create first round matches
            match_number = 1
            for i in range(0, len(participants), 2):
                if i + 1 < len(participants):
                    match = TournamentMatch(
                        tournament_id=tournament.id,
                        round_number=1,
                        match_number=match_number,
                        player1_id=participants[i].player_id,
                        player2_id=participants[i + 1].player_id,
                        match_format=tournament.match_format,
                        status="pending"
                    )
                    session.add(match)
                    match_number += 1
                    
        except Exception as e:
            logger.error(f"Error generating single elimination bracket: {e}")
    
    async def generate_double_elimination_bracket(self, session, tournament):
        """Generate double elimination bracket"""
        try:
            # Similar to single elimination but with losers bracket
            # Implementation depends on specific requirements
            await self.generate_single_elimination_bracket(session, tournament)
            
        except Exception as e:
            logger.error(f"Error generating double elimination bracket: {e}")
    
    async def generate_swiss_system_bracket(self, session, tournament):
        """Generate Swiss system bracket"""
        try:
            # Swiss system requires multiple rounds with pairing based on performance
            # Implementation depends on specific requirements
            await self.generate_single_elimination_bracket(session, tournament)
            
        except Exception as e:
            logger.error(f"Error generating Swiss system bracket: {e}")
    
    async def generate_round_robin_bracket(self, session, tournament):
        """Generate round robin bracket"""
        try:
            # Round robin: every player plays against every other player
            # Implementation depends on specific requirements
            await self.generate_single_elimination_bracket(session, tournament)
            
        except Exception as e:
            logger.error(f"Error generating round robin bracket: {e}")
    
    async def advance_tournament_round(self, session, tournament):
        """Advance tournament to next round if possible"""
        try:
            # Check if current round is complete
            current_round_matches = await session.execute(
                """
                SELECT * FROM tournament_matches 
                WHERE tournament_id = :tournament_id 
                AND round_number = :round_number
                """,
                {"tournament_id": tournament.id, "round_number": tournament.current_round}
            )
            current_round_matches = current_round_matches.fetchall()
            
            if not current_round_matches:
                return
            
            # Check if all matches in current round are completed
            completed_matches = [m for m in current_round_matches if m.status == "completed"]
            
            if len(completed_matches) == len(current_round_matches):
                # Current round is complete, advance to next round
                if tournament.current_round < tournament.total_rounds:
                    await self.create_next_round_matches(session, tournament)
                    tournament.current_round += 1
                else:
                    # Tournament is complete
                    await self.end_tournament(session, tournament)
                    
        except Exception as e:
            logger.error(f"Error advancing tournament round: {e}")
    
    async def create_next_round_matches(self, session, tournament):
        """Create matches for the next round"""
        try:
            # Get winners from current round
            winners = await session.execute(
                """
                SELECT winner_id FROM tournament_matches 
                WHERE tournament_id = :tournament_id 
                AND round_number = :round_number
                AND status = 'completed'
                AND winner_id IS NOT NULL
                """,
                {"tournament_id": tournament.id, "round_number": tournament.current_round}
            )
            winners = winners.fetchall()
            
            if len(winners) < 2:
                return
            
            # Create next round matches
            match_number = 1
            for i in range(0, len(winners), 2):
                if i + 1 < len(winners):
                    match = TournamentMatch(
                        tournament_id=tournament.id,
                        round_number=tournament.current_round + 1,
                        match_number=match_number,
                        player1_id=winners[i].winner_id,
                        player2_id=winners[i + 1].winner_id,
                        match_format=tournament.match_format,
                        status="pending"
                    )
                    session.add(match)
                    match_number += 1
                    
        except Exception as e:
            logger.error(f"Error creating next round matches: {e}")
    
    async def calculate_final_standings(self, session, tournament):
        """Calculate final standings for tournament"""
        try:
            # Get all participants with their performance
            participants = await session.execute(
                """
                SELECT tp.*, p.username
                FROM tournament_participants tp
                JOIN players p ON tp.player_id = p.id
                WHERE tp.tournament_id = :tournament_id
                ORDER BY tp.matches_won DESC, tp.matches_lost ASC
                """,
                {"tournament_id": tournament.id}
            )
            participants = participants.fetchall()
            
            # Update final places
            for i, participant in enumerate(participants, 1):
                participant.final_place = i
                
        except Exception as e:
            logger.error(f"Error calculating final standings: {e}")
    
    async def notify_tournament_started(self, tournament):
        """Notify participants that tournament has started"""
        try:
            # Get tournament participants
            session = await self.db.get_session()
        async with session as session:
                participants = await session.execute(
                    "SELECT * FROM tournament_participants WHERE tournament_id = :tournament_id AND is_active = true",
                    {"tournament_id": tournament.id}
                )
                participants = participants.fetchall()
                
                for participant in participants:
                    # Get player's Discord ID
                    player = await session.execute(
                        "SELECT discord_id FROM players WHERE id = :player_id",
                        {"player_id": participant.player_id}
                    )
                    player = player.scalar_one_or_none()
                    
                    if player:
                        user = self.bot.get_user(player.discord_id)
                        if user:
                            embed = self.create_tournament_started_embed(tournament)
                            try:
                                await user.send(
                                    f"🏅 **Турнир начался!**",
                                    embed=embed
                                )
                            except discord.Forbidden:
                                # User has DMs disabled
                                pass
            
            # Send guild notification with role tagging
            if hasattr(self.bot, 'role_manager'):
                tagged_message = await self.bot.role_manager.tag_role_for_event(
                    guild_id=tournament.guild_id,
                    event_type="tournament_start",
                    message="🏅 **Турнир начался!** - Проверьте расписание матчей!"
                )
                
                # Send to guild's system channel or first available channel
                guild = self.bot.get_guild(tournament.guild_id)
                if guild:
                    channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                    if channel:
                        try:
                            await channel.send(tagged_message)
                        except discord.Forbidden:
                            logger.warning(f"Could not send tournament start notification to guild {tournament.guild_id}")
                                
        except Exception as e:
            logger.error(f"Error notifying tournament started: {e}")
    
    async def notify_tournament_ended(self, tournament):
        """Notify participants that tournament has ended"""
        try:
            # Similar to notify_tournament_started but for tournament end
            pass
        except Exception as e:
            logger.error(f"Error notifying tournament ended: {e}")
    
    def create_tournament_started_embed(self, tournament):
        """Create embed for tournament started notification"""
        embed = discord.Embed(
            title=f"🏅 Турнир начался: {tournament.name}",
            description="Турнир официально начался! Проверьте расписание матчей.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Формат",
            value=tournament.format.value.replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="Формат матчей",
            value=tournament.match_format.upper(),
            inline=True
        )
        
        embed.add_field(
            name="Правила",
            value=tournament.rules or "Стандартные правила турнира",
            inline=False
        )
        
        embed.set_footer(text="Удачи в турнире!")
        
        return embed
    
    # Tournament management methods
    async def create_tournament(self, name: str, description: str, guild_id: int, 
                               format: TournamentFormat, match_format: str, 
                               min_participants: int, max_participants: Optional[int],
                               registration_days: int, rules: Optional[str] = None,
                               prize_pool: Optional[str] = None) -> Tournament:
        """Create a new tournament"""
        try:
            session = await self.db.get_session()
        async with session as session:
                tournament = Tournament(
                    name=name,
                    description=description,
                    guild_id=guild_id,
                    format=format,
                    match_format=match_format,
                    min_participants=min_participants,
                    max_participants=max_participants,
                    registration_start=datetime.utcnow(),
                    registration_end=datetime.utcnow() + timedelta(days=registration_days),
                    rules=rules,
                    prize_pool=prize_pool
                )
                
                session.add(tournament)
                await session.commit()
                
                logger.info(f"Created tournament: {name} in guild {guild_id}")
                return tournament
                
        except Exception as e:
            logger.error(f"Error creating tournament: {e}")
            raise
    
    async def register_player(self, tournament_id: int, player_id: int) -> bool:
        """Register a player for a tournament"""
        try:
            session = await self.db.get_session()
        async with session as session:
                # Check if tournament exists and is open for registration
                tournament = await session.execute(
                    "SELECT * FROM tournaments WHERE id = :tournament_id AND status = 'registration'",
                    {"tournament_id": tournament_id}
                )
                tournament = tournament.scalar_one_or_none()
                
                if not tournament:
                    return False
                
                # Check if player is already registered
                existing = await session.execute(
                    "SELECT id FROM tournament_participants WHERE tournament_id = :tournament_id AND player_id = :player_id",
                    {"tournament_id": tournament_id, "player_id": player_id}
                )
                existing = existing.scalar_one_or_none()
                
                if existing:
                    return False
                
                # Check if tournament is full
                if tournament.max_participants:
                    participant_count = await session.execute(
                        "SELECT COUNT(*) FROM tournament_participants WHERE tournament_id = :tournament_id AND is_active = true",
                        {"tournament_id": tournament_id}
                    )
                    participant_count = participant_count.scalar_one_or_none()
                    
                    if participant_count >= tournament.max_participants:
                        return False
                
                # Register player
                participant = TournamentParticipant(
                    tournament_id=tournament_id,
                    player_id=player_id
                )
                
                session.add(participant)
                await session.commit()
                
                logger.info(f"Player {player_id} registered for tournament {tournament_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error registering player for tournament: {e}")
            return False
    
    async def get_tournament_info(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed tournament information"""
        try:
            session = await self.db.get_session()
        async with session as session:
                tournament = await session.execute(
                    "SELECT * FROM tournaments WHERE id = :tournament_id",
                    {"tournament_id": tournament_id}
                )
                tournament = tournament.scalar_one_or_none()
                
                if not tournament:
                    return None
                
                # Get participant count
                participant_count = await session.execute(
                    "SELECT COUNT(*) FROM tournament_participants WHERE tournament_id = :tournament_id AND is_active = true",
                    {"tournament_id": tournament_id}
                )
                participant_count = participant_count.scalar_one_or_none()
                
                # Get match count
                match_count = await session.execute(
                    "SELECT COUNT(*) FROM tournament_matches WHERE tournament_id = :tournament_id",
                    {"tournament_id": tournament_id}
                )
                match_count = match_count.scalar_one_or_none()
                
                return {
                    "id": tournament.id,
                    "name": tournament.name,
                    "description": tournament.description,
                    "status": tournament.status.value,
                    "format": tournament.format.value,
                    "participant_count": participant_count or 0,
                    "match_count": match_count or 0,
                    "registration_start": tournament.registration_start,
                    "registration_end": tournament.registration_end,
                    "tournament_start": tournament.tournament_start,
                    "tournament_end": tournament.tournament_end,
                    "rules": tournament.rules,
                    "prize_pool": tournament.prize_pool
                }
                
        except Exception as e:
            logger.error(f"Error getting tournament info: {e}")
            return None
    
    async def get_guild_tournaments(self, guild_id: int, status: Optional[TournamentStatus] = None) -> List[Dict[str, Any]]:
        """Get tournaments for a specific guild"""
        try:
            session = await self.db.get_session()
        async with session as session:
                query = "SELECT * FROM tournaments WHERE guild_id = :guild_id"
                params = {"guild_id": guild_id}
                
                if status:
                    query += " AND status = :status"
                    params["status"] = status.value
                
                query += " ORDER BY created_at DESC"
                
                tournaments = await session.execute(query, params)
                tournaments = tournaments.fetchall()
                
                result = []
                for tournament in tournaments:
                    info = await self.get_tournament_info(tournament.id)
                    if info:
                        result.append(info)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting guild tournaments: {e}")
            return []