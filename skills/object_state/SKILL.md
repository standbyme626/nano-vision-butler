name: object_state
description: Determine the most likely current state of an object with explicit stale and fallback handling.
trigger_patterns:
  - "is the package still there"
  - "current state of object"
  - "object present or moved"
  - "where is object now"
allowed_tools:
  - get_object_state
  - evaluate_staleness
  - last_seen_object
  - take_snapshot
allowed_resources:
  - resource://memory/object_states
  - resource://memory/observations
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - fresh_until
    - is_stale
    - fallback_required
    - state_confidence
  rules:
    - "Always call get_object_state for factual state requests."
    - "Call evaluate_staleness before asserting current state."
    - "Treat is_stale=true or fallback_required=true as recheck-needed."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
state_effects:
  reads:
    - object_state_snapshot
    - last_observation
  writes:
    - none_direct
fallback_rules:
  - "If get_object_state returns unknown, call last_seen_object for best-effort context."
  - "If stale/fallback_required, trigger take_snapshot when possible."
  - "If recheck cannot run, answer probabilistically with uncertainty label."
steps:
  - "Normalize object_name plus optional camera/zone filters."
  - "Call get_object_state."
  - "Call evaluate_staleness with same filters."
  - "If stale or low confidence, call last_seen_object and optionally take_snapshot."
  - "Return state + confidence + fallback recommendation."
output_schema:
  answer: string
  state:
    object_name: string
    state: string_or_null
    reason_code: string_or_null
    camera_id: string_or_null
    zone_id: string_or_null
  confidence: float_or_null
  freshness:
    fresh_until: iso8601_or_null
    is_stale: bool
    fallback_required: bool
  fallback:
    executed: bool
    type: string_or_null
  trace_id: string_or_null
