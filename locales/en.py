# English localization file

MATCH_CREATION = {
    "title": "🎮 New Match Created",
    "description": "A new match has been created!",
    "player1": "Player 1",
    "player2": "Player 2",
    "format": "Format",
    "status": "Status",
    "created_at": "Created at",
    "join_match": "Join Match",
    "waiting_players": "Waiting for players to join...",
    "both_players_joined": "Both players have joined!",
    "voice_channel_created": "Voice channel created: {channel_name}"
}

MATCH_STAGES = {
    "waiting_readiness": "⏳ Waiting for players to confirm readiness",
    "waiting_draft": "📋 Waiting for draft confirmation",
    "waiting_first_player": "🎯 Waiting for players to choose who goes first",
    "preparing_game": "🎮 Preparing for the game",
    "game_in_progress": "🏃 Game in progress",
    "waiting_confirmation": "✅ Waiting for result confirmation",
    "match_complete": "🏁 Match complete"
}

DRAFT_VERIFICATION = {
    "title": "📋 Draft Verification",
    "description": "Please provide the draft link",
    "placeholder": "Enter draft link here",
    "submit": "Submit Draft",
    "waiting_both": "Waiting for both players to submit draft links...",
    "links_match": "✅ Draft links match! Draft confirmed.",
    "links_dont_match": "❌ Draft links don't match. Please coordinate and try again.",
    "draft_confirmed": "Draft confirmed successfully!"
}

FIRST_PLAYER_SELECTION = {
    "title": "🎯 Who Goes First?",
    "description": "Please select who will play first",
    "player1_first": "Player 1 goes first",
    "player2_first": "Player 2 goes first",
    "waiting_choices": "Waiting for both players to make their choice...",
    "choices_match": "✅ Both players chose the same option!",
    "choices_dont_match": "❌ Players made different choices. Please coordinate and try again.",
    "first_player_selected": "First player selected: {player_name}"
}

GAME_PREPARATION = {
    "title": "🎮 Game Preparation",
    "first_player_instructions": "Please turn off your stream and click ready when prepared",
    "second_player_instructions": "Please confirm that everything matches the draft and you're watching the stream",
    "ready_button": "I'm Ready",
    "confirm_draft_button": "Confirm Draft & Stream",
    "waiting_first_player": "Waiting for first player to be ready...",
    "waiting_second_player": "Waiting for second player to confirm...",
    "both_ready": "✅ Both players are ready! Game can begin.",
    "stream_check_failed": "❌ Stream is still active. Please turn it off and try again."
}

GAME_RESULTS = {
    "title": "⏱️ Game Results",
    "description": "Please enter your completion time and restart count",
    "time_label": "Completion Time (MM:SS)",
    "time_placeholder": "05:30",
    "restarts_label": "Number of Restarts",
    "restarts_placeholder": "2",
    "submit_results": "Submit Results",
    "waiting_confirmation": "Waiting for opponent to confirm results...",
    "results_confirmed": "✅ Results confirmed by both players!",
    "results_disputed": "❌ Results disputed. Please resolve the issue."
}

MATCH_COMPLETION = {
    "title": "🏁 Match Results",
    "description": "Final match results",
    "game_results": "Game Results",
    "total_time": "Total Time",
    "restarts": "Restarts",
    "penalties": "Penalties",
    "final_time": "Final Time",
    "winner": "Winner",
    "confirm_results": "Confirm Results",
    "results_confirmed": "✅ Match results confirmed!",
    "match_archived": "Match archived successfully.",
    "voice_channel_deletion": "Voice channel will be deleted in 5 minutes."
}

RATING_SYSTEM = {
    "title": "📊 Rating Update",
    "description": "Rating changes after the match",
    "old_rating": "Old Rating",
    "new_rating": "New Rating",
    "change": "Change",
    "rating_increased": "Rating increased by {points}",
    "rating_decreased": "Rating decreased by {points}",
    "rating_unchanged": "Rating unchanged"
}

ERRORS = {
    "player_not_in_voice": "❌ Player {player_name} is not in the voice channel",
    "stream_active": "❌ Stream is still active. Please turn it off first.",
    "invalid_time_format": "❌ Invalid time format. Use MM:SS",
    "invalid_restart_count": "❌ Invalid restart count. Must be a positive number.",
    "match_not_found": "❌ Match not found",
    "insufficient_permissions": "❌ Insufficient permissions",
    "already_in_match": "❌ You are already in a match",
    "voice_channel_full": "❌ Voice channel is full"
}

SUCCESS = {
    "match_created": "✅ Match created successfully!",
    "player_joined": "✅ Player joined the match!",
    "readiness_confirmed": "✅ Readiness confirmed!",
    "draft_confirmed": "✅ Draft confirmed!",
    "first_player_set": "✅ First player set!",
    "game_started": "✅ Game started!",
    "results_submitted": "✅ Results submitted!",
    "match_completed": "✅ Match completed successfully!"
}

BUTTONS = {
    "confirm": "Confirm",
    "cancel": "Cancel",
    "ready": "Ready",
    "submit": "Submit",
    "dispute": "Dispute",
    "join": "Join",
    "leave": "Leave"
}

FORMATS = {
    "bo1": "Best of 1",
    "bo2": "Best of 2",
    "bo3": "Best of 3"
}

STATUSES = {
    "waiting": "Waiting",
    "active": "Active",
    "completed": "Completed",
    "cancelled": "Cancelled"
}