-- Migration: Add guild configuration fields
-- Date: 2024-01-01
-- Description: Add fields for match channel, leaderboard channel, audit channel, voice category, and instructions message

-- Add new columns to penalty_settings table
ALTER TABLE penalty_settings 
ADD COLUMN IF NOT EXISTS match_channel_id BIGINT,
ADD COLUMN IF NOT EXISTS leaderboard_channel_id BIGINT,
ADD COLUMN IF NOT EXISTS audit_channel_id BIGINT,
ADD COLUMN IF NOT EXISTS voice_category_id BIGINT,
ADD COLUMN IF NOT EXISTS instructions_message_id BIGINT;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_penalty_settings_match_channel ON penalty_settings(match_channel_id);
CREATE INDEX IF NOT EXISTS idx_penalty_settings_leaderboard_channel ON penalty_settings(leaderboard_channel_id);
CREATE INDEX IF NOT EXISTS idx_penalty_settings_audit_channel ON penalty_settings(audit_channel_id);
CREATE INDEX IF NOT EXISTS idx_penalty_settings_voice_category ON penalty_settings(voice_category_id);

-- Add comments for documentation
COMMENT ON COLUMN penalty_settings.match_channel_id IS 'Discord channel ID where matches can be created';
COMMENT ON COLUMN penalty_settings.leaderboard_channel_id IS 'Discord channel ID for leaderboard updates';
COMMENT ON COLUMN penalty_settings.audit_channel_id IS 'Discord channel ID for audit logs';
COMMENT ON COLUMN penalty_settings.voice_category_id IS 'Discord category ID for voice channels';
COMMENT ON COLUMN penalty_settings.instructions_message_id IS 'Discord message ID of pinned instructions';

-- Update existing records to have default values
UPDATE penalty_settings 
SET 
    match_channel_id = NULL,
    leaderboard_channel_id = NULL,
    audit_channel_id = NULL,
    voice_category_id = NULL,
    instructions_message_id = NULL
WHERE match_channel_id IS NULL;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_add_guild_settings completed successfully';
END $$;