from fastapi import APIRouter
from models import SimulationStepRequest

router=APIRouter()

current_time = "2026-03-12T08:00:00.000Z"

@router.post("/api/simulate/step")
def simulate_step(data: SimulationStepRequest):
    # Later this will call the simulation engine
    # For now we return a dummy response

    return {
        "status": "STEP_COMPLETE",
        "new_timestamp": current_time,
        "collisions_detected": 0,
        "maneuvers_executed": 0
    }