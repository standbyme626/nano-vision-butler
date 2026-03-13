<!-- source: 迁移版本草案.md | id: 27ucay -->
BEGIN;

CREATE VIEW IF NOT EXISTS world_state_view AS
SELECT
    d.camera_id,
    d.status AS device_status,
    d.last_seen,
    z.zone_id,
    z.state_value AS zone_state_value,
    z.state_confidence AS zone_state_confidence,
    z.fresh_until AS zone_fresh_until,
    z.is_stale AS zone_is_stale
FROM devices d
LEFT JOIN zone_states z
ON d.camera_id = z.camera_id;

CREATE VIEW IF NOT EXISTS active_notification_rules_view AS
SELECT
    nr.id,
    nr.user_id,
    u.telegram_chat_id,
    nr.rule_name,
    nr.trigger_type,
    nr.target_scope,
    nr.condition_json,
    nr.cooldown_sec,
    nr.last_triggered_at
FROM notification_rules nr
JOIN users u
ON nr.user_id = u.id
WHERE nr.is_enabled = 1
  AND u.is_allowed = 1;

COMMIT;
