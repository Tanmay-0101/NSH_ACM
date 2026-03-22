"""
telemetry_api.py
----------------
POST /api/telemetry

High-frequency endpoint. Parses incoming state vectors and updates
the in-memory store. Returns ACK with live CDM warning count.
"""

from fastapi import APIRouter
from models import TelemetryRequest
import state_manager
# import collision_detector as cd
import collision_detector as cd

router = APIRouter()


@router.post("/api/telemetry")
def ingest_telemetry(data: TelemetryRequest):
    # Update state for all objects in the payload
    processed_count = state_manager.update_objects(data.objects)

    # Update simulation clock to match telemetry timestamp if it's newer
    state_manager.set_timestamp(data.timestamp)

    # Quick CDM count from current in-memory state
    sat_pos = {
        sid: {"position": s[:3].tolist(), "velocity": s[3:].tolist()}
        for sid, s in state_manager.satellites.items()
    }
    deb_pos = {
        did: {"position": d[:3].tolist(), "velocity": d[3:].tolist()}
        for did, d in state_manager.debris.items()
    }
    active_cdm_warnings = cd.detector.count_active_warnings(sat_pos, deb_pos)

    return {
        "status": "ACK",
        "processed_count": processed_count,
        "active_cdm_warnings": active_cdm_warnings,
    }