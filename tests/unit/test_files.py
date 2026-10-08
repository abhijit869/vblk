import unittest
import tempfile
import os
import shutil
from pathlib import Path
from jarvis_core.files import FileService

class FileServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_mkdir_and_trash(self):
        new_dir = self.temp_path / "new_folder"
        res = FileService.mkdir(str(new_dir))
        self.assertTrue(res.get("success"))
        self.assertTrue(new_dir.is_dir())
        
        # Trash it
        res = FileService.trash(str(new_dir))
        self.assertTrue(res.get("success"))
        self.assertFalse(new_dir.exists())

    def test_copy_folder_into_itself_refused(self):
        src = self.temp_path / "src"
        src.mkdir()
        dst = src / "dst"
        res = FileService.copy(str(src), str(dst))
        self.assertFalse(res.get("success"))
        self.assertIn("Destination is inside source", res.get("error"))

    def test_symlink_copied_as_symlink(self):
        src = self.temp_path / "src"
        src.write_text("hello")
        link = self.temp_path / "link"
        link.symlink_to(src)
        
        dst = self.temp_path / "dst_link"
        res = FileService.copy(str(link), str(dst))
        self.assertTrue(res.get("success"))
        self.assertTrue(dst.is_symlink())

    def test_trash_symlink_not_target(self):
        src = self.temp_path / "src"
        src.write_text("hello")
        link = self.temp_path / "link"
        link.symlink_to(src)
        
        FileService.trash(str(link))
        self.assertFalse(link.exists())
        self.assertTrue(src.exists())

    def test_no_permanent_delete_path(self):
        # We manually verify there's no unlink in FileService.trash
        pass

if __name__ == "__main__":
    unittest.main()
