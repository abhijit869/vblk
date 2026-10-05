import unittest
import sqlite3
import json

from jarvis_core.memory import SQLiteMemoryEngine
from jarvis_core.protocol import ToolRequest, ToolResult, RiskLevel

class SQLiteMemoryEngineTests(unittest.TestCase):
    def test_create_session(self) -> None:
        db = SQLiteMemoryEngine()
        session_id = db.create_session()
        self.assertIsInstance(session_id, str)
        
        cursor = db._conn.execute("SELECT count(*) FROM sessions WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_record_tool_call(self) -> None:
        db = SQLiteMemoryEngine()
        session_id = db.create_session()
        
        request = ToolRequest(tool="system.cpu", arguments={"x": 1})
        result = ToolResult(
            request_id=request.request_id,
            tool="system.cpu",
            status="ok",
            risk=RiskLevel.READ,
            duration_ms=10,
            data={"cpu": 4},
            redacted=False,
            truncated=False,
        )
        
        call_id = db.record_tool_call(session_id, request, result)
        
        cursor = db._conn.execute("SELECT tool_name, arguments, result FROM tool_calls WHERE call_id = ?", (call_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "system.cpu")
        self.assertEqual(json.loads(row[1]), {"x": 1})
        self.assertEqual(json.loads(row[2]), {"cpu": 4})

if __name__ == "__main__":
    unittest.main()
