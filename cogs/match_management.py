import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from typing import Optional
from database.database import DatabaseManager
from locales import LocaleManager
from models.match import Match, MatchFormat
from models.player import Player
from models.penalty_settings import PenaltySettings

class MatchCreationModal(Modal, title="Создание матча"):
    """Modal for creating a new match"""
    
    def __init__(self, opponent: discord.Member):
        super().__init__()
        self.opponent = opponent
        
        self.format_input = TextInput(
            label="Формат матча",
            placeholder="bo1, bo2, или bo3",
            default="bo1",
            required=True,
            min_length=3,
            max_length=3
        )
        
        self.add_item(self.format_input)

class MatchJoinView(View):
    """View for players to accept or decline match challenges"""
    
    def __init__(self, challenger: discord.Member, opponent: discord.Member, match_format: str):
        super().__init__(timeout=300)
        self.challenger = challenger
        self.opponent = opponent
        self.match_format = match_format
        self.challenger_accepted = False
        self.opponent_accepted = False
        
        # Add accept/decline buttons
        self.add_item(Button(
            label="✅ Принять вызов",
            custom_id="accept_challenge",
            style=discord.ButtonStyle.success
        ))
        self.add_item(Button(
            label="❌ Отклонить",
            custom_id="decline_challenge",
            style=discord.ButtonStyle.danger
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message(
                "Вы не можете взаимодействовать с этим вызовом.",
                ephemeral=True
            )
            return False
            
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "accept_challenge":
            if interaction.user.id == self.challenger.id:
                self.challenger_accepted = True
                await interaction.response.send_message(
                    "Вы подтвердили готовность к матчу!",
                    ephemeral=True
                )
            elif interaction.user.id == self.opponent.id:
                self.opponent_accepted = True
                await interaction.response.send_message(
                    "Вы приняли вызов!",
                    ephemeral=True
                )
                
            # Check if both players accepted
            if self.challenger_accepted and self.opponent_accepted:
                await self.proceed_to_match(interaction)
                
        elif custom_id == "decline_challenge":
            if interaction.user.id == self.opponent.id:
                await interaction.response.send_message(
                    "Вы отклонили вызов.",
                    ephemeral=True
                )
                await interaction.message.edit(
                    content=f"❌ {self.opponent.mention} отклонил вызов от {self.challenger.mention}",
                    view=None
                )
            else:
                await interaction.response.send_message(
                    "Только оппонент может отклонить вызов.",
                    ephemeral=True
                )
                
        return True
        
    async def proceed_to_match(self, interaction: discord.Interaction):
        """Proceed to match creation after both players accept"""
        try:
            # Create match in database
            db_manager = DatabaseManager()
            session = await db_manager.get_session()
            async with session:
                # Get or create players
                player1 = await self.get_or_create_player(session, self.challenger.id, self.challenger.display_name)
                player2 = await self.get_or_create_player(session, self.opponent.id, self.opponent.display_name)
                
                # Create match
                match = Match(
                    player1_id=player1.id,
                    player2_id=player2.id,
                    format=MatchFormat(self.match_format.lower()),
                    guild_id=interaction.guild_id
                )
                
                session.add(match)
                await session.commit()
                
                # Create match thread
                thread = await interaction.channel.create_thread(
                    name=f"Матч {self.challenger.display_name} vs {self.opponent.display_name}",
                    type=discord.ChannelType.public_thread
                )
                
                # Update match with thread ID
                match.thread_id = thread.id
                await session.commit()
                
                # Send match confirmation
                embed = discord.Embed(
                    title="🎮 Матч создан!",
                    description=f"**{self.challenger.mention}** vs **{self.opponent.mention}**",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Формат",
                    value=self.match_format.upper(),
                    inline=True
                )
                
                embed.add_field(
                    name="Статус",
                    value="Ожидание готовности игроков",
                    inline=True
                )
                
                await thread.send(
                    f"🎮 **Матч создан!**\n\n"
                    f"**Игрок 1**: {self.challenger.mention}\n"
                    f"**Игрок 2**: {self.opponent.mention}\n"
                    f"**Формат**: {self.match_format.upper()}\n\n"
                    f"Оба игрока должны подтвердить готовность к матчу.",
                    embed=embed
                )
                
                await interaction.message.edit(
                    content=f"✅ Матч создан! Перейдите в {thread.mention}",
                    view=None
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка при создании матча: {str(e)}",
                ephemeral=True
            )
    
    async def get_or_create_player(self, session, discord_id: int, username: str) -> Player:
        """Get existing player or create new one"""
        player = await session.execute(
            "SELECT * FROM players WHERE discord_id = :discord_id",
            {"discord_id": discord_id}
        )
        player = player.scalar_one_or_none()
        
        if not player:
            player = Player(discord_id=discord_id, username=username)
            session.add(player)
            await session.commit()
            await session.refresh(player)
        
        return player

class MatchManagement(commands.Cog):
    """Cog for managing match creation and management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        
    @app_commands.command(name="challenge", description="Вызвать игрока на матч")
    @app_commands.describe(
        opponent="Игрок для вызова",
        format="Формат матча (Bo1, Bo2, Bo3)"
    )
    async def challenge(
        self, 
        interaction: discord.Interaction, 
        opponent: discord.Member,
        format: str = "Bo1"
    ):
        """Вызвать игрока на матч"""
        await interaction.response.defer()
        
        try:
            # Check if user is challenging themselves
            if interaction.user.id == opponent.id:
                await interaction.followup.send(
                    "❌ Вы не можете вызвать сами себя на матч.",
                    ephemeral=True
                )
                return
            
            # Check if opponent is a bot
            if opponent.bot:
                await interaction.followup.send(
                    "❌ Вы не можете вызвать бота на матч.",
                    ephemeral=True
                )
                return
            
            # Check season status and blocking
            season_manager = self.bot.get_cog('SeasonManager')
            if season_manager:
                can_create, reason = await season_manager.can_create_new_match(interaction.guild_id)
                if not can_create:
                    embed = discord.Embed(
                        title="🚫 Создание матчей заблокировано",
                        description=f"**Причина**: {reason}",
                        color=discord.Color.red()
                    )
                    
                    # Get season status for more details
                    season = await season_manager.get_season_status(interaction.guild_id)
                    if season:
                        embed.add_field(
                            name="Информация о сезоне",
                            value=f"**Сезон**: {season.name}\n**Статус**: {season.get_status_description()}",
                            inline=False
                        )
                        
                        if season.is_ending_soon:
                            embed.add_field(
                                name="⚠️ Важно",
                                value="Завершите все активные матчи до окончания сезона!",
                                inline=False
                            )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Check if matches are restricted to specific channel
            session = await self.db.get_session()
        async with session:
                penalty_settings = await session.execute(
                    "SELECT match_channel_id FROM penalty_settings WHERE guild_id = :guild_id",
                    {"guild_id": interaction.guild_id}
                )
                penalty_settings = penalty_settings.scalar_one_or_none()
                
                if penalty_settings and penalty_settings.match_channel_id:
                    if interaction.channel_id != penalty_settings.match_channel_id:
                        await interaction.followup.send(
                            f"❌ Матчи можно создавать только в канале <#{penalty_settings.match_channel_id}>",
                            ephemeral=True
                        )
                        return
            
            # Validate match format
            if format.lower() not in ['bo1', 'bo2', 'bo3']:
                await interaction.followup.send(
                    "Неверный формат матча. Используйте: bo1, bo2, или bo3",
                    ephemeral=True
                )
                return
            
            # Check if there's already an active match between these players
            session = await self.db.get_session()
        async with session:
                active_match = await session.execute(
                    """
                    SELECT m.* FROM matches m 
                    JOIN players p1 ON m.player1_id = p1.id 
                    JOIN players p2 ON m.player2_id = p2.id 
                    WHERE m.guild_id = :guild_id 
                    AND m.status NOT IN ('complete', 'annulled')
                    AND (
                        (p1.discord_id = :user_id AND p2.discord_id = :opponent_id)
                        OR (p1.discord_id = :opponent_id AND p2.discord_id = :user_id)
                    )
                    """,
                    {
                        "guild_id": interaction.guild_id,
                        "user_id": interaction.user.id,
                        "opponent_id": opponent.id
                    }
                )
                active_match = active_match.scalar_one_or_none()
                
                if active_match:
                    await interaction.followup.send(
                        f"❌ У вас уже есть активный матч с {opponent.mention}.",
                        ephemeral=True
                    )
                    return
            
            # Create challenge view
            view = MatchJoinView(interaction.user, opponent, format)
            
            embed = discord.Embed(
                title="⚔️ Вызов на матч!",
                description=f"{interaction.user.mention} вызывает {opponent.mention} на матч!",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Формат",
                value=format.upper(),
                inline=True
            )
            
            embed.add_field(
                name="Статус",
                value="Ожидание ответа",
                inline=True
            )
            
            await interaction.followup.send(
                f"⚔️ **{interaction.user.mention}** вызывает **{opponent.mention}** на матч!",
                embed=embed,
                view=view
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Ошибка при создании вызова: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Setup function for the cog"""
    await bot.add_cog(MatchManagement(bot))