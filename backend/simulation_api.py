"""
simulation_api.py — with DANGER status on CDM detection
"""

from fastapi import APIRouter
from models import SimulationStepRequest
import state_manager
import physics_engine
import heapq
import logging
from maneuver_manager import queue as maneuver_queue
from collision_detector import detector
from autonomous_cola import cola_engine

router = APIRouter()
RK4_SUBSTEP = 10.0
logger = logging.getLogger(__name__)


@router.post("/api/simulate/step")
def simulate_step(data: SimulationStepRequest):
    current_time_s = state_manager.get_sim_time_s()
    new_time_s     = current_time_s + data.step_seconds

    # ── 1. Register station-keeping slots BEFORE propagation ─────────────────
    cola_engine.check_station_keeping(
        sat_states     = dict(state_manager.satellites),
        current_time_s = current_time_s,
    )

    # ── 2. Execute due burns ──────────────────────────────────────────────────
    burn_reports       = maneuver_queue.execute_due_burns(new_time_s)
    maneuvers_executed = sum(1 for r in burn_reports if r.get("success"))

    # ── 3. Propagate all objects (RK4 + J2) ──────────────────────────────────
    new_sats, new_deb = physics_engine.propagate_all(
        satellites   = dict(state_manager.satellites),
        debris       = dict(state_manager.debris),
        step_seconds = data.step_seconds,
        substep      = RK4_SUBSTEP,
    )
    for sat_id, s in new_sats.items():
        state_manager.set_satellite_state(sat_id, s)
    for deb_id, d in new_deb.items():
        state_manager.debris[deb_id] = d

    # ── 4. Build position dicts ───────────────────────────────────────────────
    sat_pos = {
        sid: {"position": s[:3].tolist(), "velocity": s[3:].tolist()}
        for sid, s in state_manager.satellites.items()
    }
    deb_pos = {
        did: {"position": d[:3].tolist(), "velocity": d[3:].tolist()}
        for did, d in state_manager.debris.items()
    }

    # ── 5. Collision detection ────────────────────────────────────────────────
    cdms = detector.check_conjunctions(
        sat_pos, deb_pos, state_manager.get_sim_timestamp()
    )
    collisions_detected = sum(1 for c in cdms if c.risk_level == "COLLISION")
    active_count = len([c for c in cdms if c.risk_level != "SAFE"])
    state_manager.set_active_cdm_count(active_count)

    logger.info(
        "STEP: cdms=%d levels=%s resources=%s",
        len(cdms),
        [c.risk_level for c in cdms],
        list(state_manager.resources.keys()),
    )

    # ── 6. Update satellite status based on CDM risk level ───────────────────
    # First reset all DANGER satellites that no longer have CDMs
    threatened_sats = {c.satellite_id for c in cdms if c.risk_level != "SAFE"}
    for sat_id, res in state_manager.resources.items():
        if res.status == "DANGER" and sat_id not in threatened_sats:
            res.status = "NOMINAL"

    # Now set DANGER for any satellite with an active CDM warning
    for cdm in cdms:
        res = state_manager.resources.get(cdm.satellite_id)
        if res is None:
            continue
        if cdm.risk_level == "COLLISION":
            # Imminent collision — red, highest alert
            res.status = "DANGER"
        elif cdm.risk_level == "CRITICAL":
            # Very close — red
            res.status = "DANGER"
        elif cdm.risk_level == "WARNING":
            # Getting close — also set DANGER so diamond turns red
            if res.status not in ("MANEUVERING", "GRAVEYARD"):
                res.status = "DANGER"

    # ── 7. Autonomous COLA ────────────────────────────────────────────────────
    auto_burns = cola_engine.process_cdms(
        cdms           = cdms,
        sat_states     = dict(state_manager.satellites),
        sat_resources  = state_manager.resources,
        current_time_s = current_time_s,
    )
    for burn in auto_burns:
        heapq.heappush(maneuver_queue._heap, burn)

    # ── 8. Post-propagation station-keeping ───────────────────────────────────
    sk_reports = cola_engine.check_station_keeping(
        sat_states     = dict(state_manager.satellites),
        current_time_s = new_time_s,
    )

    # ── 9. 24hr predictive assessment (every 10 ticks) ───────────────────────
    state_manager.increment_tick()
    if state_manager.get_tick_count() % 10 == 0 and sat_pos and deb_pos:
        predicted_cdms = detector.predict_conjunctions_ahead(
            satellites        = sat_pos,
            debris            = deb_pos,
            propagator        = physics_engine.propagate,
            lookahead_seconds = 86400.0,
            sample_interval   = 300.0,
        )
        future_burns = cola_engine.process_cdms(
            cdms           = [c for c in predicted_cdms
                              if c.risk_level in ("WARNING", "CRITICAL", "COLLISION")],
            sat_states     = dict(state_manager.satellites),
            sat_resources  = state_manager.resources,
            current_time_s = current_time_s,
            is_predictive  = True,
        )
        for burn in future_burns:
            heapq.heappush(maneuver_queue._heap, burn)

    # ── 10. Advance sim clock ─────────────────────────────────────────────────
    state_manager.set_sim_time_s(new_time_s)

    return {
        "status":               "STEP_COMPLETE",
        "new_timestamp":        state_manager.get_sim_timestamp(),
        "collisions_detected":  collisions_detected,
        "maneuvers_executed":   maneuvers_executed,
        "auto_burns_scheduled": len(auto_burns),
        "active_cdm_warnings":  state_manager.get_active_cdm_count(),
        "station_keeping":      sk_reports,
        "objects_propagated":   len(new_sats) + len(new_deb),
        "burn_reports":         burn_reports,
    }