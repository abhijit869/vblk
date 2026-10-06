"""A scripted, local OpenAI-compatible HTTP server for tests (no network)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeOpenAIServer:
    """Serves queued responses for POST /v1/chat/completions and records requests."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.headers: list[dict[str, str]] = []
        self._responses: list[tuple[int, dict[str, Any], dict[str, str]]] = []
        self._lock = threading.Lock()
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                with server._lock:
                    server.requests.append(body)
                    server.headers.append(
                        {key.lower(): value for key, value in self.headers.items()}
                    )
                    status, payload, extra_headers = (
                        server._responses.pop(0)
                        if server._responses
                        else (500, {"error": "no scripted reply"}, {})
                    )
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in extra_headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_: Any) -> None:
                return

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def enqueue(
        self,
        payload: dict[str, Any],
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._responses.append((status, payload, headers or {}))

    def enqueue_tool_calls(
        self, *calls: tuple[str, dict[str, Any]], model: str = "test-model"
    ) -> None:
        self.enqueue(
            {
                "model": model,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": f"call_{index}",
                                    "type": "function",
                                    "function": {
                                        "name": name,
                                        "arguments": json.dumps(arguments),
                                    },
                                }
                                for index, (name, arguments) in enumerate(calls)
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            }
        )

    def enqueue_text(self, content: str, model: str = "test-model") -> None:
        self.enqueue(
            {
                "model": model,
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 20},
            }
        )

    def __enter__(self) -> FakeOpenAIServer:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
