import subprocess
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def register_package_tools(registry):
    from jarvis_core.protocol import ToolDefinition, RiskLevel, ToolRequest
    
    def handle_search(req: ToolRequest):
        query = req.arguments.get("query", "")
        if not query:
            return []
        res = subprocess.run(["apt-cache", "search", query], capture_output=True, text=True)
        results = []
        for line in res.stdout.splitlines():
            if " - " in line:
                name, desc = line.split(" - ", 1)
                results.append({"name": name.strip(), "description": desc.strip(), "source": "Debian", "installed": False})
        return results

    def _log_audit(req: ToolRequest, package: str, operation: str, status: str, result_msg: str):
        from jarvis_core.audit import AuditRecord, InMemoryAuditLog
        log = InMemoryAuditLog()
        record = AuditRecord(
            request_id=req.request_id,
            event="package.mutation",
            actor=req.caller,
            target=package,
            status=status,
            metadata={
                "source": "Debian",
                "operation": operation,
                "risk": req.max_risk.name,
                "authorization_result": "authorized" if getattr(req, "authorized", False) else "denied",
                "package_manager_result": result_msg,
                "verification_result": status
            }
        )
        log.append(record)

    def handle_install(req: ToolRequest):
        package = req.arguments.get("package")
        if not package:
            raise Exception("No package specified")
        
        # In JARVIS Core, this runs as a trusted daemon.
        import os
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        res = subprocess.run(["sudo", "apt-get", "install", "-y", package], capture_output=True, text=True, env=env)
        if res.returncode == 0:
            _log_audit(req, package, "install", "PASS", f"Successfully installed {package}")
            return {"status": "ok", "message": f"Successfully installed {package}"}
        else:
            _log_audit(req, package, "install", "FAIL", f"Install failed: {res.stderr}")
            return {"status": "error", "message": f"Install failed: {res.stderr}"}

    def handle_remove(req: ToolRequest):
        package = req.arguments.get("package")
        import os
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        res = subprocess.run(["sudo", "apt-get", "remove", "-y", package], capture_output=True, text=True, env=env)
        if res.returncode == 0:
            _log_audit(req, package, "remove", "PASS", f"Successfully removed {package}")
            return {"status": "ok", "message": f"Successfully removed {package}"}
        else:
            _log_audit(req, package, "remove", "FAIL", f"Remove failed: {res.stderr}")
            return {"status": "error", "message": f"Remove failed: {res.stderr}"}

    registry.register(ToolDefinition("package.search", 1, RiskLevel.READ, False, 5000, 1024*1024, "Search packages", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}), handle_search)
    registry.register(ToolDefinition("package.install", 1, RiskLevel.HIGH, True, 300000, 1024*1024, "Install package", {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}), handle_install)
    registry.register(ToolDefinition("package.remove", 1, RiskLevel.HIGH, True, 300000, 1024*1024, "Remove package", {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}), handle_remove)

