name: device_status
description: Report edge device health, connectivity, and operational status using backend telemetry.
trigger_patterns:
  - "is device online"
  - "device health status"
  - "camera node status"
  - "check edge runtime"
allowed_tools:
  - device_status
  - take_snapshot
  - get_recent_clip
allowed_resources:
  - resource://devices/status
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
  sensitive_action_audit_required: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - last_seen
    - status
  rules:
    - "Call device_status for factual health checks."
    - "If status looks stale/offline, avoid claiming live view availability."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
    - get_recent_clip
state_effects:
  reads:
    - device_status_rows
  writes:
    - none_direct
fallback_rules:
  - "If device_status returns not found, return not_found with device_id echo."
  - "If status is offline, skip media actions and return recovery guidance."
  - "If status is degraded but online, optional snapshot/clip can validate camera path."
steps:
  - "Parse device_id."
  - "Call device_status."
  - "If online and user requests validation evidence, call take_snapshot or get_recent_clip."
  - "Summarize status, telemetry, and recommended action."
output_schema:
  answer: string
  device:
    device_id: string
    status: string
    effective_status: string_or_null
    last_seen: iso8601_or_null
    telemetry: object_or_null
  validation_media:
    media_id: string_or_null
    clip_uri: string_or_null
  next_action: string_or_null
  trace_id: string_or_null
