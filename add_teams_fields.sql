-- Add Teams connection fields to users table
-- Run this SQL manually in your database

-- Add Teams connection fields
ALTER TABLE users ADD COLUMN teams_connected BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN teams_user_id VARCHAR(100);
ALTER TABLE users ADD COLUMN teams_tenant_id VARCHAR(100);
ALTER TABLE users ADD COLUMN teams_user_token VARCHAR(500);
ALTER TABLE users ADD COLUMN teams_scope VARCHAR(500);
ALTER TABLE users ADD COLUMN teams_authed_at TIMESTAMP WITH TIME ZONE;

-- Update existing users to have teams_connected = FALSE by default
UPDATE users SET teams_connected = FALSE WHERE teams_connected IS NULL;

-- Optional: Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_teams_connected ON users(teams_connected);
CREATE INDEX IF NOT EXISTS idx_users_teams_tenant_id ON users(teams_tenant_id);

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name LIKE 'teams_%'
ORDER BY column_name;
