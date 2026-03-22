"""
models.py
---------
All Pydantic request/response models for the ACM API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ─────────────────────────────────────────
# Telemetry ingestion
# ─────────────────────────────────────────

class Vector3D(BaseModel):
    x: float
    y: float
    z: float


class ObjectState(BaseModel):
    id: str
    type: str           # "SATELLITE" or "DEBRIS"
    r: Vector3D         # position [km]
    v: Vector3D         # velocity [km/s]


class TelemetryRequest(BaseModel):
    timestamp: str      # ISO 8601
    objects: List[ObjectState]


# ─────────────────────────────────────────
# Maneuver scheduling
# ─────────────────────────────────────────

class DeltaVVector(BaseModel):
    x: float            # ECI [km/s]
    y: float
    z: float


class BurnCommand(BaseModel):
    burn_id: str
    burnTime: str       # ISO 8601
    deltaV_vector: DeltaVVector


class ManeuverRequest(BaseModel):
    satelliteId: str
    maneuver_sequence: List[BurnCommand]


# ─────────────────────────────────────────
# Simulation step
# ─────────────────────────────────────────

class SimulationStepRequest(BaseModel):
    step_seconds: int = Field(gt=0, description="Number of seconds to advance simulation")