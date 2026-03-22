"""
ground_station.py
-----------------
Line-of-sight (LOS) computation between satellites and ground stations.

A satellite can receive commands only if it has geometric line-of-sight
to at least one ground station above that station's minimum elevation
angle mask.

All angles in degrees unless noted.
Positions use ECI [km] for satellites, geodetic (lat/lon/elev) for stations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# --- Ground station network (from problem statement) ---
GROUND_STATIONS_CSV = [
    # id, name, lat, lon, elev_m, min_elev_angle_deg
    ("GS-001", "ISTRAC_Bengaluru",        13.0333,   77.5167,  820, 5.0),
    ("GS-002", "Svalbard_Sat_Station",    78.2297,   15.4077,  400, 5.0),
    ("GS-003", "Goldstone_Tracking",      35.4266, -116.8900, 1000, 10.0),
    ("GS-004", "Punta_Arenas",           -53.1500,  -70.9167,   30, 5.0),
    ("GS-005", "IIT_Delhi_Ground_Node",   28.5450,   77.1926,  225, 15.0),
    ("GS-006", "McMurdo_Station",        -77.8463,  166.6682,   10, 5.0),
]

RE_KM = 6378.137   # Earth radius [km]


@dataclass
class GroundStation:
    station_id: str
    name: str
    lat_deg: float
    lon_deg: float
    elevation_m: float
    min_elevation_angle_deg: float

    @property
    def ecef_position(self) -> np.ndarray:
        """
        Return ECEF position of the ground station [km].
        Uses spherical Earth approximation (sufficient for LOS checks).
        """
        lat = math.radians(self.lat_deg)
        lon = math.radians(self.lon_deg)
        r = RE_KM + self.elevation_m / 1000.0

        return np.array([
            r * math.cos(lat) * math.cos(lon),
            r * math.cos(lat) * math.sin(lon),
            r * math.sin(lat),
        ])


def _build_stations() -> list[GroundStation]:
    return [
        GroundStation(row[0], row[1], row[2], row[3], row[4], row[5])
        for row in GROUND_STATIONS_CSV
    ]


STATIONS: list[GroundStation] = _build_stations()


def elevation_angle_deg(
    station: GroundStation,
    sat_ecef: np.ndarray,
) -> float:
    """
    Compute the elevation angle (degrees above horizon) of a satellite
    as seen from a ground station.

    Parameters
    ----------
    station : GroundStation
    sat_ecef : np.ndarray shape (3,)
        Satellite position in ECEF [km].

    Returns
    -------
    float
        Elevation angle in degrees. Negative = below horizon.
    """
    gs_pos = station.ecef_position
    rho = sat_ecef - gs_pos          # Range vector from station to satellite
    rho_norm = np.linalg.norm(rho)

    if rho_norm < 1e-9:
        return 90.0  # Satellite is at the station (shouldn't happen)

    # Unit nadir vector from station (points toward Earth center)
    zenith = gs_pos / np.linalg.norm(gs_pos)

    # Elevation = complement of angle between zenith and range vector
    cos_angle = np.dot(zenith, rho) / rho_norm
    # elevation = arcsin of the component along zenith direction
    el_rad = math.asin(max(-1.0, min(1.0, cos_angle)))

    return math.degrees(el_rad)


def eci_to_ecef(r_eci: np.ndarray, gmst_rad: float = 0.0) -> np.ndarray:
    """
    Rotate ECI position to ECEF using Earth's rotation angle (GMST).

    For real-time accuracy, pass the actual Greenwich Mean Sidereal Time.
    For a quick LOS check pass gmst_rad = 0.0 — acceptable for short windows.
    """
    cos_g = math.cos(gmst_rad)
    sin_g = math.sin(gmst_rad)

    R = np.array([
        [ cos_g, sin_g, 0],
        [-sin_g, cos_g, 0],
        [     0,     0, 1],
    ])
    return R @ r_eci


def has_line_of_sight(
    sat_eci: np.ndarray,
    gmst_rad: float = 0.0,
) -> tuple[bool, list[str]]:
    """
    Check whether a satellite has LOS to at least one ground station.

    Parameters
    ----------
    sat_eci : np.ndarray shape (3,)
        Satellite ECI position [km].
    gmst_rad : float
        Earth rotation angle (radians). Pass 0.0 for approximate result.

    Returns
    -------
    (has_los, visible_station_ids) : tuple[bool, list[str]]
    """
    sat_ecef = eci_to_ecef(sat_eci, gmst_rad)

    visible = []
    for station in STATIONS:
        el = elevation_angle_deg(station, sat_ecef)
        if el >= station.min_elevation_angle_deg:
            visible.append(station.station_id)

    return len(visible) > 0, visible


def check_maneuver_los(
    sat_eci: np.ndarray,
    burn_time_offset_s: float = 10.0,
    gmst_rad: float = 0.0,
) -> tuple[bool, list[str]]:
    """
    Validate that a maneuver can be uplinked.

    The burn must occur at least 10 s in the future (signal latency).
    The satellite must have LOS at the time of the burn.

    Parameters
    ----------
    sat_eci : np.ndarray shape (3,)
        Satellite position at planned burn time [km].
    burn_time_offset_s : float
        Seconds from now until the burn. Must be >= 10.
    gmst_rad : float
        Earth rotation at burn time.

    Returns
    -------
    (valid, visible_stations)
    """
    if burn_time_offset_s < 10.0:
        return False, []

    return has_line_of_sight(sat_eci, gmst_rad)