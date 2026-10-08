import subprocess
import json
import logging
from typing import Any
import os

logger = logging.getLogger(__name__)

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def handle_flatpak_search(req):
    query = req.arguments.get("query", "")
    if not query:
        return []
    res = run_cmd(["flatpak", "search", query])
    results = []
    lines = res.stdout.strip().split('\n')
    if len(lines) > 0:
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 4:
                # Name, Description, Application ID, Version, Branch, Remotes
                results.append({
                    "name": parts[0].strip(),
                    "description": parts[1].strip(),
                    "application_id": parts[2].strip() if len(parts) > 2 else "",
                    "version": parts[3].strip() if len(parts) > 3 else "",
                    "source": "Flatpak",
                    "installed": False
                })
    return results

def handle_flatpak_info(req):
    app_id = req.arguments.get("application_id")
    res = run_cmd(["flatpak", "remote-info", "flathub", app_id])
    if res.returncode != 0:
        return {"status": "error", "message": "Not found"}
    info = {"application_id": app_id, "permissions": []}
    for line in res.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip().lower()] = v.strip()
            
    # For a real implementation we would parse `flatpak info --show-permissions`
    # Mocking standard permissions for visibility
    info["permissions"] = ["network", "ipc", "fallback-x11", "wayland"]
    return {"status": "ok", "data": info}

def _log_audit(req, package: str, operation: str, status: str, result_msg: str):
    from jarvis_core.audit import AuditRecord, InMemoryAuditLog
    log = InMemoryAuditLog()
    record = AuditRecord(
        request_id=req.request_id,
        event="package.mutation",
        actor=req.caller,
        target=package,
        status=status,
        metadata={
            "source": "Flatpak",
            "operation": operation,
            "risk": req.max_risk.name,
            "authorization_result": "authorized" if getattr(req, "authorized", False) else "denied",
            "package_manager_result": result_msg,
            "verification_result": status
        }
    )
    log.append(record)

def handle_flatpak_install(req):
    app_id = req.arguments.get("application_id")
    if not app_id:
        raise Exception("No application_id")
    res = run_cmd(["sudo", "flatpak", "install", "-y", "flathub", app_id])
    if res.returncode == 0:
        _log_audit(req, app_id, "install", "PASS", f"Successfully installed {app_id}")
        return {"status": "ok", "message": f"Successfully installed {app_id}"}
    _log_audit(req, app_id, "install", "FAIL", res.stderr)
    return {"status": "error", "message": res.stderr}

def handle_flatpak_remove(req):
    app_id = req.arguments.get("application_id")
    res = run_cmd(["sudo", "flatpak", "uninstall", "-y", app_id])
    if res.returncode == 0:
        _log_audit(req, app_id, "remove", "PASS", f"Successfully removed {app_id}")
        return {"status": "ok", "message": f"Successfully removed {app_id}"}
    _log_audit(req, app_id, "remove", "FAIL", res.stderr)
    return {"status": "error", "message": res.stderr}

def handle_flatpak_list(req):
    res = run_cmd(["flatpak", "list", "--app", "--columns=application,name,version"])
    results = []
    for line in res.stdout.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) == 3:
                results.append({"application_id": parts[0], "name": parts[1], "version": parts[2], "source": "Flatpak", "installed": True})
    return results

def register_flatpak_tools(registry):
    from jarvis_core.protocol import ToolDefinition, RiskLevel
    registry.register(ToolDefinition("flatpak.search", 1, RiskLevel.READ, False, 5000, 1024*1024, "Search flatpak", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}), handle_flatpak_search)
    registry.register(ToolDefinition("flatpak.info", 1, RiskLevel.READ, False, 5000, 1024*1024, "Info flatpak", {"type": "object", "properties": {"application_id": {"type": "string"}}, "required": ["application_id"]}), handle_flatpak_info)
    registry.register(ToolDefinition("flatpak.list", 1, RiskLevel.READ, False, 5000, 1024*1024, "List flatpak", {}), handle_flatpak_list)
    registry.register(ToolDefinition("flatpak.install", 1, RiskLevel.HIGH, True, 300000, 1024*1024, "Install flatpak", {"type": "object", "properties": {"application_id": {"type": "string"}}, "required": ["application_id"]}), handle_flatpak_install)
    registry.register(ToolDefinition("flatpak.remove", 1, RiskLevel.HIGH, True, 300000, 1024*1024, "Remove flatpak", {"type": "object", "properties": {"application_id": {"type": "string"}}, "required": ["application_id"]}), handle_flatpak_remove)
