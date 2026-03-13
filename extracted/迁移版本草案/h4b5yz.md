<!-- source: 迁移版本草案.md | id: h4b5yz -->
BEGIN;

INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json
FROM observations;

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json
FROM events;

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json
FROM ocr_results;

COMMIT;
