import os
import unittest
from pathlib import Path
from jarvis_core.tools import ToolRegistry, build_default_registry, ToolRequest

class TestWallpaperTools(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_registry()
        
    def test_tools_registered(self):
        self.assertIsNotNone(self.registry.definition("wallpaper.list"))
        self.assertIsNotNone(self.registry.definition("wallpaper.set"))
        self.assertIsNotNone(self.registry.definition("wallpaper.add"))
        self.assertIsNotNone(self.registry.definition("wallpaper.remove"))
        self.assertIsNotNone(self.registry.definition("wallpaper.reset_default"))
        
if __name__ == "__main__":
    unittest.main()
