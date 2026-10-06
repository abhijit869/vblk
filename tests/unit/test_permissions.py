import unittest

from jarvis_core.permissions import PermissionEngine


class PermissionEngineTests(unittest.TestCase):
    def test_guest_role_denies_high_risk(self) -> None:
        engine = PermissionEngine(active_role="guest")
        self.assertFalse(engine.can_execute_tool("terminal.execute", "HIGH"))
        self.assertFalse(
            engine.can_execute_tool("terminal.execute", "READ")
        )  # Explicitly blocked
        self.assertTrue(engine.can_execute_tool("system.info", "READ"))

    def test_admin_role_allows_all(self) -> None:
        engine = PermissionEngine(active_role="admin")
        self.assertTrue(engine.can_execute_tool("security.block_ip", "HIGH"))
        self.assertTrue(engine.can_execute_tool("terminal.execute", "HIGH"))

    def test_sandbox_config_returns_correct_binds(self) -> None:
        engine = PermissionEngine(active_role="user")
        allow_net, rw_paths = engine.get_sandbox_config()
        self.assertTrue(allow_net)
        self.assertEqual(rw_paths, ["/home/user"])


if __name__ == "__main__":
    unittest.main()
