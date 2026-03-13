name: ocr_query
description: Handle OCR requests by selecting quick read or structured extraction based on output needs.
trigger_patterns:
  - "read text from image"
  - "extract fields from receipt/form"
  - "ocr this snapshot"
  - "parse text from media"
allowed_tools:
  - ocr_quick_read
  - ocr_extract_fields
  - take_snapshot
allowed_resources:
  - resource://policy/freshness
auth_policy:
  require_access_check: true
  enforce_visibility_scope: true
freshness_policy:
  policy_resource: resource://policy/freshness
  freshness_fields:
    - confidence
  rules:
    - "If user asks conceptual OCR guidance and no media/input_uri is provided, answer directly."
    - "If user asks to read text from media and no field schema is required, call ocr_quick_read."
    - "If user asks structured fields, call ocr_extract_fields with field_schema."
memory_write_policy:
  mode: read_only
  direct_db_write: forbidden
  allowed_side_effect_tools:
    - take_snapshot
state_effects:
  reads:
    - OCR result payloads
  writes:
    - none_direct
fallback_rules:
  - "If media_id/input_uri missing but camera context exists, trigger take_snapshot then OCR."
  - "If structured extraction fails, fall back to ocr_quick_read and return raw text."
  - "If confidence is low, include low-confidence warning and ask user to retry with clearer media."
steps:
  - "If request is non-operational guidance only, answer directly."
  - "Resolve media source: media_id or input_uri; snapshot only when needed."
  - "Select ocr_extract_fields when field_schema exists, else ocr_quick_read."
  - "Normalize OCR output into user-facing text and optional fields_json."
  - "Return confidence and retry advice when needed."
output_schema:
  answer: string
  ocr:
    mode: "quick_read|extract_fields|direct_answer"
    raw_text: string_or_null
    fields_json: object_or_null
  confidence: float_or_null
  warnings:
    - string
  trace_id: string_or_null
