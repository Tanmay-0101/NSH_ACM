"""
maneuver_manager.py
-------------------
Priority queue of scheduled burns, sorted by burnTime.

Fixes applied:
  1. Uses simulation clock (state_manager.get_sim_time_s) not real UTC
  2. Passes real GMST to LOS check so ECI→ECEF conversion is accurate
"""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from maneuver_engine import engine as maneuver_engine
from ground_station import check_maneuver_los

logger = logging.getLogger(__name__)

SIGNAL_LATENCY_S = 10.0


def _gmst_from_sim_time_s(sim_time_s: float) -> float:
    """
    Compute Greenwich Mean Sidereal Time in radians from simulation Unix timestamp.
    Same formula as state_manager._gst_from_sim_time() — kept here to avoid
    circular import.
    """
    J2000_UNIX           = 946728000.0
    SECONDS_PER_SIDEREAL = 86164.0905
    elapsed = sim_time_s - J2000_UNIX
    return (2 * math.pi * elapsed / SECONDS_PER_SIDEREAL) % (2 * math.pi)


@dataclass(order=True)
class ScheduledBurn:
    burn_time_s:  float
    satellite_id: str        = field(compare=False)
    burn_id:      str        = field(compare=False)
    delta_v_eci:  np.ndarray = field(compare=False)

    def __repr__(self):
        dv = np.linalg.norm(self.delta_v_eci) * 1000
        return f"<Burn {self.burn_id} sat={self.satellite_id} t={self.burn_time_s:.0f} ΔV={dv:.3f} m/s>"


class ManeuverQueue:

    def __init__(self):
        self._heap: list[ScheduledBurn] = []

    def schedule(
        self,
        maneuver_request,
        current_sim_state: dict[str, np.ndarray],
        current_sim_time_s: float,
    ) -> tuple[bool, str, Optional[float]]:

        import state_manager

        sat_id  = maneuver_request.satelliteId
        sat_state = current_sim_state.get(sat_id)
        sat_res   = state_manager.get_satellite_resources(sat_id)

        if sat_state is None:
            return False, f"Unknown satellite: {sat_id}", None
        if sat_res is None:
            return False, f"No resource record for: {sat_id}", None
        if getattr(sat_res, 'status', 'NOMINAL') == "GRAVEYARD":
            return False, f"Satellite {sat_id} is in graveyard orbit", None

        total_projected_mass = sat_res.total_mass_kg
        fuel_remaining       = sat_res.fuel_kg

        for cmd in maneuver_request.maneuver_sequence:
            # Parse burnTime
            burn_dt = datetime.fromisoformat(cmd.burnTime.replace("Z", "+00:00"))
            burn_s  = burn_dt.timestamp()
            offset  = burn_s - current_sim_time_s

            # Signal latency check (uses sim clock)
            if offset < SIGNAL_LATENCY_S:
                return False, (
                    f"Burn {cmd.burn_id} is {offset:.1f}s in the future — "
                    f"minimum is {SIGNAL_LATENCY_S}s (signal latency)"
                ), None

            # ── LOS check with REAL GMST at burn time ────────────────────────
            # Compute GMST at the actual burn time so ECI→ECEF is accurate
            gmst_at_burn = _gmst_from_sim_time_s(burn_s)

            los_ok, visible = check_maneuver_los(
                sat_eci           = sat_state[:3],
                burn_time_offset_s = offset,
                gmst_rad          = gmst_at_burn,   # ← was always 0.0 before
            )
            if not los_ok:
                return False, (
                    f"Burn {cmd.burn_id}: satellite {sat_id} has no ground station "
                    f"LOS at burn time (GMST={math.degrees(gmst_at_burn):.1f}°)"
                ), None

            # ΔV validation
            dv_vec = np.array([
                cmd.deltaV_vector.x,
                cmd.deltaV_vector.y,
                cmd.deltaV_vector.z,
            ], dtype=float)
            dv_mag = float(np.linalg.norm(dv_vec))

            from maneuver_engine import MAX_DELTA_V_KM_S
            if dv_mag > MAX_DELTA_V_KM_S:
                return False, (
                    f"Burn {cmd.burn_id}: ΔV {dv_mag*1000:.2f} m/s exceeds 15 m/s limit"
                ), None

            # Fuel check
            from maneuver_engine import tsiolkovsky_delta_mass
            delta_m = tsiolkovsky_delta_mass(total_projected_mass, dv_mag)
            if delta_m > fuel_remaining:
                return False, (
                    f"Burn {cmd.burn_id}: insufficient fuel "
                    f"(need {delta_m:.3f} kg, have {fuel_remaining:.3f} kg)"
                ), None

            fuel_remaining       -= delta_m
            total_projected_mass -= delta_m

            heapq.heappush(self._heap, ScheduledBurn(
                burn_time_s  = burn_s,
                satellite_id = sat_id,
                burn_id      = cmd.burn_id,
                delta_v_eci  = dv_vec,
            ))

        return True, "All burns validated and scheduled", total_projected_mass

    def execute_due_burns(self, current_sim_time_s: float) -> list[dict]:
        import state_manager

        reports = []
        while self._heap and self._heap[0].burn_time_s <= current_sim_time_s:
            burn = heapq.heappop(self._heap)

            sat_state = state_manager.get_satellite_state(burn.satellite_id)
            sat_res   = state_manager.get_satellite_resources(burn.satellite_id)

            if sat_state is None or sat_res is None:
                reports.append({
                    "burn_id": burn.burn_id,
                    "success": False,
                    "reason":  "Satellite not found",
                })
                continue

            new_state, success, reason = maneuver_engine.execute_burn(
                sat_state_6d      = sat_state,
                sat_resources     = sat_res,
                delta_v_eci       = burn.delta_v_eci,
                simulation_time_s = current_sim_time_s,
            )

            if success:
                state_manager.set_satellite_state(burn.satellite_id, new_state)

            reports.append({
                "burn_id":           burn.burn_id,
                "satellite_id":      burn.satellite_id,
                "success":           success,
                "reason":            reason,
                "fuel_remaining_kg": round(sat_res.fuel_kg, 3) if success else None,
            })

            logger.info(
                "Burn %s: %s — %s",
                burn.burn_id, "OK" if success else "FAIL", reason
            )

        return reports

    def pending_count(self) -> int:
        return len(self._heap)

    def peek_next(self) -> Optional[ScheduledBurn]:
        return self._heap[0] if self._heap else None


# Module-level singleton
queue = ManeuverQueue()


def schedule_maneuver(maneuver_request) -> tuple[bool, str, Optional[float]]:
    """Convenience wrapper used by maneuver_api.py."""
    import state_manager

    sat_states = dict(state_manager.satellites)
    # ── Use simulation clock, not real UTC ────────────────────────────────────
    now_s = state_manager.get_sim_time_s()

    return queue.schedule(maneuver_request, sat_states, now_s)