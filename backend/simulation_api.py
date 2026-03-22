"""
simulation_api.py
-----------------
POST /api/simulate/step

Advances simulation time using real RK4+J2 orbital propagation.
Executes any scheduled maneuver burns in the time window.
"""

from fastapi import APIRouter
from models import SimulationStepRequest
import state_manager
import physics_engine
from maneuver_manager import queue as maneuver_queue

router = APIRouter()

RK4_SUBSTEP = 10.0  # seconds — RK4 sub-step size


@router.post("/api/simulate/step")
def simulate_step(data: SimulationStepRequest):
    current_time_s = state_manager.get_sim_time_s()
    new_time_s     = current_time_s + data.step_seconds

    # 1. Execute any burns scheduled within this time window
    burn_reports       = maneuver_queue.execute_due_burns(new_time_s)
    maneuvers_executed = sum(1 for r in burn_reports if r.get("success"))

    # 2. Propagate ALL objects forward using RK4 + J2
    new_sats, new_deb = physics_engine.propagate_all(
        satellites   = dict(state_manager.satellites),
        debris       = dict(state_manager.debris),
        step_seconds = data.step_seconds,
        substep      = RK4_SUBSTEP,
    )

    # 3. Write propagated states back
    for sat_id, new_state in new_sats.items():
        state_manager.set_satellite_state(sat_id, new_state)
    for deb_id, new_state in new_deb.items():
        state_manager.debris[deb_id] = new_state

    # 4. Advance sim clock
    state_manager.set_sim_time_s(new_time_s)

    return {
        "status":              "STEP_COMPLETE",
        "new_timestamp":       state_manager.get_sim_timestamp(),
        "collisions_detected": 0,
        "maneuvers_executed":  maneuvers_executed,
        "objects_propagated":  len(new_sats) + len(new_deb),
        "burn_reports":        burn_reports,
    }