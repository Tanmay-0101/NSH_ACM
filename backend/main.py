from fastapi import FastAPI
from telemetry_api import router as telemetry_router
from maneuver_api import router as maneuver_router
from simulation_api import router as simulation_router
from visualization_api import router as visualization_router

app=FastAPI(
    title="Autonomous Constellation Manager",
    version="1.0"
)

app.include_router(telemetry_router)
app.include_router(maneuver_router)
app.include_router(simulation_router)
app.include_router(visualization_router)