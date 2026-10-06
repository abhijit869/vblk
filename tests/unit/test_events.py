import time
import unittest

from jarvis_core.events import Event, EventBus


class EventBusTests(unittest.TestCase):
    def test_publish_subscribe(self) -> None:
        bus = EventBus()
        received_events: list[Event] = []

        def handler(event: Event) -> None:
            received_events.append(event)

        bus.subscribe("security.threat_detected", handler)
        bus.start()

        try:
            bus.publish("security.threat_detected", {"pid": 1234})
            bus.publish("system.load_high", {"cpu": 99})  # Should be ignored

            # Wait briefly for background thread to process
            time.sleep(0.1)

            self.assertEqual(len(received_events), 1)
            self.assertEqual(received_events[0].event_type, "security.threat_detected")
            self.assertEqual(received_events[0].payload["pid"], 1234)
        finally:
            bus.stop()


if __name__ == "__main__":
    unittest.main()
