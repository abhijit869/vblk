import sys
sys.path.insert(0, "python")
from jarvis_core.core import JarvisCore
from jarvis_core.protocol import ToolRequest, RiskLevel
from jarvis_core.tools import build_default_registry
import json

core = JarvisCore(tools=build_default_registry(), max_risk=RiskLevel.HIGH)

print("--- FLATPAK SEARCH TEST ---")
req = ToolRequest(tool="flatpak.search", arguments={"query": "gimp"})
res = core._tools.execute(req)
print(res.data)

print("\n--- FLATPAK UNAUTH INSTALL TEST ---")
req2 = ToolRequest(tool="flatpak.install", arguments={"application_id": "org.gimp.GIMP"}, max_risk=RiskLevel.READ)
res2 = core._tools.execute(req2)
print("Error:", res2.error)

print("\n--- FLATPAK AUTH INSTALL TEST ---")
req3 = ToolRequest(tool="flatpak.install", arguments={"application_id": "org.gimp.GIMP"}, max_risk=RiskLevel.HIGH)
object.__setattr__(req3, 'authorized', True)
res3 = core._tools.execute(req3)
print("Data:", res3.data, "Error:", res3.error)

print("\n--- FLATPAK INFO TEST ---")
req4 = ToolRequest(tool="flatpak.info", arguments={"application_id": "org.gimp.GIMP"})
res4 = core._tools.execute(req4)
print("Data:", res4.data)

print("\n--- FLATPAK REMOVE TEST ---")
req5 = ToolRequest(tool="flatpak.remove", arguments={"application_id": "org.gimp.GIMP"}, max_risk=RiskLevel.HIGH)
object.__setattr__(req5, 'authorized', True)
res5 = core._tools.execute(req5)
print("Data:", res5.data, "Error:", res5.error)

