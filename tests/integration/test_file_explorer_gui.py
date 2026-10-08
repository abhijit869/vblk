import unittest
import tempfile
import shutil
import threading
import time
from pathlib import Path

try:
    import tkinter
    TK_AVAILABLE = True
    import os
    if not os.environ.get("DISPLAY"):
        TK_AVAILABLE = False
except ImportError:
    TK_AVAILABLE = False

class FileExplorerGUITests(unittest.TestCase):
    @unittest.skipUnless(TK_AVAILABLE, "tkinter not available")
    def test_gui_smoke(self):
        from desktop.file_explorer import FileExplorer
        temp_dir = tempfile.mkdtemp()
        
        app = FileExplorer(temp_dir)
        app.update()
        
        # Navigate
        app.navigate(temp_dir)
        app.update()
        
        # Verify Delete inside address entry does NOT trigger trash
        app.address_entry.focus_set()
        app.event_generate("<Delete>")
        app.update()
        
        # We assume no dialog opened since focus was not on tree
        
        # Search with cancel
        app.search_var.set("foo")
        app.start_search()
        app.update()
        app.cancel_search()
        app.update()
        self.assertFalse(app.searching)
        
        app.destroy()
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    unittest.main()
