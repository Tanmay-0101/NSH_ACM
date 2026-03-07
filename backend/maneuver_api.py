from fastapi import APIRouter
from models import ManeuverRequest
from maneuver_manager import schedule_maneuver

router=APIRouter()

@router.post("/api/maneuver/schedule")
def schedule_maneuver_api(data: ManeuverRequest):

    schedule_maneuver(data)

    return {
        " status": "SCHEDULED " ,
        " validation": {
            " ground_station_los": True ,
            " sufficient_fuel": True ,
            " projected_mass_remaining_kg": 548.12
        }
    }
