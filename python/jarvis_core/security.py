"""Security and Threat Detection Engine for JARVIS."""

from __future__ import annotations

from typing import Any
from pathlib import Path
from dataclasses import dataclass, field

from jarvis_core.tools import ToolRegistry, ToolRequest
from jarvis_core.protocol import RiskLevel


@dataclass
class ThreatReport:
    scanned_processes: int
    detected_threats: list[dict[str, Any]] = field(default_factory=list)
    status: str = "secure"


class SecurityScanner:
    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def run_heuristics_scan(self) -> ThreatReport:
        """Perform a defensive heuristics scan on running processes to detect anomalies."""
        request = ToolRequest(tool="process.list", max_risk=RiskLevel.READ)
        result = self.tools.execute(request)
        
        if result.status != "ok" or not isinstance(result.data, list):
            return ThreatReport(scanned_processes=0, status="error")

        processes = result.data
        threats = []
        
        # Define some basic defensive heuristics for anomaly detection
        suspicious_paths = ["/tmp/", "/dev/shm/", "/var/tmp/"]
        
        for proc in processes:
            command = proc.get("command", "")
            pid = proc.get("pid")
            
            # Heuristic 1: Processes running from temporary directories
            for path in suspicious_paths:
                if path in command and not command.startswith("kworker"):
                    threats.append({
                        "pid": pid,
                        "command": command,
                        "reason": f"Running from volatile memory or temp path: {path}",
                        "severity": "MEDIUM",
                    })

            # Heuristic 2: Known ransomware/miner patterns (mock example)
            if "xmrig" in command.lower() or "stratum+tcp" in command.lower():
                threats.append({
                    "pid": pid,
                    "command": command,
                    "reason": "Known cryptominer signature detected",
                    "severity": "HIGH",
                })
                
        return ThreatReport(
            scanned_processes=len(processes),
            detected_threats=threats,
            status="threats_found" if threats else "secure"
        )
