"""
autonomous_cola.py
------------------
Autonomous Collision Avoidance (COLA) engine.

Fixed: works with state_manager.SatelliteResources directly.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from physics_engine import rtn_to_eci_matrix, tsiolkovsky_delta_mass, MAX_DV_KMS
from maneuver_manager import ScheduledBurn
from collision_detector import ConjunctionDataMessage

logger = logging.getLogger(__name__)

SIGNAL_LATENCY_S       = 10.0
COOLDOWN_S             = 600.0
STATION_KEEP_RADIUS_KM = 10.0
EOL_FUEL_FRACTION      = 0.05
EVASION_DV_KMS         = 0.008   # 8 m/s
GRAVEYARD_DV_KMS       = 0.010


@dataclass
class StationKeepingRecord:
    satellite_id: str
    nominal_slot_pos: np.ndarray      # ECI position at registration time
    outage_start_s: Optional[float] = None
    total_outage_s: float = 0.0
    is_in_slot: bool = True


class AutonomousCOLA:
    def __init__(self):
        self._evading_pairs: set[tuple[str, str]] = set()
        self._sk_records: dict[str, StationKeepingRecord] = {}
        self.collisions_avoided: int = 0
        self.total_dv_spent_kms: float = 0.0

    # ── COLA ──────────────────────────────────────────────────────────────────

    def process_cdms(
        self,
        cdms: list[ConjunctionDataMessage],
        sat_states: dict[str, np.ndarray],
        sat_resources: dict,
        current_time_s: float,
        is_predictive: bool = False,
    ) -> list[ScheduledBurn]:

        new_burns: list[ScheduledBurn] = []

        for cdm in cdms:
            if cdm.risk_level not in ("WARNING", "CRITICAL", "COLLISION"):
                continue

            pair_key = (cdm.satellite_id, cdm.debris_id)
            if pair_key in self._evading_pairs:
                continue

            sat_id    = cdm.satellite_id
            sat_state = sat_states.get(sat_id)
            sat_res   = sat_resources.get(sat_id)

            if sat_state is None or sat_res is None:
                logger.warning("COLA: no state/resources for %s", sat_id)
                continue

            if getattr(sat_res, 'status', 'NOMINAL') == "GRAVEYARD":
                continue

            fuel_kg = getattr(sat_res, 'fuel_kg', 0.0)
            if fuel_kg < 0.5:
                logger.warning("COLA: insufficient fuel for %s (%.2f kg)", sat_id, fuel_kg)
                continue

            # ── Burn timing ───────────────────────────────────────────────
            last_burn = getattr(sat_res, 'last_burn_s',
                        getattr(sat_res, 'last_burn_time_s', current_time_s - COOLDOWN_S - 1))
            cooldown_remaining = max(0.0, last_burn + COOLDOWN_S - current_time_s)
            evasion_time_s = current_time_s + SIGNAL_LATENCY_S + cooldown_remaining + 5.0

            if is_predictive:
                evasion_time_s += 3600.0

            # ── ΔV calculation (prograde RTN → ECI) ──────────────────────
            r_vec  = sat_state[:3]
            v_vec  = sat_state[3:]
            total_mass = getattr(sat_res, 'total_mass_kg', 550.0)
            dv_mag = min(EVASION_DV_KMS, fuel_kg * 0.3 / total_mass * 10.0)
            dv_mag = max(dv_mag, 0.002)   # minimum 2 m/s

            dv_rtn = np.array([0.0, dv_mag, 0.0])
            M      = rtn_to_eci_matrix(r_vec, v_vec)
            dv_eci = M @ dv_rtn

            # ── Evasion burn ──────────────────────────────────────────────
            evasion_burn = ScheduledBurn(
                burn_time_s  = evasion_time_s,
                satellite_id = sat_id,
                burn_id      = f"AUTO_EVASION_{sat_id}_{int(evasion_time_s)}",
                delta_v_eci  = dv_eci,
            )
            new_burns.append(evasion_burn)

            # ── Recovery burn (~90 min later, retrograde) ─────────────────
            recovery_time_s     = evasion_time_s + COOLDOWN_S + 5400.0
            dv_recovery_eci     = M @ np.array([0.0, -dv_mag * 0.95, 0.0])

            recovery_burn = ScheduledBurn(
                burn_time_s  = recovery_time_s,
                satellite_id = sat_id,
                burn_id      = f"AUTO_RECOVERY_{sat_id}_{int(recovery_time_s)}",
                delta_v_eci  = dv_recovery_eci,
            )
            new_burns.append(recovery_burn)

            self._evading_pairs.add(pair_key)
            self.collisions_avoided += 1
            self.total_dv_spent_kms += dv_mag * 2

            logger.info(
                "AUTO-COLA: %s evading %s | evasion@%.0f recovery@%.0f | dv=%.4f km/s",
                sat_id, cdm.debris_id, evasion_time_s, recovery_time_s, dv_mag
            )

            # ── EOL check ─────────────────────────────────────────────────
            projected_fuel = fuel_kg - tsiolkovsky_delta_mass(total_mass, dv_mag) * 2
            if projected_fuel / 50.0 <= EOL_FUEL_FRACTION:
                gb = self._schedule_graveyard_burn(sat_id, sat_state, current_time_s + 7200.0)
                if gb:
                    new_burns.append(gb)

        # ── Standalone EOL check ──────────────────────────────────────────────
        for sat_id, res in sat_resources.items():
            fuel_frac = getattr(res, 'fuel_fraction',
                        getattr(res, 'fuel_kg', 50.0) / 50.0)
            status = getattr(res, 'status', 'NOMINAL')
            if fuel_frac <= EOL_FUEL_FRACTION and status != "GRAVEYARD":
                sat_state = sat_states.get(sat_id)
                if sat_state is not None:
                    gb = self._schedule_graveyard_burn(
                        sat_id, sat_state, current_time_s + SIGNAL_LATENCY_S + 15.0
                    )
                    if gb:
                        new_burns.append(gb)
                        res.status = "GRAVEYARD"

        return new_burns

    # ── Station-keeping ───────────────────────────────────────────────────────

    def check_station_keeping(
        self,
        sat_states: dict[str, np.ndarray],
        current_time_s: float,
    ) -> list[dict]:
        reports = []

        for sat_id, state in sat_states.items():
            # Register nominal slot on FIRST sighting
            if sat_id not in self._sk_records:
                self._sk_records[sat_id] = StationKeepingRecord(
                    satellite_id     = sat_id,
                    nominal_slot_pos = state[:3].copy(),
                )
                logger.info("Station-keeping slot registered for %s at %.1f,%.1f,%.1f km",
                            sat_id, state[0], state[1], state[2])

            record = self._sk_records[sat_id]
            drift_km = float(np.linalg.norm(state[:3] - record.nominal_slot_pos))
            in_slot  = drift_km <= STATION_KEEP_RADIUS_KM

            if not in_slot and record.is_in_slot:
                record.outage_start_s = current_time_s
                logger.warning("SAT %s LEFT slot! drift=%.2f km", sat_id, drift_km)

            elif in_slot and not record.is_in_slot:
                if record.outage_start_s is not None:
                    record.total_outage_s += current_time_s - record.outage_start_s
                    logger.info("SAT %s RETURNED to slot", sat_id)
                record.outage_start_s = None

            record.is_in_slot = in_slot

            reports.append({
                "satellite_id":   sat_id,
                "drift_km":       round(drift_km, 3),
                "in_slot":        in_slot,
                "total_outage_s": round(record.total_outage_s, 1),
                "status":         "NOMINAL" if in_slot else "OUTAGE",
            })

        return reports

    def get_efficiency_stats(self) -> dict:
        return {
            "collisions_avoided":   self.collisions_avoided,
            "total_dv_spent_ms":    round(self.total_dv_spent_kms * 1000, 3),
            "avg_dv_per_avoidance": round(
                (self.total_dv_spent_kms * 1000 / self.collisions_avoided)
                if self.collisions_avoided > 0 else 0.0, 3
            ),
        }

    def reset_evading_pairs(self) -> None:
        self._evading_pairs.clear()

    def _schedule_graveyard_burn(
        self, sat_id: str, sat_state: np.ndarray, burn_time_s: float
    ) -> Optional[ScheduledBurn]:
        r_vec  = sat_state[:3]
        v_vec  = sat_state[3:]
        dv_mag = min(GRAVEYARD_DV_KMS, MAX_DV_KMS)
        M      = rtn_to_eci_matrix(r_vec, v_vec)
        dv_eci = M @ np.array([0.0, dv_mag, 0.0])
        logger.warning("Scheduling GRAVEYARD burn for %s", sat_id)
        return ScheduledBurn(
            burn_time_s  = burn_time_s,
            satellite_id = sat_id,
            burn_id      = f"GRAVEYARD_{sat_id}_{int(burn_time_s)}",
            delta_v_eci  = dv_eci,
        )


cola_engine = AutonomousCOLA()