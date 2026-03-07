from pydantic import BaseModel
from typing import List

# models for telemetry api
class Vector3D(BaseModel):
    x:float
    y:float
    z:float

class ObjectState(BaseModel):
    id:str
    type:str
    r:Vector3D
    v:Vector3D

class TelemetryRequest(BaseModel):
    timestamp:str
    objects:List[ObjectState]

# models for maneuever scheduling api
class DeltaVVector(BaseModel):
    x: float
    y: float
    z: float


class BurnCommand(BaseModel):
    burn_id: str
    burnTime: str
    deltaV_vector: DeltaVVector


class ManeuverRequest(BaseModel):
    satelliteId: str
    maneuver_sequence: List[BurnCommand]

#model for simulation step
class SimulationStepRequest(BaseModel):
    step_seconds: int