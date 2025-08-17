-- Migration: Update season management
-- Date: 2024-01-01
-- Description: Add season end management fields and update season structure

-- Add new columns to seasons table
ALTER TABLE seasons 
ADD COLUMN IF NOT EXISTS is_ending BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS is_rating_locked BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS season_end_warning_sent BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS new_matches_blocked BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS rating_calculation_locked BOOLEAN DEFAULT false NOT NULL;

-- Update existing seasons to have proper end_date if null
UPDATE seasons 
SET end_date = start_date + INTERVAL '30 days'
WHERE end_date IS NULL;

-- Make end_date NOT NULL
ALTER TABLE seasons ALTER COLUMN end_date SET NOT NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_seasons_is_active ON seasons(is_active);
CREATE INDEX IF NOT EXISTS idx_seasons_is_ending ON seasons(is_ending);
CREATE INDEX IF NOT EXISTS idx_seasons_end_date ON seasons(end_date);

-- Add comments for documentation
COMMENT ON COLUMN seasons.is_ending IS 'Season is in ending phase';
COMMENT ON COLUMN seasons.is_rating_locked IS 'Rating calculation is locked';
COMMENT ON COLUMN seasons.season_end_warning_sent IS 'Warning about season end has been sent to players';
COMMENT ON COLUMN seasons.new_matches_blocked IS 'New matches are blocked from creation';
COMMENT ON COLUMN seasons.rating_calculation_locked IS 'Rating calculation is locked';

-- Create function to check if season should block new matches
CREATE OR REPLACE FUNCTION should_block_new_matches(season_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    season_record RECORD;
BEGIN
    SELECT * INTO season_record FROM seasons WHERE id = season_id;
    
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Check if season is ending soon (within 7 days)
    IF season_record.end_date <= NOW() + INTERVAL '7 days' THEN
        RETURN true;
    END IF;
    
    -- Check if explicitly blocked
    IF season_record.new_matches_blocked THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Create function to get season status description
CREATE OR REPLACE FUNCTION get_season_status_description(season_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    season_record RECORD;
    days_until_end INTEGER;
BEGIN
    SELECT * INTO season_record FROM seasons WHERE id = season_id;
    
    IF NOT FOUND THEN
        RETURN 'Не найден';
    END IF;
    
    IF NOT season_record.is_active THEN
        RETURN 'Завершен';
    END IF;
    
    IF season_record.is_ending THEN
        RETURN 'Завершается';
    END IF;
    
    days_until_end := EXTRACT(DAY FROM (season_record.end_date - NOW()));
    
    IF days_until_end <= 7 AND days_until_end > 0 THEN
        RETURN 'Завершается через ' || days_until_end || ' дней';
    END IF;
    
    RETURN 'Активен';
END;
$$ LANGUAGE plpgsql;

-- Create view for active seasons with status
CREATE OR REPLACE VIEW active_seasons_status AS
SELECT 
    id,
    name,
    start_date,
    end_date,
    is_active,
    is_ending,
    is_rating_locked,
    new_matches_blocked,
    rating_calculation_locked,
    EXTRACT(DAY FROM (end_date - NOW())) as days_until_end,
    get_season_status_description(id) as status_description,
    should_block_new_matches(id) as should_block_matches
FROM seasons
WHERE is_active = true;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 004_update_season_management completed successfully';
END $$;