import ast
import os
from pathlib import Path
import unittest

class FileBoundaryTests(unittest.TestCase):
    def test_desktop_ast_security(self):
        desktop_dir = Path("desktop")
        if not desktop_dir.exists():
            return
            
        banned_calls = {
            "os.system",
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "shutil.rmtree",
            "os.unlink",
            "os.remove"
        }
        
        for root, dirs, files in os.walk(desktop_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                path = Path(root) / file
                content = path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(path))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func_name = ""
                        if isinstance(node.func, ast.Attribute):
                            if isinstance(node.func.value, ast.Name):
                                func_name = f"{node.func.value.id}.{node.func.attr}"
                        elif isinstance(node.func, ast.Name):
                            func_name = node.func.id
                            
                        if func_name in banned_calls:
                            if file == "file_explorer.py" and func_name in {"subprocess.Popen", "subprocess.run"}:
                                is_xdg_open = False
                                if node.args and isinstance(node.args[0], ast.List):
                                    if node.args[0].elts and isinstance(node.args[0].elts[0], ast.Constant):
                                        if node.args[0].elts[0].value == "xdg-open":
                                            is_xdg_open = True
                                if is_xdg_open:
                                    for kw in node.keywords:
                                        if kw.arg == "shell" and getattr(kw.value, "value", False) is True:
                                            self.fail(f"shell=True found in {path}")
                                    continue
                            self.fail(f"Banned call {func_name} found in {path}")

    def test_tool_request_authorized_field(self):
        from jarvis_core.protocol import ToolRequest
        with self.assertRaises(TypeError):
            ToolRequest(tool="test", authorized=True)

if __name__ == "__main__":
    unittest.main()
