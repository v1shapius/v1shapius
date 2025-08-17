-- Discord Rating Bot Database Initialization Script

-- Create database if it doesn't exist
-- This will be handled by Docker environment variables

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE match_format AS ENUM ('bo1', 'bo2', 'bo3');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE match_status AS ENUM ('waiting', 'active', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE match_stage AS ENUM (
        'waiting_readiness',
        'waiting_draft',
        'waiting_first_player',
        'preparing_game',
        'game_in_progress',
        'waiting_confirmation',
        'match_complete'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create players table
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    discriminator VARCHAR(4),
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on discord_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id);

-- Create seasons table
CREATE TABLE IF NOT EXISTS seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    initial_rating INTEGER DEFAULT 1500,
    k_factor_new INTEGER DEFAULT 40,
    k_factor_established INTEGER DEFAULT 20,
    established_threshold INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on active seasons
CREATE INDEX IF NOT EXISTS idx_seasons_active ON seasons(is_active);

-- Create penalty_settings table
CREATE TABLE IF NOT EXISTS penalty_settings (
    id SERIAL PRIMARY KEY,
    discord_guild_id BIGINT NOT NULL,
    restart_penalty_seconds FLOAT DEFAULT 30.0,
    max_restarts_before_penalty INTEGER DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on guild_id
CREATE INDEX IF NOT EXISTS idx_penalty_settings_guild_id ON penalty_settings(discord_guild_id);

-- Create matches table
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    discord_guild_id BIGINT NOT NULL,
    discord_channel_id BIGINT NOT NULL,
    discord_voice_channel_id BIGINT,
    player1_id INTEGER NOT NULL REFERENCES players(id),
    player2_id INTEGER NOT NULL REFERENCES players(id),
    format match_format NOT NULL,
    status match_status DEFAULT 'waiting',
    current_stage match_stage DEFAULT 'waiting_readiness',
    draft_link VARCHAR(500),
    first_player_id INTEGER REFERENCES players(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for matches
CREATE INDEX IF NOT EXISTS idx_matches_guild_id ON matches(discord_guild_id);
CREATE INDEX IF NOT EXISTS idx_matches_channel_id ON matches(discord_channel_id);
CREATE INDEX IF NOT EXISTS idx_matches_voice_channel_id ON matches(discord_voice_channel_id);
CREATE INDEX IF NOT EXISTS idx_matches_player1_id ON matches(player1_id);
CREATE INDEX IF NOT EXISTS idx_matches_player2_id ON matches(player2_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_stage ON matches(current_stage);

-- Create match_states table for tracking match progress
CREATE TABLE IF NOT EXISTS match_states (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    stage match_stage NOT NULL,
    data JSONB,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on match_id
CREATE INDEX IF NOT EXISTS idx_match_states_match_id ON match_states(match_id);

-- Create game_results table
CREATE TABLE IF NOT EXISTS game_results (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    game_number INTEGER NOT NULL,
    player1_time FLOAT NOT NULL,
    player1_restarts INTEGER DEFAULT 0,
    player1_penalties FLOAT DEFAULT 0.0,
    player1_final_time FLOAT NOT NULL,
    player2_time FLOAT NOT NULL,
    player2_restarts INTEGER DEFAULT 0,
    player2_penalties FLOAT DEFAULT 0.0,
    player2_final_time FLOAT NOT NULL,
    player1_confirmed INTEGER REFERENCES players(id),
    player2_confirmed INTEGER REFERENCES players(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for game_results
CREATE INDEX IF NOT EXISTS idx_game_results_match_id ON game_results(match_id);
CREATE INDEX IF NOT EXISTS idx_game_results_game_number ON game_results(game_number);

-- Create ratings table
CREATE TABLE IF NOT EXISTS ratings (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    rating FLOAT NOT NULL,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    rating_change FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for ratings
CREATE INDEX IF NOT EXISTS idx_ratings_player_id ON ratings(player_id);
CREATE INDEX IF NOT EXISTS idx_ratings_season_id ON ratings(season_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating);

-- Create unique constraint for player-season combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_ratings_player_season_unique ON ratings(player_id, season_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_seasons_updated_at BEFORE UPDATE ON seasons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_penalty_settings_updated_at BEFORE UPDATE ON penalty_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_states_updated_at BEFORE UPDATE ON match_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_game_results_updated_at BEFORE UPDATE ON game_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ratings_updated_at BEFORE UPDATE ON ratings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default season if none exists
INSERT INTO seasons (name, start_date, is_active, initial_rating, k_factor_new, k_factor_established, established_threshold)
SELECT 'Season 1', CURRENT_TIMESTAMP, true, 1500, 40, 20, 30
WHERE NOT EXISTS (SELECT 1 FROM seasons WHERE is_active = true);

-- Create views for common queries
CREATE OR REPLACE VIEW active_matches AS
SELECT 
    m.*,
    p1.username as player1_name,
    p2.username as player2_name
FROM matches m
JOIN players p1 ON m.player1_id = p1.id
JOIN players p2 ON m.player2_id = p2.id
WHERE m.status IN ('waiting', 'active');

CREATE OR REPLACE VIEW player_stats AS
SELECT 
    p.id,
    p.discord_id,
    p.username,
    p.display_name,
    r.rating,
    r.games_played,
    r.wins,
    r.losses,
    r.draws,
    CASE 
        WHEN r.games_played > 0 THEN ROUND((r.wins::float / r.games_played) * 100, 1)
        ELSE 0 
    END as win_rate
FROM players p
LEFT JOIN ratings r ON p.id = r.player_id
LEFT JOIN seasons s ON r.season_id = s.id
WHERE s.is_active = true OR r.id IS NULL;

-- Create function to calculate match winner
CREATE OR REPLACE FUNCTION get_match_winner(match_id_param INTEGER)
RETURNS INTEGER AS $$
DECLARE
    match_format_val match_format;
    winner_id INTEGER;
BEGIN
    -- Get match format
    SELECT format INTO match_format_val FROM matches WHERE id = match_id_param;
    
    IF match_format_val = 'bo1' THEN
        -- For BO1, winner is player with better time
        SELECT 
            CASE 
                WHEN player1_final_time < player2_final_time THEN 
                    (SELECT player1_id FROM matches WHERE id = match_id_param)
                ELSE 
                    (SELECT player2_id FROM matches WHERE id = match_id_param)
            END INTO winner_id
        FROM game_results 
        WHERE match_id = match_id_param 
        LIMIT 1;
        
    ELSIF match_format_val = 'bo2' THEN
        -- For BO2, sum up times from both games
        SELECT 
            CASE 
                WHEN SUM(player1_final_time) < SUM(player2_final_time) THEN 
                    (SELECT player1_id FROM matches WHERE id = match_id_param)
                ELSE 
                    (SELECT player2_id FROM matches WHERE id = match_id_param)
            END INTO winner_id
        FROM game_results 
        WHERE match_id = match_id_param;
        
    ELSIF match_format_val = 'bo3' THEN
        -- For BO3, count wins
        SELECT 
            CASE 
                WHEN COUNT(CASE WHEN player1_final_time < player2_final_time THEN 1 END) > 
                     COUNT(CASE WHEN player2_final_time < player1_final_time THEN 1 END) THEN 
                    (SELECT player1_id FROM matches WHERE id = match_id_param)
                WHEN COUNT(CASE WHEN player2_final_time < player1_final_time THEN 1 END) > 
                     COUNT(CASE WHEN player1_final_time < player2_final_time THEN 1 END) THEN 
                    (SELECT player2_id FROM matches WHERE id = match_id_param)
                ELSE NULL
            END INTO winner_id
        FROM game_results 
        WHERE match_id = match_id_param;
    END IF;
    
    RETURN winner_id;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to bot user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bot_user;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_matches_status_stage ON matches(status, current_stage);
CREATE INDEX IF NOT EXISTS idx_game_results_confirmed ON game_results(player1_confirmed, player2_confirmed);
CREATE INDEX IF NOT EXISTS idx_ratings_active ON ratings(season_id) WHERE season_id IN (SELECT id FROM seasons WHERE is_active = true);

-- Insert sample data for testing (optional)
-- Uncomment the following lines if you want to insert sample data

/*
INSERT INTO players (discord_id, username, display_name) VALUES
(123456789012345678, 'TestPlayer1', 'Test Player 1'),
(987654321098765432, 'TestPlayer2', 'Test Player 2')
ON CONFLICT (discord_id) DO NOTHING;

INSERT INTO penalty_settings (discord_guild_id, restart_penalty_seconds, max_restarts_before_penalty, description) VALUES
(123456789012345678, 30, 0, 'Default penalty settings')
ON CONFLICT (discord_guild_id) DO NOTHING;
*/

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Discord Rating Bot database initialized successfully';
END $$;