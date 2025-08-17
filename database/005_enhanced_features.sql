-- Migration: Enhanced Features - Achievements, Tournaments, Security
-- Date: 2024-01-01
-- Description: Add tables for achievements, tournaments, and security system

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- ACHIEVEMENTS SYSTEM
-- ========================================

-- Create achievement types enum
CREATE TYPE achievement_type AS ENUM (
    'first_match',
    'first_win',
    'streak_3',
    'streak_5',
    'streak_10',
    'rating_1600',
    'rating_1800',
    'rating_2000',
    'season_winner',
    'matches_10',
    'matches_50',
    'matches_100',
    'referee_help',
    'perfect_match',
    'comeback_win'
);

-- Create achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    achievement_type achievement_type NOT NULL,
    unlocked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_hidden BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create achievement progress table
CREATE TABLE IF NOT EXISTS achievement_progress (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    achievement_type achievement_type NOT NULL,
    current_progress INTEGER NOT NULL DEFAULT 0,
    target_progress INTEGER NOT NULL,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(player_id, achievement_type)
);

-- ========================================
-- TOURNAMENT SYSTEM
-- ========================================

-- Create tournament status enum
CREATE TYPE tournament_status AS ENUM (
    'registration',
    'active',
    'completed',
    'cancelled'
);

-- Create tournament format enum
CREATE TYPE tournament_format AS ENUM (
    'single_elimination',
    'double_elimination',
    'swiss_system',
    'round_robin'
);

-- Create tournaments table
CREATE TABLE IF NOT EXISTS tournaments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    guild_id BIGINT NOT NULL,
    season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
    
    -- Tournament settings
    status tournament_status NOT NULL DEFAULT 'registration',
    format tournament_format NOT NULL,
    max_participants INTEGER,
    min_participants INTEGER NOT NULL DEFAULT 4,
    
    -- Timing
    registration_start TIMESTAMP NOT NULL,
    registration_end TIMESTAMP NOT NULL,
    tournament_start TIMESTAMP,
    tournament_end TIMESTAMP,
    
    -- Rules and settings
    match_format VARCHAR(10) NOT NULL DEFAULT 'bo3',
    rules TEXT,
    prize_pool TEXT,
    
    -- Tournament data
    bracket_data JSONB,
    current_round INTEGER NOT NULL DEFAULT 0,
    total_rounds INTEGER,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create tournament participants table
CREATE TABLE IF NOT EXISTS tournament_participants (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    
    -- Participant status
    is_active BOOLEAN NOT NULL DEFAULT true,
    registration_time TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Tournament performance
    final_place INTEGER,
    matches_won INTEGER NOT NULL DEFAULT 0,
    matches_lost INTEGER NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(tournament_id, player_id)
);

