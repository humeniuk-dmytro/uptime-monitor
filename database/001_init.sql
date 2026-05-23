-- Idempotent migration: safe to run multiple times

CREATE TABLE IF NOT EXISTS monitors (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(255)    NOT NULL,
    url                 VARCHAR(2048)   NOT NULL,
    check_interval_sec  SMALLINT UNSIGNED NOT NULL DEFAULT 60,
    expected_status     SMALLINT UNSIGNED NOT NULL DEFAULT 200,
    timeout_sec         TINYINT UNSIGNED  NOT NULL DEFAULT 10,
    state               ENUM('unknown', 'up', 'down') NOT NULL DEFAULT 'unknown',
    status              ENUM('active', 'paused', 'deleted') NOT NULL DEFAULT 'active',
    webhook_url         VARCHAR(2048)   NULL,
    last_checked_at     DATETIME        NULL,
    consecutive_failures TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_interval CHECK (check_interval_sec >= 30),
    CONSTRAINT chk_timeout  CHECK (timeout_sec >= 1)
);

-- Index: worker шукає активні монітори по last_checked_at
CREATE INDEX IF NOT EXISTS idx_monitors_status_last_checked
    ON monitors (status, last_checked_at);


CREATE TABLE IF NOT EXISTS checks (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    monitor_id   INT UNSIGNED    NOT NULL,
    checked_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_code  SMALLINT UNSIGNED NULL,
    latency_ms   SMALLINT UNSIGNED NULL,
    is_ok        TINYINT(1)      NOT NULL DEFAULT 0,
    error_message VARCHAR(1024)  NULL,
    body_hash    CHAR(64)        NULL,

    CONSTRAINT fk_checks_monitor FOREIGN KEY (monitor_id)
        REFERENCES monitors (id) ON DELETE CASCADE
);

-- Index: history і uptime запити завжди по monitor_id + checked_at DESC
CREATE INDEX IF NOT EXISTS idx_checks_monitor_checked
    ON checks (monitor_id, checked_at DESC);


CREATE TABLE IF NOT EXISTS transitions (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    monitor_id  INT UNSIGNED    NOT NULL,
    from_state  ENUM('unknown', 'up', 'down') NOT NULL,
    to_state    ENUM('unknown', 'up', 'down') NOT NULL,
    at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_transitions_monitor FOREIGN KEY (monitor_id)
        REFERENCES monitors (id) ON DELETE CASCADE
);

-- Index: лог переходів по конкретному монітору
CREATE INDEX IF NOT EXISTS idx_transitions_monitor
    ON transitions (monitor_id, at DESC);
