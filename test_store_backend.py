import sys
sys.path.insert(0, "python")
from jarvis_core.core import JarvisCore
from jarvis_core.protocol import ToolRequest, RiskLevel
from jarvis_core.tools import build_default_registry
import json

core = JarvisCore(tools=build_default_registry(), max_risk=RiskLevel.HIGH)

# 1. Search test
print("--- SEARCH TEST ---")
req = ToolRequest(tool="package.search", arguments={"query": "sl"})
res = core._tools.execute(req)
print(f"Search 'sl': error={res.error}, data={res.data[:2] if res.data else None}...")

# 2. Unauthorized Install test (D-Bus Security Test)
print("\n--- UNAUTHORIZED INSTALL TEST ---")
req_unauth = ToolRequest(tool="package.install", arguments={"package": "sl"}, max_risk=RiskLevel.READ)
res_unauth = core._tools.execute(req_unauth)
if res_unauth.error:
    print(f"EXPECTED DENIED: {res_unauth.error.message}")
else:
    print("FAIL: Unauthorized install was allowed!")

# 3. Authorized Install test
print("\n--- AUTHORIZED INSTALL TEST ---")
req_auth = ToolRequest(tool="package.install", arguments={"package": "sl"}, max_risk=RiskLevel.HIGH)
object.__setattr__(req_auth, 'authorized', True)
res_auth = core._tools.execute(req_auth)
if res_auth.error:
    print(f"FAIL: Authorized install failed with {res_auth.error.message}")
else:
    print(f"EXPECTED ALLOWED: {res_auth.data}")

# 4. Failed install test (Unavailable package)
print("\n--- FAILED INSTALL TEST ---")
req_fail = ToolRequest(tool="package.install", arguments={"package": "this-pkg-does-not-exist"}, max_risk=RiskLevel.HIGH)
object.__setattr__(req_fail, 'authorized', True)
res_fail = core._tools.execute(req_fail)
if res_fail.error:
    print(f"EXPECTED ERROR (Policy): {res_fail.error.message}")
else:
    print(f"EXPECTED ERROR (Apt): {res_fail.data}")

# 5. Remove test
print("\n--- REMOVE TEST ---")
req_rem = ToolRequest(tool="package.remove", arguments={"package": "sl"}, max_risk=RiskLevel.HIGH)
object.__setattr__(req_rem, 'authorized', True)
res_rem = core._tools.execute(req_rem)
print(f"REMOVE RESULT: {res_rem.data}")

