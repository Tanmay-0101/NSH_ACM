from fastapi import APIRouter
from models import TelemetryRequest
from state_manager import update_objects

router=APIRouter()

@router.post("/api/telemetry")
def ingest_telemetry(data: TelemetryRequest):

    processed_count=update_objects(data.objects)

    return {
        "status": "ACK",
        "processed_count": processed_count,
        "active_cdm_warnings": 0
    }
