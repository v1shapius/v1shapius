-- Migration: Add referee system
-- Date: 2024-01-01
-- Description: Add referee system tables and update matches table

-- Create referees table
CREATE TABLE IF NOT EXISTS referees (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    username VARCHAR(100) NOT NULL,
    guild_id BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    can_annul_matches BOOLEAN DEFAULT true NOT NULL,
    can_modify_results BOOLEAN DEFAULT true NOT NULL,
    can_resolve_disputes BOOLEAN DEFAULT true NOT NULL,
    cases_resolved INTEGER DEFAULT 0 NOT NULL,
    matches_annulled INTEGER DEFAULT 0 NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create referee_cases table
CREATE TABLE IF NOT EXISTS referee_cases (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    referee_id BIGINT,
    case_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'opened' NOT NULL,
    reported_by BIGINT NOT NULL,
    problem_description TEXT NOT NULL,
    evidence TEXT,
    referee_notes TEXT,
    resolution_type VARCHAR(50),
    resolution_details TEXT,
    resolution_time BIGINT,
    stage_when_reported VARCHAR(50) NOT NULL,
    additional_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add referee-related columns to matches table
ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS referee_id BIGINT,
ADD COLUMN IF NOT EXISTS referee_intervention_stage VARCHAR(50),
ADD COLUMN IF NOT EXISTS referee_intervention_reason TEXT,
ADD COLUMN IF NOT EXISTS referee_intervention_time BIGINT,
ADD COLUMN IF NOT EXISTS referee_resolution TEXT,
ADD COLUMN IF NOT EXISTS referee_resolution_time BIGINT,
ADD COLUMN IF NOT EXISTS winner_id INTEGER REFERENCES players(id),
ADD COLUMN IF NOT EXISTS annulment_reason TEXT;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_referees_guild_id ON referees(guild_id);
CREATE INDEX IF NOT EXISTS idx_referees_discord_id ON referees(discord_id);
CREATE INDEX IF NOT EXISTS idx_referee_cases_match_id ON referee_cases(match_id);
CREATE INDEX IF NOT EXISTS idx_referee_cases_status ON referee_cases(status);
CREATE INDEX IF NOT EXISTS idx_referee_cases_referee_id ON referee_cases(referee_id);
CREATE INDEX IF NOT EXISTS idx_matches_referee_id ON matches(referee_id);

-- Add triggers for updated_at timestamps
CREATE TRIGGER update_referees_updated_at BEFORE UPDATE ON referees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_referee_cases_updated_at BEFORE UPDATE ON referee_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE referees IS 'Referee information and permissions';
COMMENT ON TABLE referee_cases IS 'Referee intervention cases and their resolutions';
COMMENT ON COLUMN matches.referee_id IS 'Discord ID of assigned referee';
COMMENT ON COLUMN matches.referee_intervention_stage IS 'Match stage when referee was called';
COMMENT ON COLUMN matches.referee_intervention_reason IS 'Reason for referee intervention';
COMMENT ON COLUMN matches.referee_intervention_time IS 'Timestamp when referee was called';
COMMENT ON COLUMN matches.referee_resolution IS 'How referee resolved the issue';
COMMENT ON COLUMN matches.referee_resolution_time IS 'Timestamp when referee resolved';
COMMENT ON COLUMN matches.winner_id IS 'Winner player ID';
COMMENT ON COLUMN matches.annulment_reason IS 'Reason for match annulment';

-- Create ENUM types for referee cases
DO $$ BEGIN
    CREATE TYPE case_type AS ENUM (
        'draft_dispute', 'stream_issue', 'time_dispute', 'result_dispute', 
        'rule_violation', 'technical_issue', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE case_status AS ENUM (
        'opened', 'assigned', 'in_progress', 'resolved', 'closed'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE resolution_type AS ENUM (
        'continue_match', 'modify_results', 'replay_game', 'annull_match', 'warning_issued', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Update existing referee_cases table to use ENUMs
ALTER TABLE referee_cases 
ALTER COLUMN case_type TYPE case_type USING case_type::case_type,
ALTER COLUMN status TYPE case_status USING status::case_status,
ALTER COLUMN resolution_type TYPE resolution_type USING resolution_type::resolution_type;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 003_add_referee_system completed successfully';
END $$;