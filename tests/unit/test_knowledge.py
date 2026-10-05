import unittest
from jarvis_core.knowledge import generate_system_snapshot

class KnowledgeTests(unittest.TestCase):
    def test_snapshot_generation(self) -> None:
        snapshot = generate_system_snapshot()
        self.assertIn("os", snapshot)
        self.assertIn("cpu", snapshot)
        self.assertIn("memory", snapshot)
        self.assertIn("network", snapshot)
        self.assertIn("top_processes", snapshot)
        self.assertEqual(snapshot["os"]["system"], "Linux")

if __name__ == "__main__":
    unittest.main()
