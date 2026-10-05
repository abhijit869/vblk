import unittest

from jarvis_core.core import JarvisCore
from jarvis_core.memory import SQLiteMemoryEngine


class CoreLoopTests(unittest.TestCase):
    def test_natural_language_cpu_request_runs_cpu_tool(self) -> None:
        response = JarvisCore().handle_text("What is my CPU usage?")

        self.assertEqual(response["selected_tool"], "system.cpu")
        self.assertEqual(response["ai"]["provider"], "mock")
        self.assertEqual(response["result"]["status"], "ok")
        self.assertEqual(response["result"]["risk"], 10)
        self.assertIn("cpu_count", response["result"]["data"])
        self.assertGreaterEqual(len(response["audit_records"]), 4)
        self.assertIsInstance(response["audit_records"][1]["timestamp"], float)
        self.assertEqual(response["audit_records"][1]["metadata"]["tool_calls"], 1)

    def test_natural_language_process_request_runs_process_tool(self) -> None:
        response = JarvisCore().handle_text("List running processes")

        self.assertEqual(response["selected_tool"], "process.list")
        self.assertEqual(response["result"]["status"], "ok")
        self.assertIsInstance(response["result"]["data"], list)

    def test_natural_language_terminal_request_runs_safe_command(self) -> None:
        response = JarvisCore().handle_text("Run terminal command")

        self.assertEqual(response["selected_tool"], "terminal.execute")
        self.assertEqual(response["result"]["status"], "ok")
        self.assertEqual(response["result"]["data"]["risk"], "READ")
        self.assertEqual(response["result"]["data"]["exit_code"], 0)



    def test_core_with_memory(self) -> None:
        db = SQLiteMemoryEngine()
        core = JarvisCore(memory_engine=db)
        response = core.handle_text("What is my CPU usage?")
        
        session_id = response.get("session_id")
        self.assertIsNotNone(session_id)
        
        # Verify it was saved
        cursor = db._conn.execute("SELECT count(*) FROM interactions WHERE session_id = ?", (session_id,))
        self.assertEqual(cursor.fetchone()[0], 1)
        
        cursor = db._conn.execute("SELECT count(*) FROM tool_calls WHERE session_id = ?", (session_id,))
        self.assertGreaterEqual(cursor.fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
