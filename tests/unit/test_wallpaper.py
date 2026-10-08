import os
import tempfile
import unittest
import shutil
from pathlib import Path
from jarvis_core.wallpaper import WallpaperManager, DEFAULT_ID

class TestWallpaperManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "wallpapers.json"
        self.user_dir = Path(self.temp_dir) / "user_wallpapers"
        
        self.builtin_dir = Path(self.temp_dir) / "builtin"
        self.builtin_dir.mkdir()
        for f in ["jarvis-default.jpeg", "jarvis-alt-1.jpeg", "jarvis-alt-2.jpeg"]:
            (self.builtin_dir / f).touch()
            
        # Monkey patch paths
        import jarvis_core.wallpaper as wp
        wp.WALLPAPER_DB_PATH = str(self.db_path)
        wp.USER_WALLPAPER_DIR = str(self.user_dir)
        wp.BUILTIN_WALLPAPER_DIR = str(self.builtin_dir)
        
        self.manager = WallpaperManager()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        wallpapers = self.manager.get_all()
        self.assertGreaterEqual(len(wallpapers), 3)
        
        current = self.manager.get_current()
        self.assertEqual(current["id"], DEFAULT_ID)
        self.assertTrue(current["default"])
        
    def test_set_current(self):
        self.assertTrue(self.manager.set_current("jarvis-alt-1"))
        self.assertEqual(self.manager.get_current()["id"], "jarvis-alt-1")
        
        # Invalid ID
        self.assertFalse(self.manager.set_current("nonexistent"))
        self.assertEqual(self.manager.get_current()["id"], "jarvis-alt-1")

    def test_reset_default(self):
        self.manager.set_current("jarvis-alt-1")
        self.manager.reset_default()
        self.assertEqual(self.manager.get_current()["id"], DEFAULT_ID)

    def test_add_remove_user_wallpaper(self):
        # Create a fake jpeg file
        fake_jpg = Path(self.temp_dir) / "test.jpg"
        fake_jpg.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")
        
        meta = self.manager.add_user_wallpaper(str(fake_jpg), "My Wallpaper")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["name"], "My Wallpaper")
        self.assertEqual(meta["source"], "user")
        
        # Set it
        self.assertTrue(self.manager.set_current(meta["id"]))
        
        # Remove it
        self.assertTrue(self.manager.remove_user_wallpaper(meta["id"]))
        
        # Current should fallback to default
        self.assertEqual(self.manager.get_current()["id"], DEFAULT_ID)

    def test_invalid_wallpaper_add(self):
        fake_txt = Path(self.temp_dir) / "test.txt"
        fake_txt.write_text("not an image")
        
        with self.assertRaises(ValueError):
            self.manager.add_user_wallpaper(str(fake_txt), "Bad Wallpaper")

if __name__ == "__main__":
    unittest.main()
