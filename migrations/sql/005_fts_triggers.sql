BEGIN;

CREATE TRIGGER IF NOT EXISTS observations_ai
AFTER INSERT ON observations
BEGIN
    INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS observations_ad
AFTER DELETE ON observations
BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS observations_au
AFTER UPDATE ON observations
BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);

    INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_ai
AFTER INSERT ON events
BEGIN
    INSERT INTO events_fts(rowid, event_type, summary, payload_json)
    VALUES (new.rowid, new.event_type, new.summary, new.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_ad
AFTER DELETE ON events
BEGIN
    INSERT INTO events_fts(events_fts, rowid, event_type, summary, payload_json)
    VALUES ('delete', old.rowid, old.event_type, old.summary, old.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_au
AFTER UPDATE ON events
BEGIN
    INSERT INTO events_fts(events_fts, rowid, event_type, summary, payload_json)
    VALUES ('delete', old.rowid, old.event_type, old.summary, old.payload_json);

    INSERT INTO events_fts(rowid, event_type, summary, payload_json)
    VALUES (new.rowid, new.event_type, new.summary, new.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_ai
AFTER INSERT ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
    VALUES (new.rowid, new.raw_text, new.fields_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_ad
AFTER DELETE ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(ocr_results_fts, rowid, raw_text, fields_json)
    VALUES ('delete', old.rowid, old.raw_text, old.fields_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_au
AFTER UPDATE ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(ocr_results_fts, rowid, raw_text, fields_json)
    VALUES ('delete', old.rowid, old.raw_text, old.fields_json);

    INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
    VALUES (new.rowid, new.raw_text, new.fields_json);
END;

COMMIT;
