name: scene_query
description: Resolve current camera or zone scene questions with freshness-aware evidence.
trigger_patterns:
  - "what is happening now"
  - "current scene"
  - "who is there now"
  - "is there anyone/package now"
  - "camera zone status"
allowed_tools:
  - describe_scene
  - get_world_state
  - take_snapshot
  - evaluate_staleness
allowed_resources:
  - resource://memory/zone_states
  - resource://memory/observations
  - resource://memory/events
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
  deny_without_camera_scope: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - fresh_until
    - is_stale
    - fallback_required
  rules:
    - "If the question is generic guidance with no factual claim, answer directly without tools."
    - "If the question asks about current facts, call describe_scene first."
    - "If describe_scene returns is_stale=true, run take_snapshot before final answer when possible."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
state_effects:
  reads:
    - zone_state
    - recent_observations
    - recent_events
  writes:
    - none_direct
fallback_rules:
  - "If describe_scene fails, use get_world_state and mark lower confidence."
  - "If stale and snapshot cannot run, return stale warning plus suggested recheck."
  - "If no evidence exists, return insufficient_evidence and ask for camera_id/zone_id."
steps:
  - "Parse camera_id and zone_id from user context."
  - "Choose direct answer only for non-factual guidance requests."
  - "For factual scene requests, call describe_scene."
  - "If stale, call take_snapshot and re-answer with fresh evidence."
  - "Return concise answer with evidence and freshness metadata."
output_schema:
  answer: string
  evidence:
    - source: string
      id: string
      observed_at: iso8601
  confidence: float_or_null
  freshness:
    fresh_until: iso8601_or_null
    is_stale: bool
    fallback_required: bool
  next_action: string_or_null
  trace_id: string_or_null
