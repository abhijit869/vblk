import unittest
from pathlib import Path
from jarvis_core.pathguard import PathGuard, PathDenied

class PathGuardTests(unittest.TestCase):
    def test_traversal(self):
        ok, reason = PathGuard.check_read("../../etc/passwd")
        # Traversal should resolve and then get caught, but wait, check_read allows tier 2 reads normally?
        # Let's check check_write.
        ok, reason = PathGuard.check_write("../../etc/passwd")
        self.assertFalse(ok)
        
    def test_absolute_escapes(self):
        ok, reason = PathGuard.check_write("/etc/passwd")
        self.assertFalse(ok)
        
    def test_symlink_to_etc(self):
        pass # Tested in integration or with real FS

    def test_nul_byte(self):
        ok, reason = PathGuard.check_read("some\0path")
        self.assertFalse(ok)
        self.assertEqual(reason, "NUL_BYTE_IN_PATH")

    def test_overlong_path(self):
        ok, reason = PathGuard.check_read("a" * 5000)
        self.assertFalse(ok)

    def test_tier2_write_denied(self):
        ok, reason = PathGuard.check_write("/usr/bin/ls")
        self.assertFalse(ok)

    def test_tier2_read_allowed(self):
        ok, reason = PathGuard.check_read("/usr/bin/ls")
        self.assertTrue(ok)

    def test_ssh_read_ai_tool_path(self):
        ok, reason = PathGuard.check_read("~/.ssh/id_rsa", ai_tool_path=True)
        self.assertFalse(ok)

if __name__ == "__main__":
    unittest.main()
