from fastapi import APIRouter, HTTPException
from models import ManeuverRequest
from maneuver_manager import validate_and_schedule_maneuver

router = APIRouter()

@router.post("/api/maneuver/schedule")
def schedule_maneuver_api(data: ManeuverRequest):
    result = validate_and_schedule_maneuver(data)

    if not result["accepted"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "REJECTED",
                "reason": result["reason"],
                "validation": result["validation"]
            }
        )

    return {
        "status": "SCHEDULED",
        "validation": result["validation"]
    }
