"""
state_manager.py
----------------
Central in-memory store for all simulation objects.

Stores:
  - satellites   : { id -> np.ndarray shape (6,) [x,y,z,vx,vy,vz] ECI km/km/s }
  - debris       : { id -> np.ndarray shape (6,) }
  - resources    : { id -> SatelliteResources }
  - sim_time_s   : current simulation time as Unix timestamp (float)
  - active_cdms  : current active CDM warning count
  - tick_count   : number of simulation steps completed
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

# ── Physical constants ────────────────────────────────────────────────────────
DRY_MASS_KG   = 500.0
INIT_FUEL_KG  = 50.0
EOL_FUEL_FRAC = 0.05

# ── State stores ──────────────────────────────────────────────────────────────
satellites: dict[str, np.ndarray] = {}
debris:     dict[str, np.ndarray] = {}

sim_time_s: float = datetime(2026, 3, 22, 10, 0, 0, tzinfo=timezone.utc).timestamp()
_active_cdm_count: int = 0
_tick_count: int = 0


@dataclass
class SatelliteResources:
    fuel_kg:          float = INIT_FUEL_KG
    dry_mass_kg:      float = DRY_MASS_KG
    status:           str   = "NOMINAL"
    last_burn_s:      float = -600.0   # allow immediate first burn

    @property
    def total_mass_kg(self) -> float:
        return self.dry_mass_kg + self.fuel_kg

    @property
    def fuel_fraction(self) -> float:
        return self.fuel_kg / INIT_FUEL_KG

    @property
    def is_eol(self) -> bool:
        return self.fuel_fraction <= EOL_FUEL_FRAC

    # alias for maneuver_engine compatibility
    @property
    def last_burn_time_s(self) -> float:
        return self.last_burn_s

    @last_burn_time_s.setter
    def last_burn_time_s(self, v: float):
        self.last_burn_s = v

    def to_dict(self) -> dict:
        return {
            "fuel_kg":           round(self.fuel_kg, 4),
            "total_mass_kg":     round(self.total_mass_kg, 4),
            "fuel_fraction_pct": round(self.fuel_fraction * 100, 2),
            "status":            self.status,
        }


resources: dict[str, SatelliteResources] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_resources(sat_id: str) -> SatelliteResources:
    if sat_id not in resources:
        resources[sat_id] = SatelliteResources()
    return resources[sat_id]


def update_objects(objects) -> int:
    processed = 0
    for obj in objects:
        state = np.array([
            obj.r.x, obj.r.y, obj.r.z,
            obj.v.x, obj.v.y, obj.v.z,
        ], dtype=float)
        if obj.type.upper() == "SATELLITE":
            satellites[obj.id] = state
            res = _ensure_resources(obj.id)
            # Keep existing resource record — don't reset fuel on re-telemetry
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
    """Update sim clock from ISO string. Only advances, never goes backward."""
    global sim_time_s
    try:
        incoming_s = datetime.fromisoformat(
            iso_string.replace("Z", "+00:00")
        ).timestamp()
        if incoming_s > sim_time_s:
            sim_time_s = incoming_s
    except (ValueError, AttributeError):
        pass


def get_active_cdm_count() -> int:
    return _active_cdm_count


def set_active_cdm_count(n: int) -> None:
    global _active_cdm_count
    _active_cdm_count = n


def get_tick_count() -> int:
    return _tick_count


def increment_tick() -> None:
    global _tick_count
    _tick_count += 1


# ── ECI → geodetic conversion ─────────────────────────────────────────────────

def eci_to_geodetic(x_km: float, y_km: float, z_km: float, gst_rad: float = 0.0):
    r  = math.sqrt(x_km**2 + y_km**2 + z_km**2)
    RE = 6378.137

    lon_rad = math.atan2(y_km, x_km) - gst_rad
    lon_rad = (lon_rad + math.pi) % (2 * math.pi) - math.pi
    lat_rad = math.asin(z_km / r)
    alt_km  = r - RE

    return math.degrees(lat_rad), math.degrees(lon_rad), round(alt_km, 2)


def _gst_from_sim_time() -> float:
    J2000_UNIX             = 946728000.0
    SECONDS_PER_SIDEREAL   = 86164.0905
    elapsed = sim_time_s - J2000_UNIX
    return (2 * math.pi * elapsed / SECONDS_PER_SIDEREAL) % (2 * math.pi)


# ── Snapshot builder ──────────────────────────────────────────────────────────

def build_snapshot() -> dict:
    gst = _gst_from_sim_time()

    sat_list = []
    for sat_id, state in satellites.items():
        res = resources.get(sat_id)
        lat, lon, alt = eci_to_geodetic(state[0], state[1], state[2], gst)

        status = "NOMINAL"
        if res:
            if res.status == "GRAVEYARD":
                status = "GRAVEYARD"
            elif res.is_eol:
                status = "CRITICAL"
                res.status = "CRITICAL"
            elif res.status in ("MANEUVERING", "LOW_FUEL"):
                # Auto-reset to NOMINAL once cooldown expires and fuel is healthy
                cooldown_expired = (sim_time_s - res.last_burn_s) > 600.0
                if cooldown_expired and res.fuel_fraction > 0.20:
                    res.status = "NOMINAL"
                status = res.status
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

    # ΔV efficiency stats for UI graph
    try:
        from autonomous_cola import cola_engine
        efficiency = cola_engine.get_efficiency_stats()
    except Exception:
        efficiency = {}

    return {
        "timestamp":           get_sim_timestamp(),
        "satellites":          sat_list,
        "debris_cloud":        debris_list,
        "active_cdm_warnings": _active_cdm_count,
        "efficiency_stats":    efficiency,
    }