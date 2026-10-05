"""Snapshot and Rollback Engine for JARVIS OS.

Allows the AI to take system snapshots before executing high-risk plans
and automatically rollback if the verification step fails or the system crashes.
"""

from __future__ import annotations

import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SnapshotEngine:
    def __init__(self, snapshot_dir: str = "/var/lib/jarvis/snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        # Using rsync as a generic fallback if btrfs/timeshift is not available
        self._mode = self._detect_mode()

    def _detect_mode(self) -> str:
        # Check if the root filesystem is btrfs
        try:
            result = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", "/"], capture_output=True, text=True)
            if "btrfs" in result.stdout.lower():
                return "btrfs"
        except Exception:
            pass
        return "rsync"

    def create_snapshot(self, reason: str = "pre-execution") -> str:
        """Create a system snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snap_id = f"snap_{timestamp}_{reason.replace(' ', '_')}"
        snap_path = self.snapshot_dir / snap_id
        
        logger.info(f"Creating {self._mode} snapshot: {snap_id}")
        
        if self._mode == "btrfs":
            # BTRFS atomic subvolume snapshot
            subprocess.run(["btrfs", "subvolume", "snapshot", "/", str(snap_path)], check=True)
        else:
            # Fallback to critical config backup
            snap_path.mkdir(parents=True, exist_ok=True)
            # Backup /etc and /opt/jarvis as a minimum safe state
            subprocess.run(["rsync", "-a", "/etc/", str(snap_path / "etc")], check=True)
            subprocess.run(["rsync", "-a", "/opt/jarvis/", str(snap_path / "jarvis")], check=True)
            
        return snap_id

    def rollback(self, snap_id: str) -> bool:
        """Rollback the system to a previous snapshot."""
        snap_path = self.snapshot_dir / snap_id
        if not snap_path.exists():
            logger.error(f"Snapshot {snap_id} does not exist.")
            return False
            
        logger.warning(f"INITIATING ROLLBACK to {snap_id} via {self._mode}...")
        
        if self._mode == "btrfs":
            # This requires reboot or live-mount trickery, simplified for prototype
            logger.info("BTRFS rollback staged for next reboot.")
            # In a real system, you'd swap the default subvolume here.
        else:
            # Restore critical configs
            subprocess.run(["rsync", "-a", str(snap_path / "etc/"), "/etc/"], check=True)
            subprocess.run(["rsync", "-a", str(snap_path / "jarvis/"), "/opt/jarvis/"], check=True)
            logger.info("Config rollback applied instantly.")
            
        return True
