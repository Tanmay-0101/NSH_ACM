"""
maneuver_api.py
---------------
POST /api/maneuver/schedule

Validates and enqueues a maneuver sequence.
Checks: signal latency, ΔV limits, fuel budget, ground station LOS.
"""

from fastapi import APIRouter, HTTPException
from models import ManeuverRequest
from maneuver_manager import schedule_maneuver

router = APIRouter()


@router.post("/api/maneuver/schedule", status_code=202)
def schedule_maneuver_api(data: ManeuverRequest):
    success, message, projected_mass = schedule_maneuver(data)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "status": "SCHEDULED",
        "validation": {
            "ground_station_los": True,
            "sufficient_fuel": True,
            "projected_mass_remaining_kg": round(projected_mass, 2) if projected_mass else None,
            "message": message,
        },
    }