name: zone_state
description: Resolve current zone-level state with stale checks and bounded fallback.
trigger_patterns:
  - "is zone occupied now"
  - "state of this area"
  - "entry zone status"
  - "what is happening in zone"
allowed_tools:
  - get_zone_state
  - describe_scene
  - get_world_state
  - take_snapshot
allowed_resources:
  - resource://memory/zone_states
  - resource://memory/observations
  - resource://memory/events
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - fresh_until
    - is_stale
    - state_confidence
  rules:
    - "Call get_zone_state for zone factual status."
    - "If user asks richer context, add describe_scene."
    - "When stale, attempt snapshot recheck before final assertion."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
state_effects:
  reads:
    - zone_state_snapshot
    - observations
    - events
  writes:
    - none_direct
fallback_rules:
  - "If get_zone_state lacks coverage, call describe_scene for supporting evidence."
  - "If zone context unavailable, fall back to get_world_state camera-level summary."
  - "If stale and snapshot unavailable, return stale warning and recheck suggestion."
steps:
  - "Extract camera_id and zone_id."
  - "Call get_zone_state."
  - "If user asks for details, call describe_scene."
  - "If stale, call take_snapshot; if not possible, call get_world_state."
  - "Return zone answer with stale marker and recommended action."
output_schema:
  answer: string
  zone_state:
    camera_id: string
    zone_id: string
    state: string_or_null
    reason_code: string_or_null
  evidence:
    observations_count: int
    events_count: int
  confidence: float_or_null
  freshness:
    fresh_until: iso8601_or_null
    is_stale: bool
  next_action: string_or_null
  trace_id: string_or_null
