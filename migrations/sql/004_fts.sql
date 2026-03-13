BEGIN;

CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
USING fts5(
    object_name,
    object_class,
    ocr_text,
    raw_payload_json,
    content='observations',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
USING fts5(
    event_type,
    summary,
    payload_json,
    content='events',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS ocr_results_fts
USING fts5(
    raw_text,
    fields_json,
    content='ocr_results',
    content_rowid='rowid'
);

COMMIT;
