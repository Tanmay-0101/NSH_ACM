"""
maneuver_engine.py
------------------
Applies scheduled burns to satellite states and tracks propellant.

Responsibilities:
  - Convert RTN ΔV → ECI ΔV using the rotation matrix from physics_engine.
  - Apply impulsive burn to velocity vector.
  - Compute and deduct propellant mass via Tsiolkovsky equation.
  - Enforce per-satellite thruster cooldown (600 s between burns).
  - Enforce per-burn ΔV magnitude limit (≤ 15 m/s = 0.015 km/s).
  - Flag a satellite for graveyard orbit if fuel drops below 5 %.
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
DRY_MASS_KG            = 500.0    # kg
INITIAL_FUEL_KG        = 50.0     # kg
INITIAL_WET_MASS_KG    = 550.0    # kg
ISP_S                  = 300.0    # s
MAX_DELTA_V_KM_S       = 0.015    # 15 m/s per burn
THRUSTER_COOLDOWN_S    = 600.0    # seconds between burns
FUEL_EOL_FRACTION      = 0.05     # graveyard trigger at 5 % of initial fuel


@dataclass
class SatelliteResources:
    """
    Tracks the mutable physical state of a single satellite.
    Stored in state_manager — one instance per satellite.
    """
    satellite_id: str
    fuel_kg: float = field(default=INITIAL_FUEL_KG)
    last_burn_time_s: float = field(default=-THRUSTER_COOLDOWN_S)  # allow immediate first burn
    status: str = "NOMINAL"   # NOMINAL | MANEUVERING | LOW_FUEL | GRAVEYARD

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
            "satellite_id": self.satellite_id,
            "fuel_kg": round(self.fuel_kg, 4),
            "total_mass_kg": round(self.total_mass_kg, 4),
            "fuel_fraction_pct": round(self.fuel_fraction * 100, 2),
            "status": self.status,
        }


class ManeuverEngine:
    """
    Applies burns to satellite states, mutating both the orbital state
    (velocity) and the resource state (fuel_kg, last_burn_time_s).
    """

    def execute_burn(
        self,
        sat_state_6d: np.ndarray,
        sat_resources: SatelliteResources,
        delta_v_eci: np.ndarray,
        simulation_time_s: float,
    ) -> tuple[np.ndarray, bool, str]:
        """
        Apply one impulsive burn to a satellite.

        Parameters
        ----------
        sat_state_6d : np.ndarray shape (6,)
            Current [x, y, z, vx, vy, vz] in ECI [km, km/s].
        sat_resources : SatelliteResources
            Mutable resource object (modified in place).
        delta_v_eci : np.ndarray shape (3,)
            ΔV vector in ECI [km/s].
        simulation_time_s : float
            Current simulation time (seconds since epoch) for cooldown tracking.

        Returns
        -------
        (new_state, success, reason)
        """
        dv_mag = float(np.linalg.norm(delta_v_eci))

        # --- Validation ---
        if dv_mag > MAX_DELTA_V_KM_S:
            return sat_state_6d, False, f"ΔV {dv_mag*1000:.2f} m/s exceeds 15 m/s limit"

        cooldown_remaining = (
            sat_resources.last_burn_time_s + THRUSTER_COOLDOWN_S - simulation_time_s
        )
        if cooldown_remaining > 0:
            return sat_state_6d, False, f"Thruster in cooldown: {cooldown_remaining:.0f} s remaining"

        # Propellant required
        delta_m = tsiolkovsky_delta_mass(sat_resources.total_mass_kg, dv_mag)
        if delta_m > sat_resources.fuel_kg:
            return sat_state_6d, False, (
                f"Insufficient fuel: need {delta_m:.3f} kg, have {sat_resources.fuel_kg:.3f} kg"
            )

        # --- Execute burn ---
        new_state = apply_delta_v_eci(sat_state_6d, delta_v_eci)

        # Update resources
        sat_resources.fuel_kg -= delta_m
        sat_resources.last_burn_time_s = simulation_time_s

        # Update status
        if sat_resources.is_eol:
            sat_resources.status = "GRAVEYARD"
            logger.warning(
                "Satellite %s fuel at EOL (%.1f%%) — graveyard orbit required",
                sat_resources.satellite_id,
                sat_resources.fuel_fraction * 100,
            )
        elif sat_resources.fuel_fraction < 0.20:
            sat_resources.status = "LOW_FUEL"
        else:
            sat_resources.status = "MANEUVERING"

        logger.info(
            "Burn executed: sat=%s  ΔV=%.4f km/s  Δm=%.3f kg  fuel_remaining=%.3f kg",
            sat_resources.satellite_id,
            dv_mag,
            delta_m,
            sat_resources.fuel_kg,
        )

        return new_state, True, "OK"

    def delta_v_rtn_to_eci(
        self,
        sat_state_6d: np.ndarray,
        delta_v_rtn: np.ndarray,
    ) -> np.ndarray:
        """
        Convert a ΔV given in RTN coordinates to ECI coordinates.

        Parameters
        ----------
        sat_state_6d : np.ndarray shape (6,)
        delta_v_rtn : np.ndarray shape (3,)
            [ΔV_R, ΔV_T, ΔV_N] in km/s.

        Returns
        -------
        np.ndarray shape (3,)
            ΔV in ECI [km/s].
        """
        r = sat_state_6d[:3]
        v = sat_state_6d[3:]
        M = rtn_to_eci_matrix(r, v)   # columns = [R̂, T̂, N̂]
        return M @ delta_v_rtn

    def projected_mass_after_burn(
        self,
        sat_resources: SatelliteResources,
        delta_v_km_s: float,
    ) -> float:
        """
        Preview how much mass will remain after a hypothetical burn.
        Does not modify resources.
        """
        delta_m = tsiolkovsky_delta_mass(sat_resources.total_mass_kg, delta_v_km_s)
        return sat_resources.total_mass_kg - delta_m


# Module-level singleton
engine = ManeuverEngine()