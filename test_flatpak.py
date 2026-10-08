import sys
sys.path.insert(0, "python")
from jarvis_core.core import JarvisCore
from jarvis_core.protocol import ToolRequest, RiskLevel
from jarvis_core.tools import build_default_registry
import json

core = JarvisCore(tools=build_default_registry(), max_risk=RiskLevel.HIGH)

req = ToolRequest(tool="flatpak.search", arguments={"query": "gimp"})
res = core._tools.execute(req)
print("Error:", res.error)
print("Data:", res.data)
