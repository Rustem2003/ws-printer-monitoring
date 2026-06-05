-- ============================================================
-- Printer Monitoring System — Initial Schema
-- PostgreSQL
-- ============================================================

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO roles (name, description) VALUES
    ('super_admin', 'Full system access, user management, system settings'),
    ('administrator', 'Printer management, scanning, notification settings'),
    ('operator', 'View status, manual scan trigger'),
    ('viewer', 'Dashboard and report view only')
ON CONFLICT (name) DO NOTHING;

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(256) UNIQUE,
    hashed_password VARCHAR(256) NOT NULL,
    full_name VARCHAR(256),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    tenant_id INTEGER REFERENCES tenants(id),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);

-- Default super admin (password: admin123 — change on first login!)
INSERT INTO users (username, email, hashed_password, full_name, role_id)
VALUES (
    'admin',
    'admin@printer-monitoring.local',
    '$2b$12$LJ3m4ys3Lk0TSwHhJRNvwemYqfGxq.5QJmZPhXAx.p5NPv8GqDlSi',
    'Super Admin',
    1
) ON CONFLICT (username) DO NOTHING;

-- Printers
CREATE TABLE IF NOT EXISTS printers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(17),
    vendor VARCHAR(128),
    model VARCHAR(256),
    serial_number VARCHAR(256),
    firmware_version VARCHAR(128),
    location VARCHAR(256),
    is_color BOOLEAN DEFAULT FALSE,
    is_online BOOLEAN DEFAULT FALSE,
    snmp_version VARCHAR(8) DEFAULT '2c',
    snmp_community VARCHAR(64) DEFAULT 'public',
    snmp_port INTEGER DEFAULT 161,
    last_seen TIMESTAMPTZ,
    tenant_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_printers_ip ON printers(ip_address);
CREATE INDEX IF NOT EXISTS idx_printers_online ON printers(is_online);
CREATE INDEX IF NOT EXISTS idx_printers_vendor ON printers(vendor);

-- Consumables
CREATE TABLE IF NOT EXISTS consumables (
    id SERIAL PRIMARY KEY,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    oid VARCHAR(256),
    current_level FLOAT,
    max_capacity INTEGER,
    threshold_warning FLOAT DEFAULT 20.0,
    threshold_critical FLOAT DEFAULT 5.0,
    unit VARCHAR(32) DEFAULT '%',
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consumables_printer ON consumables(printer_id);

-- Printer Status
CREATE TABLE IF NOT EXISTS printer_status (
    id SERIAL PRIMARY KEY,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    status_code INTEGER,
    status_text VARCHAR(128),
    page_count INTEGER,
    uptime_seconds INTEGER,
    cpu_load FLOAT,
    memory_total INTEGER,
    memory_free INTEGER,
    temperature FLOAT,
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    raw_snmp_data TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_status_printer ON printer_status(printer_id);
CREATE INDEX IF NOT EXISTS idx_status_recorded ON printer_status(recorded_at);

-- Printer Events
CREATE TABLE IF NOT EXISTS printer_events (
    id SERIAL PRIMARY KEY,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) DEFAULT 'info',
    message VARCHAR(512),
    details TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_by INTEGER,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_printer ON printer_events(printer_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON printer_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON printer_events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_severity ON printer_events(severity);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    message VARCHAR(1024) NOT NULL,
    severity VARCHAR(16) DEFAULT 'info',
    status VARCHAR(16) DEFAULT 'sent',
    error_message VARCHAR(512),
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);

-- Telegram Chats
CREATE TABLE IF NOT EXISTS telegram_chats (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(256),
    chat_type VARCHAR(32) DEFAULT 'group',
    is_active INTEGER DEFAULT 1,
    subscribed_events TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Telegram chats: добавляйте через UI (раздел "Telegram"). Без seed-данных.

-- Scan Jobs
CREATE TABLE IF NOT EXISTS scan_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(32) DEFAULT 'discovery',
    status VARCHAR(32) DEFAULT 'pending',
    subnet VARCHAR(45),
    method VARCHAR(32) DEFAULT 'snmp_broadcast',
    devices_found INTEGER DEFAULT 0,
    devices_added INTEGER DEFAULT 0,
    progress FLOAT DEFAULT 0.0,
    error_message VARCHAR(512),
    started_by INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Tokens
CREATE TABLE IF NOT EXISTS api_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(256) UNIQUE NOT NULL,
    name VARCHAR(256),
    user_id INTEGER,
    permissions TEXT,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id INTEGER,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);

-- ============================================================
-- Seed data: default consumable thresholds for color printing
-- These are applied dynamically — thresholds stored here for reference
-- ============================================================
-- Black:   warning 20%, critical 10%
-- Cyan:    warning 10%, critical 5%
-- Magenta: warning 10%, critical 5%
-- Yellow:  warning 10%, critical 0%
