"""sys.path setup for integration tests that span multiple service packages.

Both services use a bare `src/` namespace package. We load each in isolation
and re-register the modules under unique names so they stay in sys.modules
and are patchable via patch.object.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

_REPO = Path(__file__).parents[2]


def _load_service_module(service: str, module: str) -> ModuleType:
    """Import src.<module> from services/<service>/ in isolation.

    Clears any cached `src.*` entries before and after, then stores the result
    under a unique key so patch.object can find it.
    """
    svc_root = str(_REPO / "services" / service)
    sys.path.insert(0, svc_root)
    try:
        for key in list(sys.modules):
            if key == "src" or key.startswith("src."):
                del sys.modules[key]
        __import__(f"src.{module}")
        return sys.modules[f"src.{module}"]
    finally:
        sys.path.remove(svc_root)
        # Clear again so subsequent imports from other services start clean
        for key in list(sys.modules):
            if key == "src" or key.startswith("src."):
                del sys.modules[key]


# Load once at collection time; stored as module objects for patch.object use.
admin_reindex_mod = _load_service_module("admin-service", "reindex")
indexing_coordinator_mod = _load_service_module("indexing-service", "coordinator")

# Register under unique names so they survive in sys.modules
sys.modules["_admin_reindex"] = admin_reindex_mod
sys.modules["_indexing_coordinator"] = indexing_coordinator_mod

# Exported callables
trigger_reindex = admin_reindex_mod.trigger_reindex
swap_index = admin_reindex_mod.swap_index
maybe_complete_document = indexing_coordinator_mod.maybe_complete_document
maybe_complete_indexing_job = indexing_coordinator_mod.maybe_complete_indexing_job
