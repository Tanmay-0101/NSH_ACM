"""
maneuver_engine.py
------------------
Applies scheduled burns to satellite states and tracks propellant.
Fixed: removed sat_resources.satellite_id references (field doesn't exist
       on state_manager.SatelliteResources).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from physics_engine import (
    rtn_to_eci_matrix,
    apply_delta_v_eci,
    tsiolkovsky_delta_mass,
)

logger = logging.getLogger(__name__)

# --- Spacecraft constants (from problem statement) ---
DRY_MASS_KG            = 500.0
INITIAL_FUEL_KG        = 50.0
INITIAL_WET_MASS_KG    = 550.0
ISP_S                  = 300.0
MAX_DELTA_V_KM_S       = 0.015
THRUSTER_COOLDOWN_S    = 600.0
FUEL_EOL_FRACTION      = 0.05


@dataclass
class SatelliteResources:
    """
    Used only when maneuver_api creates a resource manually.
    The live resources are stored in state_manager.SatelliteResources.
    """
    satellite_id: str
    fuel_kg: float = field(default=INITIAL_FUEL_KG)
    last_burn_time_s: float = field(default=-THRUSTER_COOLDOWN_S)
    status: str = "NOMINAL"

    @property
    def total_mass_kg(self) -> float:
        return DRY_MASS_KG + self.fuel_kg

    @property
    def fuel_fraction(self) -> float:
        return self.fuel_kg / INITIAL_FUEL_KG

    @property
    def is_eol(self) -> bool:
        return self.fuel_fraction <= FUEL_EOL_FRACTION

    def to_dict(self) -> dict:
        return {
            "satellite_id":      self.satellite_id,
            "fuel_kg":           round(self.fuel_kg, 4),
            "total_mass_kg":     round(self.total_mass_kg, 4),
            "fuel_fraction_pct": round(self.fuel_fraction * 100, 2),
            "status":            self.status,
        }


class ManeuverEngine:

    def execute_burn(
        self,
        sat_state_6d: np.ndarray,
        sat_resources,           # accepts both SatelliteResources types
        delta_v_eci: np.ndarray,
        simulation_time_s: float,
    ) -> tuple[np.ndarray, bool, str]:

        dv_mag = float(np.linalg.norm(delta_v_eci))

        # ── Validation ────────────────────────────────────────────────────────
        if dv_mag > MAX_DELTA_V_KM_S:
            return sat_state_6d, False, f"ΔV {dv_mag*1000:.2f} m/s exceeds 15 m/s limit"

        # Support both last_burn_time_s and last_burn_s attribute names
        last_burn = getattr(sat_resources, 'last_burn_time_s',
                    getattr(sat_resources, 'last_burn_s', simulation_time_s - THRUSTER_COOLDOWN_S - 1))

        cooldown_remaining = last_burn + THRUSTER_COOLDOWN_S - simulation_time_s
        if cooldown_remaining > 0:
            return sat_state_6d, False, f"Thruster cooldown: {cooldown_remaining:.0f}s remaining"

        fuel_kg    = getattr(sat_resources, 'fuel_kg', INITIAL_FUEL_KG)
        total_mass = getattr(sat_resources, 'total_mass_kg', DRY_MASS_KG + fuel_kg)

        delta_m = tsiolkovsky_delta_mass(total_mass, dv_mag)
        if delta_m > fuel_kg:
            return sat_state_6d, False, (
                f"Insufficient fuel: need {delta_m:.3f} kg, have {fuel_kg:.3f} kg"
            )

        # ── Execute burn ──────────────────────────────────────────────────────
        new_state = apply_delta_v_eci(sat_state_6d, delta_v_eci)

        # Update fuel
        sat_resources.fuel_kg -= delta_m

        # Update last burn time — support both attribute names
        if hasattr(sat_resources, 'last_burn_time_s'):
            sat_resources.last_burn_time_s = simulation_time_s
        if hasattr(sat_resources, 'last_burn_s'):
            sat_resources.last_burn_s = simulation_time_s

        # Update status
        new_fuel_fraction = sat_resources.fuel_kg / INITIAL_FUEL_KG
        if new_fuel_fraction <= FUEL_EOL_FRACTION:
            sat_resources.status = "GRAVEYARD"
            logger.warning("Satellite fuel at EOL (%.1f%%) — graveyard required",
                           new_fuel_fraction * 100)
        elif new_fuel_fraction < 0.20:
            sat_resources.status = "LOW_FUEL"
        else:
            sat_resources.status = "MANEUVERING"

        logger.info(
            "Burn executed: ΔV=%.4f km/s  Δm=%.3f kg  fuel_remaining=%.3f kg  status=%s",
            dv_mag, delta_m, sat_resources.fuel_kg, sat_resources.status,
        )

        return new_state, True, "OK"

    def delta_v_rtn_to_eci(
        self,
        sat_state_6d: np.ndarray,
        delta_v_rtn: np.ndarray,
    ) -> np.ndarray:
        r = sat_state_6d[:3]
        v = sat_state_6d[3:]
        M = rtn_to_eci_matrix(r, v)
        return M @ delta_v_rtn

    def projected_mass_after_burn(
        self,
        sat_resources,
        delta_v_km_s: float,
    ) -> float:
        total_mass = getattr(sat_resources, 'total_mass_kg', 550.0)
        delta_m    = tsiolkovsky_delta_mass(total_mass, delta_v_km_s)
        return total_mass - delta_m


# Module-level singleton
engine = ManeuverEngine()