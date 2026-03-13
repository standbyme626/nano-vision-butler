name: last_seen
description: Resolve where and when an object was last observed, with stale-aware fallback.
trigger_patterns:
  - "where did I last see"
  - "when was object last seen"
  - "last appearance of object"
  - "find last seen package/person"
allowed_tools:
  - last_seen_object
  - evaluate_staleness
  - take_snapshot
allowed_resources:
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
  rules:
    - "Call last_seen_object for factual lookup."
    - "Run evaluate_staleness before final claim when user asks about current relevance."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
state_effects:
  reads:
    - last_observation
    - freshness_policy
  writes:
    - none_direct
fallback_rules:
  - "If no last_seen record exists, return not_found and suggest snapshot recheck."
  - "If stale or fallback_required=true, trigger take_snapshot when permissions allow."
  - "If snapshot unavailable, return stale answer with explicit uncertainty."
steps:
  - "Extract object_name and optional camera_id/zone_id filters."
  - "Call last_seen_object."
  - "Call evaluate_staleness for current-validity check."
  - "If stale, optionally call take_snapshot for revalidation."
  - "Return last_seen location/time plus freshness signal."
output_schema:
  answer: string
  last_seen:
    object_name: string
    camera_id: string_or_null
    zone_id: string_or_null
    observed_at: iso8601_or_null
  freshness:
    fresh_until: iso8601_or_null
    is_stale: bool
    fallback_required: bool
  confidence: float_or_null
  next_action: string_or_null
  trace_id: string_or_null
