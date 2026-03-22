"""
physics_engine.py
-----------------
Orbital propagation engine using:
  - RK4 (4th-order Runge-Kutta) numerical integrator
  - J2 perturbation (Earth's equatorial bulge)
  - Impulsive maneuver burns (ΔV applied instantaneously)

All units:
  position  → km
  velocity  → km/s
  time      → seconds
  mass      → kg
"""

from __future__ import annotations

import numpy as np
from typing import Dict

# ── Physical constants (from problem statement) ───────────────────────────────
MU    = 398600.4418       # km³/s²  — Earth gravitational parameter
RE    = 6378.137          # km      — Earth equatorial radius
J2    = 1.08263e-3        # —       — J2 zonal harmonic coefficient
G0    = 9.80665e-3        # km/s²   — standard gravity (converted from m/s²)
ISP   = 300.0             # s       — specific impulse
MAX_DV_KMS = 0.015        # km/s    — 15 m/s max per burn


# ── J2 acceleration ───────────────────────────────────────────────────────────

def _j2_acceleration(r_vec: np.ndarray) -> np.ndarray:
    """
    Compute J2 perturbation acceleration vector in ECI frame.

    Parameters
    ----------
    r_vec : np.ndarray shape (3,)  — position in km

    Returns
    -------
    a_j2 : np.ndarray shape (3,)  — acceleration in km/s²
    """
    x, y, z = r_vec
    r = np.linalg.norm(r_vec)
    r2 = r * r
    r5 = r2 * r2 * r

    factor = (3.0 / 2.0) * J2 * MU * RE**2 / r5
    z2_r2  = (z / r) ** 2

    ax = factor * x * (5.0 * z2_r2 - 1.0)
    ay = factor * y * (5.0 * z2_r2 - 1.0)
    az = factor * z * (5.0 * z2_r2 - 3.0)

    return np.array([ax, ay, az])


# ── Equations of motion ───────────────────────────────────────────────────────

def _derivatives(state: np.ndarray) -> np.ndarray:
    """
    Compute d/dt [r, v] = [v, a_gravity + a_J2]

    Parameters
    ----------
    state : np.ndarray shape (6,)  — [x, y, z, vx, vy, vz]

    Returns
    -------
    dstate : np.ndarray shape (6,)
    """
    r_vec = state[:3]
    v_vec = state[3:]

    r     = np.linalg.norm(r_vec)
    r3    = r * r * r

    # Two-body gravity
    a_grav = -(MU / r3) * r_vec

    # J2 perturbation
    a_j2   = _j2_acceleration(r_vec)

    a_total = a_grav + a_j2

    return np.concatenate([v_vec, a_total])


# ── RK4 integrator ────────────────────────────────────────────────────────────

def rk4_step(state: np.ndarray, dt: float) -> np.ndarray:
    """
    Advance state by one RK4 step of size dt seconds.

    Parameters
    ----------
    state : np.ndarray shape (6,)
    dt    : float  — time step in seconds

    Returns
    -------
    new_state : np.ndarray shape (6,)
    """
    k1 = _derivatives(state)
    k2 = _derivatives(state + 0.5 * dt * k1)
    k3 = _derivatives(state + 0.5 * dt * k2)
    k4 = _derivatives(state + dt * k3)

    return state + (dt / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)


def propagate(state: np.ndarray, total_seconds: float, substep: float = 10.0) -> np.ndarray:
    """
    Propagate a state vector forward by total_seconds using RK4.

    Uses sub-steps of `substep` seconds for accuracy.
    For a 1-hour step with 10s substeps = 360 RK4 iterations per object.

    Parameters
    ----------
    state         : np.ndarray shape (6,)
    total_seconds : float  — total time to propagate
    substep       : float  — RK4 sub-step size in seconds (default 10s)

    Returns
    -------
    new_state : np.ndarray shape (6,)
    """
    remaining = total_seconds
    current   = state.copy()

    while remaining > 0.0:
        dt      = min(substep, remaining)
        current = rk4_step(current, dt)
        remaining -= dt

    return current


# ── Fleet propagation ─────────────────────────────────────────────────────────

