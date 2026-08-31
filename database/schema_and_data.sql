-- ============================================================
-- RGB-Pose Hub — Relational Database Schema & Initial Data
-- Database Engine: SQLite / PostgreSQL compatible
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- 1. Users Table
-- Stores user credentials, roles, 2FA status, and activity counts
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(20) NOT NULL DEFAULT 'researcher',
    is_active BOOLEAN DEFAULT 1,
    is_2fa_enabled BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    total_analyses INTEGER DEFAULT 0,
    total_uploads INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ------------------------------------------------------------
-- 2. Two-Factor Authentication Secrets Table
-- Stores TOTP secret keys and setup status
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS two_factor_secrets (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    secret VARCHAR(32) NOT NULL,
    is_verified BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 3. Sessions Table
-- Tracks active JWT tokens and device sessions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    revoked_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 4. Activity Logs Table
-- Complete chronological log of user operations (SRS requirement)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    metadata_json TEXT,
    ip_address VARCHAR(45),
    status VARCHAR(20) DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at);

-- ------------------------------------------------------------
-- Initial Seed Data: Default Demo Researcher Account
-- Password: Password123! (bcrypt hashed)
-- ------------------------------------------------------------
INSERT OR IGNORE INTO users (id, email, username, password_hash, full_name, role, is_active, is_2fa_enabled, created_at)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'admin@rgbposehub.org',
    'lead_researcher',
    '$2b$12$KIXV8bQ.1gK3N4/y0N5lre6V3zN2P1c10F.nL6p6vQzE5X/Y0N5lr',
    'Lead Researcher',
    'admin',
    1,
    1,
    CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO two_factor_secrets (id, user_id, secret, is_verified, created_at, verified_at)
VALUES (
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'JBSWY3DPEHPK3PXP',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