-- Create tournament matches table
CREATE TABLE IF NOT EXISTS tournament_matches (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL,
    
    -- Match information
    round_number INTEGER NOT NULL,
    match_number INTEGER NOT NULL,
    player1_id INTEGER NOT NULL REFERENCES players(id),
    player2_id INTEGER NOT NULL REFERENCES players(id),
    
    -- Match status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    winner_id INTEGER REFERENCES players(id),
    
    -- Match details
    match_format VARCHAR(10) NOT NULL,
    scheduled_time TIMESTAMP,
    actual_start_time TIMESTAMP,
    actual_end_time TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ========================================
-- SECURITY SYSTEM
-- ========================================

-- Create security event type enum
CREATE TYPE security_event_type AS ENUM (
    'suspicious_match',
    'rating_spike',
    'multiple_accounts',
    'unusual_activity',
    'referee_abuse',
    'system_abuse'
);

-- Create security level enum
CREATE TYPE security_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- Create security events table
CREATE TABLE IF NOT EXISTS security_events (
    id SERIAL PRIMARY KEY,
    event_type security_event_type NOT NULL,
    security_level security_level NOT NULL,
    
    -- Event details
    guild_id BIGINT NOT NULL,
    player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL,
    
    -- Event data
    description TEXT NOT NULL,
    evidence JSONB,
    risk_score FLOAT NOT NULL DEFAULT 0.0,
    
    -- Status
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_by BIGINT,
    resolution_notes TEXT,
    resolution_time TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create player security profiles table
CREATE TABLE IF NOT EXISTS player_security_profiles (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE UNIQUE,
    
    -- Risk assessment
    overall_risk_score FLOAT NOT NULL DEFAULT 0.0,
    risk_level security_level NOT NULL DEFAULT 'low',
    
    -- Behavior tracking
    total_matches INTEGER NOT NULL DEFAULT 0,
    suspicious_matches INTEGER NOT NULL DEFAULT 0,
    rating_changes JSONB,
    
    -- Account security
    ip_addresses JSONB,
    device_fingerprints JSONB,
    last_suspicious_activity TIMESTAMP,
    
    -- Restrictions
    is_restricted BOOLEAN NOT NULL DEFAULT false,
    restriction_reason TEXT,
    restriction_until TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create match integrity checks table
CREATE TABLE IF NOT EXISTS match_integrity_checks (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE UNIQUE,
    
    -- Integrity metrics
    time_consistency_score FLOAT NOT NULL DEFAULT 1.0,
    result_plausibility_score FLOAT NOT NULL DEFAULT 1.0,
    overall_integrity_score FLOAT NOT NULL DEFAULT 1.0,
    
    -- Check details
    performed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    check_type VARCHAR(50) NOT NULL,
    details JSONB,
    
    -- Flags
    is_suspicious BOOLEAN NOT NULL DEFAULT false,
    requires_review BOOLEAN NOT NULL DEFAULT false,
    reviewed_by BIGINT,
    review_notes TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create security rules table
CREATE TABLE IF NOT EXISTS security_rules (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    
    -- Rule configuration
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Rule parameters
    parameters JSONB NOT NULL,
    threshold FLOAT NOT NULL,
    
    -- Actions
    actions JSONB NOT NULL,
    notification_channels JSONB,
    
    -- Statistics
    times_triggered INTEGER NOT NULL DEFAULT 0,
    last_triggered TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Achievements indexes
CREATE INDEX IF NOT EXISTS idx_achievements_player_id ON achievements(player_id);
CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(achievement_type);
CREATE INDEX IF NOT EXISTS idx_achievements_unlocked_at ON achievements(unlocked_at);

-- Achievement progress indexes
CREATE INDEX IF NOT EXISTS idx_achievement_progress_player_id ON achievement_progress(player_id);
CREATE INDEX IF NOT EXISTS idx_achievement_progress_type ON achievement_progress(achievement_type);

-- Tournament indexes
CREATE INDEX IF NOT EXISTS idx_tournaments_guild_id ON tournaments(guild_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
CREATE INDEX IF NOT EXISTS idx_tournaments_season_id ON tournaments(season_id);

-- Tournament participants indexes
CREATE INDEX IF NOT EXISTS idx_tournament_participants_tournament_id ON tournament_participants(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_participants_player_id ON tournament_participants(player_id);

-- Tournament matches indexes
CREATE INDEX IF NOT EXISTS idx_tournament_matches_tournament_id ON tournament_matches(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_matches_round ON tournament_matches(round_number);
CREATE INDEX IF NOT EXISTS idx_tournament_matches_status ON tournament_matches(status);

-- Security indexes
CREATE INDEX IF NOT EXISTS idx_security_events_guild_id ON security_events(guild_id);
CREATE INDEX IF NOT EXISTS idx_security_events_player_id ON security_events(player_id);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_level ON security_events(security_level);
CREATE INDEX IF NOT EXISTS idx_security_events_resolved ON security_events(is_resolved);

-- Player security profiles indexes
CREATE INDEX IF NOT EXISTS idx_player_security_profiles_risk_level ON player_security_profiles(risk_level);
CREATE INDEX IF NOT EXISTS idx_player_security_profiles_restricted ON player_security_profiles(is_restricted);

-- Match integrity checks indexes
CREATE INDEX IF NOT EXISTS idx_match_integrity_checks_suspicious ON match_integrity_checks(is_suspicious);
CREATE INDEX IF NOT EXISTS idx_match_integrity_checks_review ON match_integrity_checks(requires_review);

-- Security rules indexes
CREATE INDEX IF NOT EXISTS idx_security_rules_guild_id ON security_rules(guild_id);
CREATE INDEX IF NOT EXISTS idx_security_rules_type ON security_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_security_rules_active ON security_rules(is_active);

-- ========================================
-- FUNCTIONS AND TRIGGERS
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_achievements_updated_at BEFORE UPDATE ON achievements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_achievement_progress_updated_at BEFORE UPDATE ON achievement_progress FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tournaments_updated_at BEFORE UPDATE ON tournaments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tournament_participants_updated_at BEFORE UPDATE ON tournament_participants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tournament_matches_updated_at BEFORE UPDATE ON tournament_matches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_security_events_updated_at BEFORE UPDATE ON security_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_player_security_profiles_updated_at BEFORE UPDATE ON player_security_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_match_integrity_checks_updated_at BEFORE UPDATE ON match_integrity_checks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_security_rules_updated_at BEFORE UPDATE ON security_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check if tournament can start
CREATE OR REPLACE FUNCTION can_tournament_start(tournament_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    tournament_record RECORD;
    participant_count INTEGER;
BEGIN
    SELECT * INTO tournament_record FROM tournaments WHERE id = tournament_id;
    
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Check if tournament is in registration status
    IF tournament_record.status != 'registration' THEN
        RETURN false;
    END IF;
    
    -- Count active participants
    SELECT COUNT(*) INTO participant_count 
    FROM tournament_participants 
    WHERE tournament_id = tournament_id AND is_active = true;
    
    -- Check if enough participants
    RETURN participant_count >= tournament_record.min_participants;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate achievement completion percentage
CREATE OR REPLACE FUNCTION get_achievement_completion_percentage(player_id INTEGER)
RETURNS FLOAT AS $$
DECLARE
    unlocked_count INTEGER;
    total_possible INTEGER;
BEGIN
    -- Count unlocked achievements
    SELECT COUNT(*) INTO unlocked_count 
    FROM achievements 
    WHERE player_id = player_id;
    
    -- Total possible achievements (hardcoded for now)
    total_possible := 15;
    
    IF total_possible = 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN (unlocked_count::FLOAT / total_possible::FLOAT) * 100.0;
END;
$$ LANGUAGE plpgsql;

-- Function to get player security risk level
CREATE OR REPLACE FUNCTION get_player_security_risk_level(player_id INTEGER)
RETURNS security_level AS $$
DECLARE
    risk_score FLOAT;
BEGIN
    SELECT overall_risk_score INTO risk_score 
    FROM player_security_profiles 
    WHERE player_id = player_id;
    
    IF risk_score IS NULL THEN
        RETURN 'low';
    END IF;
    
    IF risk_score >= 0.8 THEN
        RETURN 'critical';
    ELSIF risk_score >= 0.6 THEN
        RETURN 'high';
    ELSIF risk_score >= 0.3 THEN
        RETURN 'medium';
    ELSE
        RETURN 'low';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- View for tournament overview
CREATE OR REPLACE VIEW tournament_overview AS
SELECT 
    t.id,
    t.name,
    t.status,
    t.format,
    t.guild_id,
    t.registration_start,
    t.registration_end,
    COUNT(tp.id) as participant_count,
    t.min_participants,
    t.max_participants
FROM tournaments t
LEFT JOIN tournament_participants tp ON t.id = tp.tournament_id AND tp.is_active = true
GROUP BY t.id, t.name, t.status, t.format, t.guild_id, t.registration_start, t.registration_end, t.min_participants, t.max_participants;

-- View for player achievements summary
CREATE OR REPLACE VIEW player_achievements_summary AS
SELECT 
    p.id as player_id,
    p.discord_id,
    p.username,
    COUNT(a.id) as achievements_unlocked,
    get_achievement_completion_percentage(p.id) as completion_percentage,
    ps.overall_risk_score,
    ps.risk_level as security_risk_level
FROM players p
LEFT JOIN achievements a ON p.id = a.player_id
LEFT JOIN player_security_profiles ps ON p.id = ps.player_id
GROUP BY p.id, p.discord_id, p.username, ps.overall_risk_score, ps.risk_level;

-- View for security events summary
CREATE OR REPLACE VIEW security_events_summary AS
SELECT 
    guild_id,
    event_type,
    security_level,
    COUNT(*) as event_count,
    AVG(risk_score) as avg_risk_score,
    MAX(created_at) as last_event
FROM security_events
WHERE is_resolved = false
GROUP BY guild_id, event_type, security_level
ORDER BY guild_id, security_level DESC, event_count DESC;

-- ========================================
-- INITIAL DATA
-- ========================================

-- Insert default achievement progress for existing players
INSERT INTO achievement_progress (player_id, achievement_type, current_progress, target_progress)
SELECT 
    p.id,
    'matches_10'::achievement_type,
    0,
    10
FROM players p
WHERE NOT EXISTS (
    SELECT 1 FROM achievement_progress ap 
    WHERE ap.player_id = p.id AND ap.achievement_type = 'matches_10'
);

INSERT INTO achievement_progress (player_id, achievement_type, current_progress, target_progress)
SELECT 
    p.id,
    'matches_50'::achievement_type,
    0,
    50
FROM players p
WHERE NOT EXISTS (
    SELECT 1 FROM achievement_progress ap 
    WHERE ap.player_id = p.id AND ap.achievement_type = 'matches_50'
);

INSERT INTO achievement_progress (player_id, achievement_type, current_progress, target_progress)
SELECT 
    p.id,
    'matches_100'::achievement_type,
    0,
    100
FROM players p
WHERE NOT EXISTS (
    SELECT 1 FROM achievement_progress ap 
    WHERE ap.player_id = p.id AND ap.achievement_type = 'matches_100'
);

-- Insert default security rules
INSERT INTO security_rules (guild_id, rule_name, rule_type, parameters, threshold, actions)
VALUES 
(0, 'Rating Spike Detection', 'rating_spike', '{"max_change": 100, "time_window": 24}', 0.7, '{"commands": ["flag_player", "notify_admin"]}'),
(0, 'Suspicious Match Detection', 'match_pattern', '{"min_duration": 120, "max_win_rate": 0.9}', 0.8, '{"commands": ["flag_match", "review_required"]}'),
(0, 'Multiple Account Detection', 'multiple_accounts', '{"max_rating_gain": 200, "time_window": 168}', 0.6, '{"commands": ["investigate_player", "restrict_account"]}');

-- ========================================
-- COMMENTS
-- ========================================

COMMENT ON TABLE achievements IS 'Player achievements and accomplishments';
COMMENT ON TABLE achievement_progress IS 'Progress tracking for hidden achievements';
COMMENT ON TABLE tournaments IS 'Tournament organization and management';
COMMENT ON TABLE tournament_participants IS 'Tournament participants and their performance';
COMMENT ON TABLE tournament_matches IS 'Individual matches within tournaments';
COMMENT ON TABLE security_events IS 'Security events and suspicious activity detection';
COMMENT ON TABLE player_security_profiles IS 'Player security profiles and risk assessment';
COMMENT ON TABLE match_integrity_checks IS 'Match integrity verification and scoring';
COMMENT ON TABLE security_rules IS 'Configurable security rules and thresholds';

COMMENT ON FUNCTION can_tournament_start(INTEGER) IS 'Check if tournament can start based on participant count';
COMMENT ON FUNCTION get_achievement_completion_percentage(INTEGER) IS 'Calculate achievement completion percentage for a player';
COMMENT ON FUNCTION get_player_security_risk_level(INTEGER) IS 'Get current security risk level for a player';

-- ========================================
-- MIGRATION COMPLETE
-- ========================================

-- Log migration completion
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('005_enhanced_features', NOW())
ON CONFLICT (version) DO NOTHING;