def propagate_all(
    satellites: Dict[str, np.ndarray],
    debris:     Dict[str, np.ndarray],
    step_seconds: float,
    substep: float = 10.0,
) -> tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Propagate every satellite and debris object forward by step_seconds.

    Called by simulation_api on each /api/simulate/step request.

    Parameters
    ----------
    satellites   : {id: state_6d}
    debris       : {id: state_6d}
    step_seconds : float
    substep      : float  — RK4 sub-step (default 10s)

    Returns
    -------
    (new_satellites, new_debris) — updated state dicts
    """
    new_sats = {
        sid: propagate(state, step_seconds, substep)
        for sid, state in satellites.items()
    }
    new_deb = {
        did: propagate(state, step_seconds, substep)
        for did, state in debris.items()
    }
    return new_sats, new_deb


# ── Tsiolkovsky fuel consumption ──────────────────────────────────────────────

def tsiolkovsky_delta_mass(current_mass_kg: float, dv_km_s: float) -> float:
    """
    Mass of propellant consumed for a given ΔV burn.

    Δm = m_current × (1 - e^(-|ΔV| / (Isp × g0)))

    Parameters
    ----------
    current_mass_kg : float  — wet mass before burn (kg)
    dv_km_s         : float  — |ΔV| in km/s

    Returns
    -------
    delta_m : float  — propellant consumed in kg
    """
    exhaust_velocity = ISP * G0  # km/s
    delta_m = current_mass_kg * (1.0 - np.exp(-abs(dv_km_s) / exhaust_velocity))
    return delta_m


# ── RTN ↔ ECI rotation ────────────────────────────────────────────────────────

def rtn_to_eci_matrix(r_vec: np.ndarray, v_vec: np.ndarray) -> np.ndarray:
    """
    Build the 3×3 rotation matrix from RTN frame to ECI frame.

    R (Radial)    : r_vec / |r_vec|
    N (Normal)    : (r × v) / |r × v|
    T (Transverse): N × R

    Parameters
    ----------
    r_vec : np.ndarray shape (3,)  — ECI position
    v_vec : np.ndarray shape (3,)  — ECI velocity

    Returns
    -------
    M : np.ndarray shape (3, 3)
        Columns are R, T, N unit vectors in ECI.
        Multiply RTN vector by M to get ECI vector.
    """
    R_hat = r_vec / np.linalg.norm(r_vec)
    N_hat = np.cross(r_vec, v_vec)
    N_hat = N_hat / np.linalg.norm(N_hat)
    T_hat = np.cross(N_hat, R_hat)

    # Columns: R, T, N
    return np.column_stack([R_hat, T_hat, N_hat])


def dv_rtn_to_eci(
    dv_rtn: np.ndarray,
    r_vec:  np.ndarray,
    v_vec:  np.ndarray,
) -> np.ndarray:
    """
    Convert a ΔV vector from RTN frame to ECI frame.

    Parameters
    ----------
    dv_rtn : np.ndarray shape (3,)  — [dVr, dVt, dVn] in km/s
    r_vec  : np.ndarray shape (3,)  — ECI position (km)
    v_vec  : np.ndarray shape (3,)  — ECI velocity (km/s)

    Returns
    -------
    dv_eci : np.ndarray shape (3,)  — ΔV in ECI frame (km/s)
    """
    M = rtn_to_eci_matrix(r_vec, v_vec)
    return M @ dv_rtn


# ── Collision avoidance ΔV planner ────────────────────────────────────────────

def plan_evasion_burn(
    sat_state:  np.ndarray,
    deb_state:  np.ndarray,
    tca_s:      float,
    standoff_km: float = 0.5,
) -> np.ndarray:
    """
    Calculate a simple prograde evasion burn in RTN frame.

    Strategy: small prograde ΔV raises the orbit's semi-major axis,
    shifting the satellite's position at TCA away from the debris.

    This is a simplified Hohmann-style approach — sufficient for the
    hackathon's autonomous avoidance requirement.

    Parameters
    ----------
    sat_state   : current satellite state (6,)
    deb_state   : current debris state (6,)
    tca_s       : seconds until closest approach
    standoff_km : desired miss distance in km (default 0.5 km)

    Returns
    -------
    dv_eci : np.ndarray shape (3,)  — recommended ΔV in ECI (km/s)
    """
    r_sat = sat_state[:3]
    v_sat = sat_state[3:]
    r_deb = deb_state[:3]

    # Current miss vector
    miss_vec  = r_sat - r_deb
    miss_dist = np.linalg.norm(miss_vec)

    # Scale needed ΔV: rough linear estimate
    # A 1 m/s prograde burn shifts position by ~1 km per orbit period
    # We need standoff_km separation at TCA
    dv_mag = min(0.001 * standoff_km, MAX_DV_KMS)  # km/s, capped at 15 m/s

    # Prograde direction (T in RTN) — most fuel-efficient
    dv_rtn = np.array([0.0, dv_mag, 0.0])
    dv_eci = dv_rtn_to_eci(dv_rtn, r_sat, v_sat)

    return dv_eci


# ── Apply ΔV to state vector ──────────────────────────────────────────────────

def apply_delta_v_eci(state_6d: np.ndarray, delta_v_eci: np.ndarray) -> np.ndarray:
    """
    Apply an impulsive ΔV to a satellite state vector.

    Adds delta_v_eci to the velocity component of the state.
    Position is unchanged (impulsive burn assumption).

    Parameters
    ----------
    state_6d     : np.ndarray shape (6,)  — [x, y, z, vx, vy, vz]
    delta_v_eci  : np.ndarray shape (3,)  — ΔV in ECI [km/s]

    Returns
    -------
    new_state : np.ndarray shape (6,)
    """
    new_state = state_6d.copy()
    new_state[3] += delta_v_eci[0]
    new_state[4] += delta_v_eci[1]
    new_state[5] += delta_v_eci[2]
    return new_state