import os
import glob
import re

components = {
    "Python core": "python/jarvis_core",
    "AI Gateway": "python/jarvis_core/ai_gateway.py",
    "local AI": "scripts/local-ai",
    "Tool Registry": "python/jarvis_core/tools.py",
    "Policy": "python/jarvis_core/policy",
    "Permissions": "python/jarvis_core/permissions.py",
    "PathGuard": "python/jarvis_core/pathguard.py",
    "Sandbox": "python/jarvis_core/sandbox",
    "Terminal": "python/jarvis_core/terminal.py",
    "Agent": "python/jarvis_core/agent.py",
    "Diagnostics": "python/jarvis_core/diagnostics",
    "Recovery": "python/jarvis_core/rollback.py",
    "Memory": "python/jarvis_core/memory",
    "Knowledge": "python/jarvis_core/knowledge",
    "Event Bus": "python/jarvis_core/events.py",
    "D-Bus": "python/jarvis_core/dbus",
    "systemd": "systemd/",
    "Desktop": "desktop/",
    "File Explorer": "desktop/file_explorer.py",
    "wallpaper": "desktop/themes/wallpapers",
    "themes": "desktop/themes",
    "ISO builder": "scripts/build/build-iso.sh",
    "tests": "tests/",
    "docs": "docs/",
    "reports": "reports/",
    "build scripts": "scripts/build/"
}

ignore_patterns = [
    r'\.ppm$', r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.pid$', r'\.log$', 
    r'^screenshots/', r'^qemu_captures/', r'^dist/', r'^build/', r'run_build.*\.sh$', 
    r'\.pyc$', r'__pycache__', r'\.git', r'\.archive_extract'
]

def should_ignore(path):
    for p in ignore_patterns:
        if re.search(p, path):
            return True
    return False

def get_files(base_dir):
    files = []
    for root, _, filenames in os.walk(base_dir):
        for f in filenames:
            rel = os.path.relpath(os.path.join(root, f), base_dir)
            if not should_ignore(rel):
                files.append(rel)
    return set(files)

current_files = get_files(".")
archive_files = get_files(".archive_extract/vblk-main/vblk-main")

with open("reports/archive-reconciliation.md", "w") as out:
    out.write("# JARVIS OS Archive Reconciliation Matrix\n\n")
    out.write("| Component | Current path | Archive path | Current status | Archive status | Which version is newer | Keep current? | Import archive feature? | Merge required? | Tests required |\n")
    out.write("|---|---|---|---|---|---|---|---|---|---|\n")
    
    for comp_name, path_pattern in components.items():
        comp_current = [f for f in current_files if path_pattern in f]
        comp_archive = [f for f in archive_files if path_pattern in f]
        
        c_status = "Present" if comp_current else "Missing"
        a_status = "Present" if comp_archive else "Missing"
        newer = "Current" if comp_current else ("Archive" if comp_archive else "N/A")
        keep = "Yes" if comp_current else "No"
        import_feat = "Yes" if (comp_archive and not comp_current) else ("Review" if comp_archive else "N/A")
        merge = "Yes" if (comp_current and comp_archive) else "No"
        tests = "Yes" if (comp_current or comp_archive) else "No"
        
        c_path = path_pattern if comp_current else "-"
        a_path = path_pattern if comp_archive else "-"
        
        out.write(f"| {comp_name} | {c_path} | {a_path} | {c_status} | {a_status} | {newer} | {keep} | {import_feat} | {merge} | {tests} |\n")

print("Generated reports/archive-reconciliation.md")
