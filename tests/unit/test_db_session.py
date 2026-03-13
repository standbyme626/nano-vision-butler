from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from src.db.session import create_connection


class SQLiteSessionThreadingTests(unittest.TestCase):
    def test_create_connection_allows_cross_thread_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vision_butler_db_thread_") as tmp:
            db_path = Path(tmp) / "threading.db"
            conn = create_connection(db_path)
            try:
                conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
                conn.commit()

                errors: list[str] = []

                def worker() -> None:
                    try:
                        conn.execute("INSERT INTO items(value) VALUES (?)", ("ok",))
                        conn.commit()
                    except Exception as exc:  # pragma: no cover - regression guard
                        errors.append(str(exc))

                thread = threading.Thread(target=worker)
                thread.start()
                thread.join()

                self.assertEqual(errors, [])
                row = conn.execute("SELECT value FROM items LIMIT 1").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["value"], "ok")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
