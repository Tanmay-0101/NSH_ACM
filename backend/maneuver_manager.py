from math import sqrt, exp
from datetime import datetime

from state_manager import satellites, get_current_timestamp

DRY_MASS_KG = 500.0
INITIAL_FUEL_KG = 50.0
ISP_SECONDS = 300.0
G0 = 9.80665
MAX_BURN_DV_MPS = 15.0
COOLDOWN_SECONDS = 600
COMMAND_LATENCY_SECONDS = 10

scheduled_maneuvers = []


def parse_time_z(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", ""))


def dv_magnitude_mps(delta_v_vector: dict) -> float:
    dv_kms = sqrt(
        delta_v_vector["x"] ** 2 +
        delta_v_vector["y"] ** 2 +
        delta_v_vector["z"] ** 2
    )
    return dv_kms * 1000.0


def propellant_used_kg(current_mass_kg: float, dv_mps: float) -> float:
    return current_mass_kg * (1.0 - exp(-dv_mps / (ISP_SECONDS * G0)))


def has_ground_station_los(satellite_id: str, burn_time: str) -> bool:
    return True # Later we will replace it with real LOS logic.


def validate_cooldown(satellite_id: str, burn_times: list[datetime]) -> bool:
    burn_times = sorted(burn_times)

    for i in range(1, len(burn_times)):
        if (burn_times[i] - burn_times[i - 1]).total_seconds() < COOLDOWN_SECONDS:
            return False

    existing_times = []
    for maneuver in scheduled_maneuvers:
        if maneuver["satelliteId"] == satellite_id:
            existing_times.append(parse_time_z(maneuver["burnTime"]))

    for new_bt in burn_times:
        for existing_bt in existing_times:
            if abs((new_bt - existing_bt).total_seconds()) < COOLDOWN_SECONDS:
                return False

    return True


def validate_and_schedule_maneuver(maneuver_request):
    satellite_id = maneuver_request.satelliteId

    if satellite_id not in satellites:
        return {
            "accepted": False,
            "reason": "Satellite not found",
            "validation": {
                "ground_station_los": False,
                "sufficient_fuel": False,
                "projected_mass_remaining_kg": None
            }
        }

    sat = satellites[satellite_id]

    current_time = parse_time_z(get_current_timestamp())
    burn_times = []
    ground_station_los = True

    current_fuel_kg = sat.get("fuel_kg", INITIAL_FUEL_KG)
    current_mass_kg = DRY_MASS_KG + current_fuel_kg
    total_propellant_needed = 0.0

    for burn in maneuver_request.maneuver_sequence:
        burn_time = parse_time_z(burn.burnTime)
        burn_times.append(burn_time)

        if (burn_time - current_time).total_seconds() < COMMAND_LATENCY_SECONDS:
            return {
                "accepted": False,
                "reason": "Burn violates 10-second command latency",
                "validation": {
                    "ground_station_los": False,
                    "sufficient_fuel": False,
                    "projected_mass_remaining_kg": round(current_mass_kg, 3)
                }
            }

        if not has_ground_station_los(satellite_id, burn.burnTime):
            ground_station_los = False

        dv_vec = {
            "x": burn.deltaV_vector.x,
            "y": burn.deltaV_vector.y,
            "z": burn.deltaV_vector.z
        }

        dv_mps = dv_magnitude_mps(dv_vec)

        if dv_mps > MAX_BURN_DV_MPS:
            return {
                "accepted": False,
                "reason": f"Burn exceeds max delta-v of {MAX_BURN_DV_MPS} m/s",
                "validation": {
                    "ground_station_los": ground_station_los,
                    "sufficient_fuel": False,
                    "projected_mass_remaining_kg": round(current_mass_kg, 3)
                }
            }

        dm = propellant_used_kg(current_mass_kg, dv_mps)
        total_propellant_needed += dm
        current_mass_kg -= dm

    if not validate_cooldown(satellite_id, burn_times):
        return {
            "accepted": False,
            "reason": "Burn sequence violates 600-second cooldown constraint",
            "validation": {
                "ground_station_los": ground_station_los,
                "sufficient_fuel": False,
                "projected_mass_remaining_kg": round(current_mass_kg, 3)
            }
        }

    projected_fuel_remaining = current_fuel_kg - total_propellant_needed
    sufficient_fuel = projected_fuel_remaining >= 0.0
    projected_mass_remaining = DRY_MASS_KG + max(projected_fuel_remaining, 0.0)

    if not sufficient_fuel:
        return {
            "accepted": False,
            "reason": "Insufficient fuel",
            "validation": {
                "ground_station_los": ground_station_los,
                "sufficient_fuel": False,
                "projected_mass_remaining_kg": round(projected_mass_remaining, 3)
            }
        }

    if not ground_station_los:
        return {
            "accepted": False,
            "reason": "No ground station line-of-sight for one or more burns",
            "validation": {
                "ground_station_los": False,
                "sufficient_fuel": True,
                "projected_mass_remaining_kg": round(projected_mass_remaining, 3)
            }
        }

    for burn in maneuver_request.maneuver_sequence:
        scheduled_maneuvers.append({
            "satelliteId": satellite_id,
            "burn_id": burn.burn_id,
            "burnTime": burn.burnTime,
            "deltaV_vector": {
                "x": burn.deltaV_vector.x,
                "y": burn.deltaV_vector.y,
                "z": burn.deltaV_vector.z
            }
        })

    scheduled_maneuvers.sort(key=lambda x: parse_time_z(x["burnTime"]))

    return {
        "accepted": True,
        "reason": None,
        "validation": {
            "ground_station_los": True,
            "sufficient_fuel": True,
            "projected_mass_remaining_kg": round(projected_mass_remaining, 3)
        }
    }


def get_scheduled_maneuvers():
    return scheduled_maneuvers