"""OS Knowledge Snapshot.

Aggregates system state into a unified snapshot.
"""
import platform
from typing import Any

from jarvis_core.protocol import ToolRequest
from jarvis_core.tools import (
    network_status,
    process_list,
    system_cpu,
    system_memory,
)


def generate_system_snapshot() -> dict[str, Any]:
    """Capture a high-level overview of the system state."""
    
    # We use empty requests to bypass full policy checks internally,
    # as this is for the knowledge engine itself.
    req = ToolRequest(tool="internal", arguments={})
    
    # Gather data
    try:
        cpu = system_cpu(req)
    except Exception:
        cpu = None

    try:
        mem = system_memory(req)
    except Exception:
        mem = None
        
    try:
        # Just grab the top 10 processes by PID for a quick snapshot, 
        # or we could sort by CPU/RAM if we had that.
        procs = process_list(req)
        # Sort by threads as a proxy for size, just for the snapshot brevity
        top_procs = sorted(procs, key=lambda p: p.get("threads") or 0, reverse=True)[:10]
    except Exception:
        top_procs = []

    try:
        net = network_status(req)
    except Exception:
        net = None

    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "cpu": cpu,
        "memory": mem,
        "network": net,
        "top_processes": top_procs,
    }
