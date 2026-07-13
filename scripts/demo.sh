#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=src

python - <<'PY'
from ai_planes.control_plane import IdentityContext
from ai_planes.platform import PlatformFacade

f = PlatformFacade()
print("=== Five planes ===")
for name in f.describe()["planes"]:
    print(f"  • {name}")

identity = IdentityContext("demo-architect", ["analyst"])
print("\n=== Retrieve ===")
r = f.retrieve("hybrid retrieval FinOps", identity)
for c in r["chunks"][:3]:
    print(f"  [{c['score']:.3f}] {c['source']}: {c['text'][:70]}...")

print("\n=== Chat via model gateway ===")
chat = f.chat([{"role": "user", "content": "Summarize platform FinOps tags"}], identity)
print(f"  model={chat['model_id']} provider={chat['provider']}")
print(f"  {chat['text'][:120]}...")

print("\n=== Orchestrate (HITL) ===")
orch = f.orchestrate("propose price change for club 5521", identity)
print(f"  approval_required={orch['approval_required']}")
print(f"  tools={[t['name']+':'+t['decision'] for t in orch['tool_calls']]}")

print("\n=== Control ===")
print(f"  audit_valid={f.control.audit.verify()} entries={len(f.control.audit.entries())}")
print(f"  finops={f.control.finops.summary()}")
print("OK")
PY
