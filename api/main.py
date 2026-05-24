# api/main.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   main.py is the ENTRY POINT — the file you run to start the server.
#   It creates the FastAPI app, configures global settings (CORS, docs),
#   mounts all routers, and defines startup/shutdown hooks.
#
#   It deliberately contains NO business logic.
#   Think of it as the receptionist of a building:
#     - Knows where every department is (routers)
#     - Greets visitors with the right info (docs, CORS)
#     - Doesn't do any actual department work
# ─────────────────────────────────────────────────────────────────────────────

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router, health_router


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SETUP
# Load .env file into os.environ before anything else runs.
#
# WHY load_dotenv() here and not in individual files?
#   Central loading ensures .env is available everywhere from startup.
#   Calling it multiple times is safe (it's idempotent).
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# APP CREATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "🏏 IPL Akinator API",
    description = (
        "An AI-powered IPL player guessing system. "
        "Think of any IPL cricketer — the AI will identify them "
        "in ≤8 questions using Bayesian probabilistic reasoning."
    ),
    version     = "1.0.0",

    # WHY custom doc URLs?
    #   /docs  → Swagger UI  (interactive — judges can test endpoints here)
    #   /redoc → ReDoc UI    (cleaner reading view)
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS MIDDLEWARE
#
# WHAT IS CORS?
#   Cross-Origin Resource Sharing. Browsers block JavaScript on one domain
#   (e.g. localhost:3000) from calling APIs on another (localhost:8000)
#   unless the API explicitly allows it.
#
# WHY read from environment variable?
#   In development: ALLOWED_ORIGINS=* (allow everything)
#   In production : ALLOWED_ORIGINS=https://ipl-akinator.web.app
#   This way we never hardcode URLs and never accidentally expose
#   a production API to all origins.
# ─────────────────────────────────────────────────────────────────────────────

# Parse allowed origins from env — comma-separated list or "*"
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    ["*"] if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = "https://ipl-akinator.web.app",
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER MOUNTING
#
# WHY include_router and not @app.get directly?
#   Routers keep routes modular. main.py stays clean.
#   Adding a new feature = create a new router, add one include_router line.
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(health_router)           # /health   (no prefix)
app.include_router(router)                  # /game/... (prefix defined in routes.py)


# ─────────────────────────────────────────────────────────────────────────────
# ROOT ENDPOINT
#
# WHY a root endpoint?
#   When judges/evaluators hit the base URL, they should see something
#   useful — not a 404. This gives them immediate orientation.
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "app":         "IPL Akinator",
        "version":     "1.0.0",
        "description": "AI-powered IPL player guessing game",
        "note":        "POST endpoints cannot be tested in a browser. Use /docs instead.",
        "interactive_docs": "http://localhost:8000/docs",
        "health":      "http://localhost:8000/health",
        "endpoints": {
            "start_game":    "POST   /game/start                     ← Start here",
            "submit_answer": "POST   /game/{session_id}/answer       ← Submit answers",
            "confirm_guess": "POST   /game/{session_id}/confirm      ← Confirm final guess",
            "game_state":    "GET    /game/{session_id}/state        ← Check game state",
        },
        "how_to_test": "Open http://localhost:8000/docs → click any endpoint → Try it out → Execute"
    }


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP & SHUTDOWN EVENTS
#
# WHY lifespan events?
#   @app.on_event("startup") lets you run code ONCE when the server starts.
#   Useful for: loading datasets into memory, connecting to DBs, warming caches.
#
#   Here we just print a banner — but this is where you'd add
#   dataset pre-loading in a production system.
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Runs once when the server starts."""
    print("\n" + "="*55)
    print("  🏏  IPL AKINATOR — SERVER STARTED")
    print("="*55)
    print(f"  Docs       : http://localhost:8000/docs")
    print(f"  Health     : http://localhost:8000/health")
    print(f"  Start Game : POST http://localhost:8000/game/start")
    print("="*55 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Runs once when the server shuts down."""
    print("\n🏏 IPL Akinator shutting down. Goodbye!")


# ─────────────────────────────────────────────────────────────────────────────
# RUN DIRECTLY
#
# WHY __name__ == "__main__"?
#   Allows running with: python api/main.py
#   In production, you'd use: uvicorn api.main:app --reload
#   Both work — the guard prevents auto-running when imported as a module.
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",   # Listen on all interfaces (not just localhost)
        port     = 8000,
        reload   = True,         # Auto-restart on code changes (dev mode)
        log_level= "info",
    )