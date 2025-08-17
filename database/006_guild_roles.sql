-- Migration 006: Guild Roles System
-- Adds support for managing guild roles with automatic assignment and tagging

-- Create guilds table
CREATE TABLE IF NOT EXISTS guilds (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    guild_name VARCHAR(255) NOT NULL,
    prefix VARCHAR(10) DEFAULT '!',
    language VARCHAR(10) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create guild_roles table
CREATE TABLE IF NOT EXISTS guild_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    role_type VARCHAR(50) NOT NULL,
    discord_role_id BIGINT NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    auto_assign BOOLEAN DEFAULT FALSE,
    permissions TEXT, -- JSON string of permissions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create guild_role_permissions table
CREATE TABLE IF NOT EXISTS guild_role_permissions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    role_type VARCHAR(50) NOT NULL,
    permission_name VARCHAR(100) NOT NULL,
    permission_description TEXT,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create guild_member_roles table for tracking member role assignments
CREATE TABLE IF NOT EXISTS guild_member_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES guild_roles(id),
    assigned_by BIGINT, -- Discord ID of who assigned the role
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- For temporary role assignments
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_guilds_guild_id ON guilds(guild_id);
CREATE INDEX IF NOT EXISTS idx_guilds_active ON guilds(is_active);

CREATE INDEX IF NOT EXISTS idx_guild_roles_guild_id ON guild_roles(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_roles_type ON guild_roles(role_type);
CREATE INDEX IF NOT EXISTS idx_guild_roles_active ON guild_roles(is_active);
CREATE INDEX IF NOT EXISTS idx_guild_roles_discord_id ON guild_roles(discord_role_id);

CREATE INDEX IF NOT EXISTS idx_guild_role_permissions_guild_id ON guild_role_permissions(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_role_permissions_type ON guild_role_permissions(role_type);

CREATE INDEX IF NOT EXISTS idx_guild_member_roles_guild_id ON guild_member_roles(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_member_roles_member_id ON guild_member_roles(member_id);
CREATE INDEX IF NOT EXISTS idx_guild_member_roles_role_id ON guild_member_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_guild_member_roles_active ON guild_member_roles(is_active);

-- Add foreign key constraints
ALTER TABLE guild_roles ADD CONSTRAINT fk_guild_roles_guild_id 
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE;

ALTER TABLE guild_role_permissions ADD CONSTRAINT fk_guild_role_permissions_guild_id 
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE;

ALTER TABLE guild_member_roles ADD CONSTRAINT fk_guild_member_roles_guild_id 
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE;

-- Create unique constraints
ALTER TABLE guild_roles ADD CONSTRAINT uk_guild_roles_guild_type 
    UNIQUE (guild_id, role_type);

ALTER TABLE guild_role_permissions ADD CONSTRAINT uk_guild_role_permissions_guild_type_name 
    UNIQUE (guild_id, role_type, permission_name);

ALTER TABLE guild_member_roles ADD CONSTRAINT uk_guild_member_roles_guild_member_role 
    UNIQUE (guild_id, member_id, role_id);

-- Insert default role types and permissions
INSERT INTO guild_role_permissions (guild_id, role_type, permission_name, permission_description) VALUES
-- Player permissions (guild_id = 0 means default for all guilds)
(0, 'players', 'can_challenge', 'Может создавать вызовы на дуэли'),
(0, 'players', 'can_join_tournaments', 'Может участвовать в турнирах'),
(0, 'players', 'can_view_stats', 'Может просматривать статистику'),
(0, 'players', 'can_view_leaderboard', 'Может просматривать таблицу лидеров'),

-- Referee permissions
(0, 'referees', 'can_moderate_matches', 'Может модерировать матчи'),
(0, 'referees', 'can_resolve_disputes', 'Может разрешать споры'),
(0, 'referees', 'can_announce_results', 'Может объявлять результаты'),
(0, 'referees', 'can_view_admin_panel', 'Может просматривать админ панель'),

-- Admin permissions
(0, 'admins', 'can_manage_seasons', 'Может управлять сезонами'),
(0, 'admins', 'can_manage_tournaments', 'Может управлять турнирами'),
(0, 'admins', 'can_manage_roles', 'Может управлять ролями'),
(0, 'admins', 'can_view_security_logs', 'Может просматривать логи безопасности'),

-- Tournament organizer permissions
(0, 'tournament_organizers', 'can_create_tournaments', 'Может создавать турниры'),
(0, 'tournament_organizers', 'can_manage_tournaments', 'Может управлять турнирами'),
(0, 'tournament_organizers', 'can_announce_results', 'Может объявлять результаты');

-- Create view for active guild roles
CREATE OR REPLACE VIEW active_guild_roles AS
SELECT 
    gr.id,
    gr.guild_id,
    g.guild_name,
    gr.role_type,
    gr.discord_role_id,
    gr.role_name,
    gr.description,
    gr.auto_assign,
    gr.permissions,
    gr.created_at,
    gr.updated_at
FROM guild_roles gr
JOIN guilds g ON gr.guild_id = g.guild_id
WHERE gr.is_active = TRUE AND g.is_active = TRUE;

-- Create view for guild member roles
CREATE OR REPLACE VIEW guild_member_roles_view AS
SELECT 
    gmr.id,
    gmr.guild_id,
    g.guild_name,
    gmr.member_id,
    gr.role_type,
    gr.role_name,
    gr.discord_role_id,
    gmr.assigned_by,
    gmr.assigned_at,
    gmr.expires_at,
    gmr.is_active
FROM guild_member_roles gmr
JOIN guild_roles gr ON gmr.role_id = gr.id
JOIN guilds g ON gmr.guild_id = g.guild_id
WHERE gmr.is_active = TRUE AND gr.is_active = TRUE;

-- Create function to get member permissions
CREATE OR REPLACE FUNCTION get_member_permissions(p_guild_id BIGINT, p_member_id BIGINT)
RETURNS TABLE(permission_name VARCHAR(100), permission_description TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT grp.permission_name, grp.permission_description
    FROM guild_member_roles gmr
    JOIN guild_roles gr ON gmr.role_id = gr.id
    JOIN guild_role_permissions grp ON gr.guild_id = grp.guild_id AND gr.role_type = grp.role_type
    WHERE gmr.guild_id = p_guild_id 
      AND gmr.member_id = p_member_id 
      AND gmr.is_active = TRUE 
      AND gr.is_active = TRUE 
      AND grp.is_enabled = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create function to check if member has permission
CREATE OR REPLACE FUNCTION member_has_permission(p_guild_id BIGINT, p_member_id BIGINT, p_permission VARCHAR(100))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM get_member_permissions(p_guild_id, p_member_id)
        WHERE permission_name = p_permission
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to get role members
CREATE OR REPLACE FUNCTION get_role_members(p_guild_id BIGINT, p_role_type VARCHAR(50))
RETURNS TABLE(member_id BIGINT, assigned_at TIMESTAMP WITH TIME ZONE) AS $$
BEGIN
    RETURN QUERY
    SELECT gmr.member_id, gmr.assigned_at
    FROM guild_member_roles gmr
    JOIN guild_roles gr ON gmr.role_id = gr.id
    WHERE gmr.guild_id = p_guild_id 
      AND gr.role_type = p_role_type 
      AND gmr.is_active = TRUE 
      AND gr.is_active = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create function to auto-assign roles
CREATE OR REPLACE FUNCTION auto_assign_player_role(p_guild_id BIGINT, p_member_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_role_id INTEGER;
    v_match_count INTEGER;
BEGIN
    -- Check if member has played at least one match
    SELECT COUNT(*) INTO v_match_count
    FROM matches m
    JOIN players p ON (m.player1_id = p.id OR m.player2_id = p.id)
    WHERE p.discord_id = p_member_id AND m.status = 'complete';
    
    -- Only assign if member has played matches
    IF v_match_count > 0 THEN
        -- Get player role ID
        SELECT id INTO v_role_id
        FROM guild_roles
        WHERE guild_id = p_guild_id 
          AND role_type = 'players' 
          AND is_active = TRUE 
          AND auto_assign = TRUE;
        
        -- Assign role if found and not already assigned
        IF v_role_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM guild_member_roles 
            WHERE guild_id = p_guild_id 
              AND member_id = p_member_id 
              AND role_id = v_role_id 
              AND is_active = TRUE
        ) THEN
            INSERT INTO guild_member_roles (guild_id, member_id, role_id, assigned_by)
            VALUES (p_guild_id, p_member_id, v_role_id, NULL);
            
            RETURN TRUE;
        END IF;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-assign player role when match is completed
CREATE OR REPLACE FUNCTION trigger_auto_assign_player_role()
RETURNS TRIGGER AS $$
BEGIN
    -- Only trigger on match completion
    IF NEW.status = 'complete' AND OLD.status != 'complete' THEN
        -- Try to auto-assign player role for both players
        PERFORM auto_assign_player_role(NEW.guild_id, 
            (SELECT discord_id FROM players WHERE id = NEW.player1_id));
        PERFORM auto_assign_player_role(NEW.guild_id, 
            (SELECT discord_id FROM players WHERE id = NEW.player2_id));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on matches table
CREATE TRIGGER auto_assign_player_role_trigger
    AFTER UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION trigger_auto_assign_player_role();

-- Insert sample data for testing (optional)
-- This will be handled by the bot when it joins a guild

-- Grant permissions to bot user (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_bot_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_bot_user;

COMMENT ON TABLE guilds IS 'Configuration for Discord guilds/servers';
COMMENT ON TABLE guild_roles IS 'Role configurations for guilds';
COMMENT ON TABLE guild_role_permissions IS 'Permissions for different role types';
COMMENT ON TABLE guild_member_roles IS 'Role assignments for guild members';

COMMENT ON FUNCTION get_member_permissions IS 'Get all permissions for a guild member';
COMMENT ON FUNCTION member_has_permission IS 'Check if member has specific permission';
COMMENT ON FUNCTION get_role_members IS 'Get all members with a specific role type';
COMMENT ON FUNCTION auto_assign_player_role IS 'Automatically assign player role to member';