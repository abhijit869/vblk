import unittest

from jarvis_core.sandbox import SandboxEngine


class SandboxTests(unittest.TestCase):
    def test_wrap_command_without_bwrap(self) -> None:
        # If bwrap is not available, it just returns the cmd (fallback mode)
        # We simulate it by clearing the path
        sandbox = SandboxEngine()
        sandbox._bwrap_path = None
        cmd = ["ls", "-la"]
        self.assertEqual(sandbox.wrap_command(cmd), ["ls", "-la"])

    def test_wrap_command_with_bwrap(self) -> None:
        sandbox = SandboxEngine()
        sandbox._bwrap_path = "/usr/bin/bwrap"

        cmd = ["rm", "-rf", "/"]
        wrapped = sandbox.wrap_command(
            cmd, allow_network=False, rw_paths=["/home/user/safe_dir"]
        )

        self.assertIn("/usr/bin/bwrap", wrapped)
        self.assertIn("--ro-bind", wrapped)
        self.assertIn("--unshare-net", wrapped)
        self.assertIn("--bind", wrapped)
        self.assertIn("/home/user/safe_dir", wrapped)
        self.assertIn("rm", wrapped)


if __name__ == "__main__":
    unittest.main()
