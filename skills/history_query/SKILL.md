name: history_query
description: Answer recent history and timeline questions using event memory and bounded time ranges.
trigger_patterns:
  - "what happened recently"
  - "timeline in last hour"
  - "recent events in zone"
  - "history of object"
  - "show latest alerts"
allowed_tools:
  - query_recent_events
  - get_world_state
allowed_resources:
  - resource://memory/events
  - resource://memory/observations
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
  deny_without_scope: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - event_at
  rules:
    - "Always treat history as time-bounded facts; require or infer a bounded range."
    - "If no time range is provided, default to recent window via query_recent_events."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
state_effects:
  reads:
    - recent_events
    - recent_observations
  writes:
    - none
fallback_rules:
  - "If query_recent_events returns empty, report no matching events and suggest broader range."
  - "If time parsing fails, fall back to latest N events with explicit disclaimer."
steps:
  - "Normalize filters: zone_id, object_name, start_time, end_time, limit."
  - "Call query_recent_events with bounded range."
  - "Sort and summarize into timeline bullets."
  - "If needed, call get_world_state for current context contrast."
  - "Return history summary plus explicit time window."
output_schema:
  answer: string
  time_window:
    start_time: iso8601_or_null
    end_time: iso8601_or_null
  items:
    - event_id: string
      event_type: string
      summary: string
      event_at: iso8601
  confidence: float_or_null
  freshness:
    basis: "event timestamps"
  next_action: string_or_null
  trace_id: string_or_null
