BEGIN;

INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json
FROM observations
WHERE rowid NOT IN (SELECT rowid FROM observations_fts);

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json
FROM events
WHERE rowid NOT IN (SELECT rowid FROM events_fts);

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json
FROM ocr_results
WHERE rowid NOT IN (SELECT rowid FROM ocr_results_fts);

COMMIT;
