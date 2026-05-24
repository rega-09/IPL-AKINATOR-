# run.py  (project root — always run from here)
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE?
#   Running `uvicorn api.main:app` directly has a Windows path issue —
#   uvicorn spawns a subprocess that loses the correct sys.path context.
#
#   This file ensures:
#     1. The project root is always in sys.path
#     2. uvicorn starts with the correct app reference
#     3. Works identically on Windows, Mac, and Linux
#
# HOW TO RUN:
#     python run.py
#
# This is equivalent to: uvicorn api.main:app --reload --port 8000
#   but with guaranteed correct path resolution on all platforms.
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

# Add the project root to sys.path FIRST, before any imports
# WHY? This ensures `import api`, `import engine`, `import utils`
# all resolve correctly regardless of where Python was invoked from.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host      = "0.0.0.0",
        port      = 8000,
        reload    = True,
        log_level = "info",
        # WHY reload_dirs?
        # Tells uvicorn to watch the whole project, not just api/
        # So changes in engine/ or utils/ also trigger a reload
        reload_dirs = [PROJECT_ROOT],
    )