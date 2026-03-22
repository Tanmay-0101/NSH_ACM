"""
main.py
-------
Autonomous Constellation Manager — FastAPI application entry point.
Binds on 0.0.0.0:8000 as required by the Docker grading environment.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from telemetry_api import router as telemetry_router
from maneuver_api import router as maneuver_router
from simulation_api import router as simulation_router
from visualization_api import router as visualization_router

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Autonomous Constellation Manager",
    version="1.0",
    description=(
        "Backend engine for orbital debris avoidance and constellation management. "
        "Implements J2-perturbed RK4 propagation, KD-tree conjunction detection, "
        "and autonomous maneuver scheduling."
    ),
)

# CORS — allow the React frontend (any origin in dev, tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(telemetry_router)
app.include_router(maneuver_router)
app.include_router(simulation_router)
app.include_router(visualization_router)


@app.get("/")
def root():
    return {
        "system": "Autonomous Constellation Manager",
        "version": "1.0",
        "status": "ONLINE",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    import state_manager
    return {
        "status": "OK",
        "satellites_tracked": len(state_manager.satellites),
        "debris_tracked": len(state_manager.debris),
        "active_cdms": state_manager.get_active_cdm_count(),
        "pending_burns": __import__("maneuver_manager").queue.pending_count(),
    }