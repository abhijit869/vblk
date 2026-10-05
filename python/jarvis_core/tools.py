"""Read-only Linux tools for the JARVIS v0.1 prototype."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path
from shutil import disk_usage
from typing import Any

from jarvis_core.policy import PolicyEngine
from jarvis_core.protocol import RiskLevel, Timer, ToolDefinition, ToolError, ToolRequest, ToolResult
from jarvis_core.redaction import redact_data, redact_text
from jarvis_core.terminal import TerminalEngine

ToolHandler = Callable[[ToolRequest], dict[str, Any] | list[Any]]
PROCESS_COMMAND_LIMIT = 240


class ToolDenied(Exception):
    """Raised by a handler when it refuses to act, with optional result data."""

    def __init__(self, error: ToolError, data: dict[str, Any] | list[Any] | None = None) -> None:
        super().__init__(error.message)
        self.error = error
        self.data = data


class ToolRegistry:
    def __init__(self, policy: PolicyEngine | None = None) -> None:
        self._policy = policy or PolicyEngine()
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def definition(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def definitions(self, max_risk: RiskLevel | None = None) -> list[ToolDefinition]:
        """Return registered tools, optionally only those at or below a risk level."""
        return [
            definition
            for definition in self._definitions.values()
            if max_risk is None or definition.risk <= max_risk
        ]

    def execute(self, request: ToolRequest) -> ToolResult:
        timer = Timer()
        definition = self._definitions.get(request.tool)
        if definition is None:
            return ToolResult(
                request_id=request.request_id,
                tool=request.tool,
                status="error",
                risk=RiskLevel.READ,
                duration_ms=timer.elapsed_ms(),
                redacted=False,
                truncated=False,
                data=None,
                error=ToolError(code="unknown_tool", message=f"Unknown tool: {request.tool}"),
            )

        decision = self._policy.authorize(request, definition)
        if not decision.allowed:
            return ToolResult(
                request_id=request.request_id,
                tool=request.tool,
                status="denied",
                risk=definition.risk,
                duration_ms=timer.elapsed_ms(),
                redacted=False,
                truncated=False,
                data=None,
                error=decision.error,
            )

        status = "ok"
        error: ToolError | None = None
        try:
            validate_arguments(definition.parameters, request.arguments)
            data: dict[str, Any] | list[Any] | None = self._handlers[request.tool](request)
        except ToolDenied as exc:
            status, error, data = "denied", exc.error, exc.data
        except subprocess.TimeoutExpired as exc:
            status, data = "error", None
            error = ToolError(code="timeout", message=f"{request.tool} timed out after {exc.timeout}s")
        except (ValueError, TypeError, KeyError) as exc:
            status, data = "error", None
            error = ToolError(code="invalid_arguments", message=str(exc))
        except OSError as exc:
            status, data = "error", None
            error = ToolError(code="os_error", message=str(exc))
        except Exception as exc:  # noqa: BLE001 - tool failures must never crash the core loop
            status, data = "error", None
            error = ToolError(code="tool_exception", message=f"{type(exc).__name__}: {exc}")

        data, redacted = redact_data(data)
        data, truncated = limit_data(data, definition.output_limit_bytes)
        if isinstance(data, dict):
            redacted = redacted or bool(data.get("redacted"))
            truncated = truncated or bool(data.get("truncated"))

        return ToolResult(
            request_id=request.request_id,
            tool=request.tool,
            status=status,
            risk=definition.risk,
            duration_ms=timer.elapsed_ms(),
            redacted=redacted,
            truncated=truncated,
            data=data,
            error=error,
        )


PATH_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Filesystem path to inspect. Defaults to the current directory."},
    },
    "additionalProperties": False,
}


FILE_READ_PARAMETERS = {
    "type": "object",
    "required": ["path"],
    "properties": {
        "path": {"type": "string", "description": "Absolute or relative path to the file to read."},
    },
    "additionalProperties": False,
}

FILE_SEARCH_PARAMETERS = {
    "type": "object",
    "required": ["pattern"],
    "properties": {
        "pattern": {"type": "string", "description": "Glob pattern to search for (e.g. '*.py' or '*/*.md')."},
        "path": {"type": "string", "description": "Directory to search in. Defaults to current directory."},
    },
    "additionalProperties": False,
}

TERMINAL_PARAMETERS = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "A single read-only command such as 'uptime', 'df -h' or 'free -m'. "
                "No pipes, redirection or shell syntax. Mutating commands are denied."
            ),
        },
        "cwd": {"type": "string", "description": "Working directory. Defaults to the current directory."},
    },
    "required": ["command"],
    "additionalProperties": False,
}


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition("system.info", 1, RiskLevel.READ, False, 2000, 32768, "Return basic OS information"),
        system_info,
    )
    registry.register(
        ToolDefinition("system.cpu", 1, RiskLevel.READ, False, 2000, 32768, "Return CPU count and load average"),
        system_cpu,
    )
    registry.register(
        ToolDefinition("system.memory", 1, RiskLevel.READ, False, 2000, 32768, "Return memory information"),
        system_memory,
    )
    registry.register(
        ToolDefinition(
            "system.disk", 1, RiskLevel.READ, False, 2000, 32768, "Return disk usage for a path", PATH_PARAMETERS
        ),
        system_disk,
    )
    registry.register(
        ToolDefinition("process.list", 1, RiskLevel.READ, False, 3000, 65536, "Return running processes"),
        process_list,
    )
    registry.register(
        ToolDefinition("service.list", 1, RiskLevel.READ, False, 3000, 65536, "Return systemd services"),
        service_list,
    )
    registry.register(
        ToolDefinition(
            "terminal.execute",
            1,
            RiskLevel.READ,
            False,
            3000,
            65536,
            "Execute a read-only command",
            TERMINAL_PARAMETERS,
        ),
        terminal_execute,
    )
    
    registry.register(
        ToolDefinition("network.interfaces", 1, RiskLevel.READ, False, 2000, 32768, "Return network interfaces"),
        network_interfaces,
    )
    registry.register(
        ToolDefinition("network.status", 1, RiskLevel.READ, False, 2000, 32768, "Return network routes and IP addresses"),
        network_status,
    )
    registry.register(
        ToolDefinition("file.read", 1, RiskLevel.READ, False, 2000, 262144, "Read utf-8 text file contents", FILE_READ_PARAMETERS),
        file_read,
    )
    registry.register(
        ToolDefinition("file.search", 1, RiskLevel.READ, False, 5000, 65536, "Search for files by glob pattern recursively", FILE_SEARCH_PARAMETERS),
        file_search,
    )
    return registry


def system_info(_: ToolRequest) -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def system_cpu(_: ToolRequest) -> dict[str, Any]:
    load_average = os.getloadavg() if hasattr(os, "getloadavg") else None
    return {
        "cpu_count": os.cpu_count(),
        "load_average": list(load_average) if load_average else None,
    }


def system_memory(_: ToolRequest) -> dict[str, Any]:
    meminfo = _read_meminfo()
    total_kb = meminfo.get("MemTotal")
    available_kb = meminfo.get("MemAvailable")
    used_kb = None
    if total_kb is not None and available_kb is not None:
        used_kb = total_kb - available_kb

    return {
        "total_kb": total_kb,
        "available_kb": available_kb,
        "used_kb": used_kb,
    }


def system_disk(request: ToolRequest) -> dict[str, Any]:
    path = Path(str(request.arguments.get("path", "."))).resolve()
    usage = disk_usage(path)
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def process_list(_: ToolRequest) -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = _read_proc_status(entry / "status")
            stat = (entry / "stat").read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue

        processes.append(
            {
                "pid": int(entry.name),
                "name": status.get("Name"),
                "state": status.get("State"),
                "ppid": _parse_int(status.get("PPid")),
                "threads": _parse_int(status.get("Threads")),
                "vm_rss_kb": _parse_status_kb(status.get("VmRSS")),
                "command": _parse_proc_command(entry, stat),
            }
        )
    return sorted(processes, key=lambda process: process["pid"])


def service_list(_: ToolRequest) -> list[dict[str, Any]]:
    command = ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or f"systemctl exited with code {completed.returncode}"
        raise OSError(message)

    services: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        services.append(
            {
                "unit": parts[0],
                "load": parts[1],
                "active": parts[2],
                "sub": parts[3],
                "description": parts[4] if len(parts) == 5 else "",
            }
        )
    return services


TERMINAL_MAX_TIMEOUT_MS = 3000
TERMINAL_MAX_OUTPUT_BYTES = 32768


def terminal_execute(request: ToolRequest) -> dict[str, Any]:
    command = request.arguments.get("command")
    if not isinstance(command, (str, list)):
        raise ValueError("terminal.execute requires a command string or argument list")

    timeout_ms = int(request.arguments.get("timeout_ms", 2000))
    if request.timeout_ms is not None:
        timeout_ms = min(timeout_ms, request.timeout_ms)
    output_limit = int(request.arguments.get("output_limit_bytes", TERMINAL_MAX_OUTPUT_BYTES))

    result = TerminalEngine().execute(
        command=command,
        cwd=str(request.arguments.get("cwd", ".")),
        timeout_ms=max(1, min(timeout_ms, TERMINAL_MAX_TIMEOUT_MS)),
        output_limit_bytes=max(1, min(output_limit, TERMINAL_MAX_OUTPUT_BYTES)),
        max_risk=request.max_risk,
    )
    data = {
        "command": result.command,
        "risk": result.risk.name,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "signal": result.signal,
        "duration_ms": result.duration_ms,
        "cwd": result.cwd,
        "timed_out": result.timed_out,
        "truncated": result.truncated,
        "redacted": result.redacted,
    }
    if result.denied:
        raise ToolDenied(ToolError(code="command_risk_exceeds_limit", message=result.stderr), data)
    return data



def network_interfaces(_: ToolRequest) -> list[dict[str, Any]]:
    interfaces: list[dict[str, Any]] = []
    net_path = Path("/sys/class/net")
    if not net_path.exists():
        return interfaces
    
    for iface in net_path.iterdir():
        if not iface.is_dir():
            continue
        try:
            mac = (iface / "address").read_text(encoding="utf-8").strip()
            state = (iface / "operstate").read_text(encoding="utf-8").strip()
            mtu = int((iface / "mtu").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            mac = state = ""
            mtu = 0
            
        interfaces.append({
            "name": iface.name,
            "mac_address": mac,
            "state": state,
            "mtu": mtu,
        })
    return sorted(interfaces, key=lambda x: x["name"])


def network_status(_: ToolRequest) -> dict[str, Any]:
    addresses = []
    routes = []
    
    try:
        completed = subprocess.run(["ip", "-j", "address"], capture_output=True, text=True, timeout=2, check=False)
        if completed.returncode == 0 and completed.stdout.strip():
            addresses = json.loads(completed.stdout)
    except (OSError, json.JSONDecodeError):
        pass

    try:
        completed = subprocess.run(["ip", "-j", "route"], capture_output=True, text=True, timeout=2, check=False)
        if completed.returncode == 0 and completed.stdout.strip():
            routes = json.loads(completed.stdout)
    except (OSError, json.JSONDecodeError):
        pass

    return {
        "addresses": addresses,
        "routes": routes
    }


def file_read(request: ToolRequest) -> dict[str, Any]:
    path = Path(request.arguments["path"]).resolve()
    try:
        content = path.read_text(encoding="utf-8")
        return {"path": str(path), "content": content}
    except UnicodeDecodeError:
        return {"path": str(path), "error": "file is binary or not valid utf-8"}
    except Exception as e:
        return {"path": str(path), "error": str(e)}


def file_search(request: ToolRequest) -> dict[str, Any]:
    path = Path(request.arguments.get("path", ".")).resolve()
    pattern = request.arguments["pattern"]
    if not path.is_dir():
        raise OSError(f"Directory not found: {path}")
    
    results = []
    try:
        for p in path.rglob(pattern):
            results.append(str(p))
            if len(results) >= 1000:
                break
    except Exception as e:
        return {"path": str(path), "pattern": pattern, "error": str(e)}
        
    return {"path": str(path), "pattern": pattern, "results": results}

def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
        for line in handle:
            key, raw_value = line.split(":", maxsplit=1)
            parts = raw_value.strip().split()
            if parts and parts[0].isdigit():
                values[key] = int(parts[0])
    return values


def _read_proc_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            key, value = line.split(":", maxsplit=1)
            values[key] = value.strip()
    return values


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_status_kb(value: str | None) -> int | None:
    if value is None:
        return None
    parts = value.split()
    if not parts:
        return None
    return _parse_int(parts[0])


def _parse_proc_command(process_path: Path, stat: str) -> str:
    try:
        raw_command = (process_path / "cmdline").read_bytes()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        raw_command = b""
    command = raw_command.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    if not command and "(" in stat and ")" in stat:
        command = stat[stat.find("(") + 1 : stat.rfind(")")]
    command, _ = redact_text(command)
    if len(command) > PROCESS_COMMAND_LIMIT:
        return f"{command[:PROCESS_COMMAND_LIMIT]} [TRUNCATED]"
    return command


def _json_size(value: Any) -> int:
    return len(json.dumps(value, default=str, ensure_ascii=False).encode("utf-8"))


def limit_data(data: Any, limit_bytes: int) -> tuple[Any, bool]:
    """Enforce a tool's output limit on JSON-like result data.

    Lists are trimmed to the largest prefix that fits. Oversized strings inside
    dicts are cut with a ``[TRUNCATED]`` marker.
    """
    if data is None or _json_size(data) <= limit_bytes:
        return data, False

    if isinstance(data, list):
        low, high = 0, len(data)
        while low < high:
            middle = (low + high + 1) // 2
            if _json_size(data[:middle]) <= limit_bytes:
                low = middle
            else:
                high = middle - 1
        return data[:low], True

    if isinstance(data, dict):
        per_field = max(64, limit_bytes // max(1, len(data)))
        limited: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value.encode("utf-8")) > per_field:
                value = value.encode("utf-8")[:per_field].decode("utf-8", errors="ignore") + "\n[TRUNCATED]"
            elif isinstance(value, list):
                value, _ = limit_data(value, per_field)
            limited[key] = value
        return limited, True

    if isinstance(data, str):
        return data.encode("utf-8")[:limit_bytes].decode("utf-8", errors="ignore") + "\n[TRUNCATED]", True

    return data, True


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list, tuple),
    "object": (dict,),
}


def validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Validate tool arguments against the subset of JSON Schema JARVIS uses.

    Raises ``ValueError`` describing the first problem found.
    """
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    properties: dict[str, Any] = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments:
            raise ValueError(f"missing required argument: {name}")
    for name, value in arguments.items():
        spec = properties.get(name)
        if spec is None:
            if schema.get("additionalProperties", True) is False:
                raise ValueError(f"unexpected argument: {name}")
            continue
        expected = spec.get("type")
        if expected is None:
            continue
        allowed = expected if isinstance(expected, list) else [expected]
        python_types = tuple(t for kind in allowed for t in _JSON_TYPES.get(kind, ()))
        is_bool_for_number = isinstance(value, bool) and "boolean" not in allowed
        if not isinstance(value, python_types) or is_bool_for_number:
            raise ValueError(f"argument {name} must be of type {' or '.join(allowed)}")
