# JARVIS OS Archive Reconciliation Matrix

| Component | Current path | Archive path | Current status | Archive status | Which version is newer | Keep current? | Import archive feature? | Merge required? | Tests required |
|---|---|---|---|---|---|---|---|---|---|
| Python core | python/jarvis_core/ | python/jarvis_core/ | Present | Present | Current | Yes | No | Review | Yes |
| AI Gateway | python/jarvis_core/ai_gateway.py | python/jarvis_core/ai_gateway.py | Present | Present | Current | Yes | No | Review | Yes |
| local AI | scripts/local-ai | scripts/local-ai | Present | Missing | Current | Yes | No | No | Yes |
| Tool Registry | python/jarvis_core/tools.py | python/jarvis_core/tools.py | Present | Present | Current | Yes | No | Review | Yes |
| Policy | python/jarvis_core/policy.py | python/jarvis_core/policy.py | Present | Present | Current | Yes | No | Review | Yes |
| Permissions | python/jarvis_core/permissions.py | python/jarvis_core/permissions.py | Present | Present | Current | Yes | No | Review | Yes |
| PathGuard | python/jarvis_core/pathguard.py | python/jarvis_core/pathguard.py | Present | Present | Current | Yes | No | Review | Yes |
| Sandbox | python/jarvis_core/sandbox.py | python/jarvis_core/sandbox.py | Present | Present | Current | Yes | No | Review | Yes |
| Terminal | python/jarvis_core/terminal.py | python/jarvis_core/terminal.py | Present | Present | Current | Yes | No | Review | Yes |
| Agent | python/jarvis_core/agent.py | python/jarvis_core/agent.py | Present | Present | Current | Yes | No | Review | Yes |
| Diagnostics | python/jarvis_core/diagnostics.py | python/jarvis_core/diagnostics.py | Present | Present | Current | Yes | No | Review | Yes |
| Recovery | python/jarvis_core/rollback.py | python/jarvis_core/rollback.py | Present | Present | Current | Yes | No | Review | Yes |
| Memory | python/jarvis_core/memory.py | python/jarvis_core/memory.py | Present | Present | Current | Yes | No | Review | Yes |
| Knowledge | python/jarvis_core/knowledge.py | python/jarvis_core/knowledge.py | Present | Present | Current | Yes | No | Review | Yes |
| Event Bus | python/jarvis_core/events.py | python/jarvis_core/events.py | Present | Present | Current | Yes | No | Review | Yes |
| D-Bus | python/jarvis_core/dbus | python/jarvis_core/dbus | Present | Present | Current | Yes | No | Review | Yes |
| systemd | systemd/ | systemd/ | Present | Present | Current | Yes | No | Review | Yes |
| Desktop | desktop/ | desktop/ | Present | Present | Current | Yes | No | Review | Yes |
| File Explorer | desktop/file_explorer.py | desktop/jarvis_explorer.py | Present | Present | Current | Yes | Yes (styles) | Review | Yes |
| wallpaper | desktop/themes/wallpapers | desktop/themes/wallpapers | Present | Present | Current | Yes | Yes (assets) | Review | Yes |
| themes | desktop/themes | desktop/themes | Present | Present | Current | Yes | Yes (assets) | Review | Yes |
| ISO builder | scripts/build/build-iso.sh | iso/build.sh | Present | Present | Current | Yes | No | Review | Yes |
| tests | tests/ | tests/ | Present | Present | Current | Yes | No | Review | Yes |
| docs | docs/ | docs/ | Present | Present | Current | Yes | No | Review | Yes |
| reports | reports/ | reports/ | Present | Present | Current | Yes | No | Review | Yes |
| build scripts | scripts/build/ | scripts/build/ | Present | Present | Current | Yes | No | Review | Yes |

