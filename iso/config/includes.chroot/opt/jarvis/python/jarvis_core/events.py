"""Event Bus for JARVIS OS.

Provides asynchronous pub/sub capabilities for continuous system monitoring
and background security scanning (Milestone 6).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: list[Event] = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._running = False
        self._worker_thread: threading.Thread | None = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to the bus."""
        event = Event(event_type=event_type, payload=payload)
        with self._condition:
            self._queue.append(event)
            self._condition.notify()

    def start(self) -> None:
        """Start the background event processing thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_events, daemon=True, name="JarvisEventBus"
            )
            self._worker_thread.start()

    def stop(self) -> None:
        """Stop the event processing thread."""
        with self._condition:
            self._running = False
            self._condition.notify_all()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

    def _process_events(self) -> None:
        while True:
            with self._condition:
                while self._running and not self._queue:
                    self._condition.wait()

                if not self._running and not self._queue:
                    break

                event = self._queue.pop(0)

            # Dispatch outside the lock to prevent deadlocks if handlers publish
            handlers = self._subscribers.get(event.event_type, [])
            for handler in handlers:
                try:
                    handler(event)
                except Exception:
                    # In a real system, we'd log this securely
                    pass
