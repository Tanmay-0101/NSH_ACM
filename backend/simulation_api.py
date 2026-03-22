from fastapi import APIRouter
from models import SimulationStepRequest
from state_manager import advance_simulation_time
from simulation_engine import (
    execute_due_maneuvers,
    propagate_objects_rk4,
    detect_collisions_kdtree
)

router=APIRouter()

current_time = "2026-03-12T08:00:00.000Z"

@router.post("/api/simulate/step")
def simulate_step(data: SimulationStepRequest):
    new_time = advance_simulation_time(data.step_seconds)
    executed_count = execute_due_maneuvers(new_time)
    propagate_objects_rk4(data.step_seconds, substep_seconds=60)
    warnings = detect_collisions_kdtree(
        threshold_km=0.1,
        horizon_seconds=86400,
        sample_seconds=300, # sample after each 5 miniutes for the next 24 hours
        substep_seconds=60, # for rk4 propagation
        candidate_radius_km=20.0 # radius used by KD tree to filter candidate debris
    )

    return {
        "status": "STEP_COMPLETE",
        "new_timestamp": new_time,
        "collisions_detected": len(warnings),
        "maneuvers_executed": executed_count
    }