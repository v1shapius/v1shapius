-- Discord Rating Bot Database Initialization Script

-- Create database if it doesn't exist
-- This will be handled by Docker environment variables

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom ENUM types
CREATE TYPE match_format AS ENUM ('bo1', 'bo2', 'bo3');
CREATE TYPE match_status AS ENUM ('waiting_players', 'waiting_readiness', 'draft_verification', 'first_player_selection', 'game_preparation', 'game_in_progress', 'result_confirmation', 'complete');
CREATE TYPE match_stage AS ENUM ('waiting_readiness', 'draft_verification', 'first_player_selection', 'game_preparation', 'game_in_progress', 'result_confirmation', 'complete');

-- Create tables
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    glicko2_rd_initial FLOAT DEFAULT 350.0,
    glicko2_volatility_initial FLOAT DEFAULT 0.06,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE penalty_settings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT UNIQUE NOT NULL,
    restart_penalty INTEGER DEFAULT 30 NOT NULL,
    match_channel_id BIGINT,
    leaderboard_channel_id BIGINT,
    audit_channel_id BIGINT,
    voice_category_id BIGINT,
    instructions_message_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    format match_format NOT NULL,
    status match_status NOT NULL DEFAULT 'waiting_players',
    current_stage match_stage NOT NULL DEFAULT 'waiting_readiness',
    player1_id INTEGER REFERENCES players(id),
    player2_id INTEGER REFERENCES players(id),
    season_id INTEGER REFERENCES seasons(id),
    guild_id BIGINT NOT NULL,
    thread_id BIGINT,
    voice_channel_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_states (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
    stage match_stage NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE game_results (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id),
    game_number INTEGER NOT NULL,
    completion_time_seconds INTEGER NOT NULL,
    restart_count INTEGER DEFAULT 0,
    penalty_seconds INTEGER DEFAULT 0,
    final_time_seconds INTEGER NOT NULL,
    is_confirmed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
    season_id INTEGER REFERENCES seasons(id),
    rating FLOAT DEFAULT 1500.0,
    rd FLOAT DEFAULT 350.0,
    volatility FLOAT DEFAULT 0.06,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    rating_change FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season_id)
);

-- Create indexes for better performance
CREATE INDEX idx_players_discord_id ON players(discord_id);
CREATE INDEX idx_matches_guild_id ON matches(guild_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_players ON matches(player1_id, player2_id);
CREATE INDEX idx_game_results_match_id ON game_results(match_id);
CREATE INDEX idx_ratings_player_season ON ratings(player_id, season_id);
CREATE INDEX idx_penalty_settings_guild_id ON penalty_settings(guild_id);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_seasons_updated_at BEFORE UPDATE ON seasons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_penalty_settings_updated_at BEFORE UPDATE ON penalty_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_game_results_updated_at BEFORE UPDATE ON game_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ratings_updated_at BEFORE UPDATE ON ratings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default season
INSERT INTO seasons (name, start_date, end_date) VALUES ('Season 1', CURRENT_DATE, CURRENT_DATE + INTERVAL '90 days');

-- Create views for common queries
CREATE VIEW active_matches AS
SELECT m.*, p1.username as player1_name, p2.username as player2_name
FROM matches m
JOIN players p1 ON m.player1_id = p1.id
JOIN players p2 ON m.player2_id = p2.id
WHERE m.status != 'complete';

CREATE VIEW player_stats AS
SELECT 
    p.discord_id,
    p.username,
    r.rating,
    r.games_played,
    r.wins,
    r.losses,
    r.draws
FROM players p
LEFT JOIN ratings r ON p.id = r.player_id
LEFT JOIN seasons s ON r.season_id = s.id
WHERE s.is_active = true OR s.is_active IS NULL;

CREATE VIEW match_winner AS
SELECT 
    m.id as match_id,
    m.format,
    CASE 
        WHEN m.format = 'bo1' THEN
            CASE 
                WHEN gr1.final_time_seconds < gr2.final_time_seconds THEN p1.username
                ELSE p2.username
            END
        WHEN m.format = 'bo2' THEN
            CASE 
                WHEN (gr1.final_time_seconds + gr3.final_time_seconds) < (gr2.final_time_seconds + gr4.final_time_seconds) THEN p1.username
                ELSE p2.username
            END
        WHEN m.format = 'bo3' THEN
            CASE 
                WHEN (gr1.final_time_seconds < gr2.final_time_seconds)::int + (gr3.final_time_seconds < gr4.final_time_seconds)::int + (gr5.final_time_seconds < gr6.final_time_seconds)::int >= 2 THEN p1.username
                ELSE p2.username
            END
    END as winner
FROM matches m
JOIN players p1 ON m.player1_id = p1.id
JOIN players p2 ON m.player2_id = p2.id
LEFT JOIN game_results gr1 ON m.id = gr1.match_id AND gr1.player_id = m.player1_id AND gr1.game_number = 1
LEFT JOIN game_results gr2 ON m.id = gr2.match_id AND gr2.player_id = m.player2_id AND gr2.game_number = 1
LEFT JOIN game_results gr3 ON m.id = gr3.match_id AND gr3.player_id = m.player1_id AND gr3.game_number = 2
LEFT JOIN game_results gr4 ON m.id = gr4.match_id AND gr4.player_id = m.player2_id AND gr4.game_number = 2
LEFT JOIN game_results gr5 ON m.id = gr5.match_id AND gr5.player_id = m.player1_id AND gr5.game_number = 3
LEFT JOIN game_results gr6 ON m.id = gr6.match_id AND gr6.player_id = m.player2_id AND gr6.game_number = 3
WHERE m.status = 'complete';

-- Grant permissions to bot user (adjust username as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO discord_bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO discord_bot_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO discord_bot_user;