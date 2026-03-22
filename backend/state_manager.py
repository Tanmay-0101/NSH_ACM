"""
state_manager.py
----------------
Central in-memory store for all simulation objects.

Stores:
  - satellites : { id -> np.ndarray shape (6,) [x,y,z,vx,vy,vz] in km / km/s ECI }
  - debris     : { id -> np.ndarray shape (6,) }
  - resources  : { id -> SatelliteResources }
  - sim_time_s : current simulation time as Unix timestamp (float)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

# ── physical constants ────────────────────────────────────────────────────────
DRY_MASS_KG   = 500.0
INIT_FUEL_KG  = 50.0
EOL_FUEL_FRAC = 0.05   # 5% threshold → graveyard

# ── state stores ─────────────────────────────────────────────────────────────
satellites: dict[str, np.ndarray] = {}   # ECI state vectors
debris:     dict[str, np.ndarray] = {}

sim_time_s: float = datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc).timestamp()


@dataclass
class SatelliteResources:
    fuel_kg:       float = INIT_FUEL_KG
    dry_mass_kg:   float = DRY_MASS_KG
    status:        str   = "NOMINAL"   # NOMINAL | EVADING | RECOVERING | GRAVEYARD
    last_burn_s:   float = 0.0         # sim time of last burn (for cooldown)

    @property
    def total_mass_kg(self) -> float:
        return self.dry_mass_kg + self.fuel_kg

    @property
    def fuel_fraction(self) -> float:
        return self.fuel_kg / INIT_FUEL_KG


resources: dict[str, SatelliteResources] = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_resources(sat_id: str) -> SatelliteResources:
    if sat_id not in resources:
        resources[sat_id] = SatelliteResources()
    return resources[sat_id]


def update_objects(objects) -> int:
    """Parse incoming telemetry and update state stores."""
    processed = 0
    for obj in objects:
        state = np.array([
            obj.r.x, obj.r.y, obj.r.z,
            obj.v.x, obj.v.y, obj.v.z,
        ], dtype=float)

        if obj.type.upper() == "SATELLITE":
            satellites[obj.id] = state
            _ensure_resources(obj.id)
        else:
            debris[obj.id] = state

        processed += 1
    return processed


def get_satellite_state(sat_id: str) -> Optional[np.ndarray]:
    return satellites.get(sat_id)


def set_satellite_state(sat_id: str, state: np.ndarray) -> None:
    satellites[sat_id] = state


def get_satellite_resources(sat_id: str) -> Optional[SatelliteResources]:
    return resources.get(sat_id)


def get_sim_time_s() -> float:
    return sim_time_s


def set_sim_time_s(t: float) -> None:
    global sim_time_s
    sim_time_s = t


def get_sim_timestamp() -> str:
    return datetime.fromtimestamp(sim_time_s, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )


def set_timestamp(iso_string: str) -> None:
    global sim_time_s
    try:
        incoming_s = datetime.fromisoformat(
            iso_string.replace("Z", "+00:00")
        ).timestamp()
        if incoming_s > sim_time_s:
            sim_time_s = incoming_s
    except (ValueError, AttributeError):
        pass


# ── ECI → geodetic conversion ─────────────────────────────────────────────────

def eci_to_geodetic(x_km: float, y_km: float, z_km: float, gst_rad: float = 0.0):
    """
    Convert ECI (km) to (lat_deg, lon_deg, alt_km).

    gst_rad : Greenwich Sidereal Time in radians.
              Pass 0.0 for a rough approximation (good enough for visualisation).
    """
    r = math.sqrt(x_km**2 + y_km**2 + z_km**2)
    RE = 6378.137  # km

    # Longitude: rotate ECI X/Y by GST to get ECEF
    lon_rad = math.atan2(y_km, x_km) - gst_rad
    # Normalise to [-π, π]
    lon_rad = (lon_rad + math.pi) % (2 * math.pi) - math.pi

    # Latitude (geocentric, good enough for display)
    lat_rad = math.asin(z_km / r)

    alt_km = r - RE

    return math.degrees(lat_rad), math.degrees(lon_rad), round(alt_km, 2)


def _gst_from_sim_time() -> float:
    """Approximate Greenwich Sidereal Time from simulation Unix timestamp."""
    # J2000 epoch: 2000-01-01 12:00:00 UTC = 946728000.0 Unix
    J2000_UNIX = 946728000.0
    SECONDS_PER_SIDEREAL_DAY = 86164.0905
    elapsed = sim_time_s - J2000_UNIX
    gst_rad = (2 * math.pi * elapsed / SECONDS_PER_SIDEREAL_DAY) % (2 * math.pi)
    return gst_rad


# ── snapshot builder (called by visualization_api) ────────────────────────────

def build_snapshot() -> dict:
    """Return the full visualization snapshot from live state."""
    gst = _gst_from_sim_time()

    sat_list = []
    for sat_id, state in satellites.items():
        res = resources.get(sat_id)
        lat, lon, alt = eci_to_geodetic(state[0], state[1], state[2], gst)

        # Check EOL threshold
        status = "NOMINAL"
        if res:
            if res.status == "GRAVEYARD":
                status = "GRAVEYARD"
            elif res.fuel_fraction <= EOL_FUEL_FRAC:
                status = "CRITICAL"
                res.status = "CRITICAL"
            else:
                status = res.status

        sat_list.append({
            "id":      sat_id,
            "lat":     round(lat, 4),
            "lon":     round(lon, 4),
            "alt_km":  alt,
            "fuel_kg": round(res.fuel_kg, 3) if res else INIT_FUEL_KG,
            "status":  status,
        })

    debris_list = []
    for deb_id, state in debris.items():
        lat, lon, alt = eci_to_geodetic(state[0], state[1], state[2], gst)
        debris_list.append([deb_id, round(lat, 3), round(lon, 3), round(alt, 1)])

    return {
        "timestamp":           get_sim_timestamp(),
        "satellites":          sat_list,
        "debris_cloud":        debris_list,
        "active_cdm_warnings": 0,   # updated by collision_detector when wired in
    }