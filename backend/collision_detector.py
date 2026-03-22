"""
collision_detector.py
---------------------
Efficient conjunction assessment using a KD-tree spatial index.

Avoids the O(N²) brute-force approach required by the problem statement.
Strategy:
  1. Build a KD-tree over all debris positions.
  2. For each satellite, query the tree for debris within a coarse radius.
  3. Run exact distance checks only on that small candidate set.
  4. Flag any pair under CONJUNCTION_THRESHOLD_KM as a CDM.

All positions in ECI [km].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.spatial import KDTree

logger = logging.getLogger(__name__)

# --- Thresholds (from problem statement) ---
CONJUNCTION_THRESHOLD_KM = 0.100   # 100 metres — hard collision threshold
WARNING_RADIUS_KM         = 5.0    # Yellow warning zone
CRITICAL_RADIUS_KM        = 1.0    # Red critical zone
COARSE_QUERY_RADIUS_KM    = 50.0   # KD-tree pre-filter radius (much larger than threshold)


@dataclass
class ConjunctionDataMessage:
    """Represents a predicted close approach between one satellite and one debris."""

    satellite_id: str
    debris_id: str
    miss_distance_km: float
    time_of_closest_approach: Optional[str] = None   # ISO timestamp, set when predicted
    risk_level: str = "SAFE"                         # SAFE | WARNING | CRITICAL | COLLISION

    def __post_init__(self):
        self.risk_level = self._classify_risk()

    def _classify_risk(self) -> str:
        if self.miss_distance_km < CONJUNCTION_THRESHOLD_KM:
            return "COLLISION"
        elif self.miss_distance_km < CRITICAL_RADIUS_KM:
            return "CRITICAL"
        elif self.miss_distance_km < WARNING_RADIUS_KM:
            return "WARNING"
        return "SAFE"

    def to_dict(self) -> dict:
        return {
            "satellite_id": self.satellite_id,
            "debris_id": self.debris_id,
            "miss_distance_km": round(self.miss_distance_km, 4),
            "time_of_closest_approach": self.time_of_closest_approach,
            "risk_level": self.risk_level,
        }


class CollisionDetector:
    """
    Stateless conjunction assessor.

    Call `check_conjunctions` with the current satellite and debris
    state dicts on every simulation tick (or on demand).
    """

    def __init__(self, coarse_radius_km: float = COARSE_QUERY_RADIUS_KM):
        self.coarse_radius_km = coarse_radius_km

    def check_conjunctions(
        self,
        satellites: dict[str, dict],
        debris: dict[str, dict],
        current_timestamp: Optional[str] = None,
    ) -> list[ConjunctionDataMessage]:
        """
        Run conjunction assessment for all (satellite, debris) pairs.

        Parameters
        ----------
        satellites : dict
            { id: {"position": [x,y,z], "velocity": [vx,vy,vz], ...} }
        debris : dict
            Same structure.
        current_timestamp : str | None
            ISO timestamp to attach to each CDM.

        Returns
        -------
        list[ConjunctionDataMessage]
            All pairs within WARNING_RADIUS_KM, sorted by miss distance.
        """
        if not satellites or not debris:
            return []

        # Build KD-tree over debris positions
        debris_ids   = list(debris.keys())
        debris_pos   = np.array([debris[d]["position"] for d in debris_ids])  # (N_deb, 3)

        tree = KDTree(debris_pos)

        cdms: list[ConjunctionDataMessage] = []

        for sat_id, sat_state in satellites.items():
            sat_pos = np.array(sat_state["position"])  # (3,)

            # Coarse filter: find debris within coarse_radius_km
            candidate_indices = tree.query_ball_point(sat_pos, r=self.coarse_radius_km)

            if not candidate_indices:
                continue

            # Exact distance check on candidates
            for idx in candidate_indices:
                deb_pos = debris_pos[idx]
                dist_km = float(np.linalg.norm(sat_pos - deb_pos))

                if dist_km < WARNING_RADIUS_KM:
                    cdm = ConjunctionDataMessage(
                        satellite_id=sat_id,
                        debris_id=debris_ids[idx],
                        miss_distance_km=dist_km,
                        time_of_closest_approach=current_timestamp,
                    )
                    cdms.append(cdm)

        cdms.sort(key=lambda c: c.miss_distance_km)
        return cdms

    def count_active_warnings(
        self,
        satellites: dict[str, dict],
        debris: dict[str, dict],
    ) -> int:
        """
        Quick count of active conjunctions (WARNING or worse).
        Used to populate active_cdm_warnings in telemetry ACK.
        """
        cdms = self.check_conjunctions(satellites, debris)
        return sum(1 for c in cdms if c.risk_level in ("WARNING", "CRITICAL", "COLLISION"))

    def predict_conjunctions_ahead(
        self,
        satellites: dict[str, dict],
        debris: dict[str, dict],
        propagator,
        lookahead_seconds: float = 86400.0,   # 24 hours
        sample_interval: float = 60.0,         # sample every 60 s
        current_timestamp: Optional[str] = None,
    ) -> list[ConjunctionDataMessage]:
        """
        Predict conjunctions up to `lookahead_seconds` in the future
        by sampling propagated positions at `sample_interval` steps.

        This is a computationally heavier operation — call asynchronously
        or on a background thread, not on every tick.

        Parameters
        ----------
        propagator : callable
            A function f(state_6d, dt_seconds) → state_6d.
            Pass physics_engine.propagate.
        lookahead_seconds : float
            How far ahead to look (default = 24 h).
        sample_interval : float
            Time between samples in seconds.

        Returns
        -------
        list[ConjunctionDataMessage]
            All predicted conjunctions, tagged with approximate TCA.
        """
        import copy

        # Work on copies so we don't mutate live state
        sat_states  = {sid: np.array(s["position"] + s["velocity"] if len(s["position"]) == 3
                                     else s["position"])
                       for sid, s in satellites.items()}

        # Build full 6D state arrays
        sat_6d  = {}
        for sid, s in satellites.items():
            pos = s["position"]
            vel = s["velocity"]
            sat_6d[sid] = np.array(pos + vel, dtype=float)

        deb_6d = {}
        for did, d in debris.items():
            pos = d["position"]
            vel = d["velocity"]
            deb_6d[did] = np.array(pos + vel, dtype=float)

        all_cdms: list[ConjunctionDataMessage] = []
        seen_pairs: set[tuple[str, str]] = set()

        elapsed = 0.0
        while elapsed <= lookahead_seconds:
            # Propagate all objects to this time step
            if elapsed > 0:
                sat_6d = {sid: propagator(s, sample_interval) for sid, s in sat_6d.items()}
                deb_6d = {did: propagator(d, sample_interval) for did, d in deb_6d.items()}

            # Build position-only dicts for detector
            sat_pos_dict = {sid: {"position": s[:3].tolist(), "velocity": s[3:].tolist()}
                            for sid, s in sat_6d.items()}
            deb_pos_dict = {did: {"position": d[:3].tolist(), "velocity": d[3:].tolist()}
                            for did, d in deb_6d.items()}

            step_cdms = self.check_conjunctions(sat_pos_dict, deb_pos_dict, current_timestamp)

            for cdm in step_cdms:
                pair = (cdm.satellite_id, cdm.debris_id)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    all_cdms.append(cdm)

            elapsed += sample_interval

        all_cdms.sort(key=lambda c: c.miss_distance_km)
        return all_cdms


# Module-level singleton — imported by other modules
detector = CollisionDetector()