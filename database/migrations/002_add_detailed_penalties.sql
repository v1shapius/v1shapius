-- Migration: Add detailed restart penalty configuration
-- Date: 2024-01-01
-- Description: Add JSON field for detailed restart penalty tiers

-- Add new column for detailed penalty configuration
ALTER TABLE penalty_settings 
ADD COLUMN IF NOT EXISTS restart_penalties JSONB DEFAULT '{
    "free_restarts": 2,
    "penalty_tiers": {
        "3": 5,
        "4": 15,
        "5": 999
    }
}' NOT NULL;

-- Add index for JSON field queries
CREATE INDEX IF NOT EXISTS idx_penalty_settings_restart_penalties ON penalty_settings USING GIN (restart_penalties);

-- Add comment for documentation
COMMENT ON COLUMN penalty_settings.restart_penalties IS 'Detailed restart penalty configuration with tiers and free restarts';

-- Update existing records to have default detailed penalties
UPDATE penalty_settings 
SET restart_penalties = '{
    "free_restarts": 2,
    "penalty_tiers": {
        "3": 5,
        "4": 15,
        "5": 999
    }
}'
WHERE restart_penalties IS NULL;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 002_add_detailed_penalties completed successfully';
END $$;