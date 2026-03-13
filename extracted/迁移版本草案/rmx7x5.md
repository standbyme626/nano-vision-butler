<!-- source: 迁移版本草案.md | id: rmx7x5 -->
BEGIN;

CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_users_allowed
ON users(is_allowed);

CREATE INDEX IF NOT EXISTS idx_devices_status
ON devices(status);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen
ON devices(last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_observations_camera_time
ON observations(camera_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_zone_time
ON observations(zone_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_object_time
ON observations(object_name, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_track_id
ON observations(track_id);

CREATE INDEX IF NOT EXISTS idx_observations_source_event
ON observations(source_event_id);

CREATE INDEX IF NOT EXISTS idx_events_time
ON events(event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_time
ON events(event_type, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_zone_time
ON events(zone_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_object_time
ON events(object_name, event_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key
ON object_states(object_name, camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_object_states_stale
ON object_states(is_stale, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key
ON zone_states(camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_zone_states_stale
ON zone_states(is_stale, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_owner
ON media_items(owner_type, owner_id);

CREATE INDEX IF NOT EXISTS idx_media_created_at
ON media_items(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_sha256
ON media_items(sha256);

CREATE INDEX IF NOT EXISTS idx_audit_user_time
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_device_time
ON audit_logs(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trace
ON audit_logs(trace_id);

CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time
ON telegram_updates(status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time
ON telegram_updates(chat_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled
ON notification_rules(user_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_facts_scope
ON facts(scope);

CREATE INDEX IF NOT EXISTS idx_ocr_results_media
ON ocr_results(source_media_id);

CREATE INDEX IF NOT EXISTS idx_ocr_results_observation
ON ocr_results(source_observation_id);

COMMIT;
