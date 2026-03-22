from datetime import datetime
from math import sqrt,exp
from scipy.spatial import KDTree

from state_manager import satellites, debris, collision_warnings
from maneuver_manager import scheduled_maneuvers

MU_EARTH = 398600.4418      # km^3 / s^2
R_EARTH = 6378.137          # km
J2 = 1.08263e-3
DRY_MASS_KG = 500.0
ISP_SECONDS = 300.0
G0 = 9.80665

def dv_magnitude_mps(delta_v_vector):
    dv_kms = sqrt(
        delta_v_vector["x"] ** 2 +
        delta_v_vector["y"] ** 2 +
        delta_v_vector["z"] ** 2
    )
    return dv_kms * 1000.0


def propellant_used_kg(current_mass_kg, dv_mps):
    return current_mass_kg * (1.0 - exp(-dv_mps / (ISP_SECONDS * G0)))

def execute_due_maneuvers(current_time_str):
    executed_count = 0
    current_time = datetime.fromisoformat(current_time_str.replace("Z", ""))

    remaining = []

    for maneuver in scheduled_maneuvers:
        burn_time = datetime.fromisoformat(maneuver["burnTime"].replace("Z", ""))

        if burn_time <= current_time:
            sat_id = maneuver["satelliteId"]

            if sat_id in satellites:
                satellites[sat_id]["velocity"][0] += maneuver["deltaV_vector"]["x"]
                satellites[sat_id]["velocity"][1] += maneuver["deltaV_vector"]["y"]
                satellites[sat_id]["velocity"][2] += maneuver["deltaV_vector"]["z"]

                current_fuel_kg = satellites[sat_id].get("fuel_kg", 50.0)
                current_mass_kg = DRY_MASS_KG + current_fuel_kg

                dv_mps = dv_magnitude_mps(maneuver["deltaV_vector"])
                fuel_used = propellant_used_kg(current_mass_kg, dv_mps)

                new_fuel_kg = max(0.0, current_fuel_kg - fuel_used)
                satellites[sat_id]["fuel_kg"] = new_fuel_kg

                executed_count += 1
        else:
            remaining.append(maneuver)

    scheduled_maneuvers.clear()
    scheduled_maneuvers.extend(remaining)

    return executed_count


def acceleration(position):
    x, y, z = position

    r2 = x * x + y * y + z * z
    r = sqrt(r2)

    if r == 0:
        return [0.0, 0.0, 0.0]

    factor_gravity = -MU_EARTH / (r ** 3)
    ax_gravity = factor_gravity * x
    ay_gravity = factor_gravity * y
    az_gravity = factor_gravity * z

    z2 = z * z
    r5 = r ** 5

    j2_factor = 1.5 * J2 * MU_EARTH * (R_EARTH ** 2) / r5
    term = 5.0 * z2 / r2

    ax_j2 = j2_factor * x * (term - 1.0)
    ay_j2 = j2_factor * y * (term - 1.0)
    az_j2 = j2_factor * z * (term - 3.0)

    return [
        ax_gravity + ax_j2,
        ay_gravity + ay_j2,
        az_gravity + az_j2
    ]


def rk4_step(position, velocity, dt):
    k1_r = velocity
    k1_v = acceleration(position)

    p2 = [
        position[0] + 0.5 * dt * k1_r[0],
        position[1] + 0.5 * dt * k1_r[1],
        position[2] + 0.5 * dt * k1_r[2]
    ]
    v2 = [
        velocity[0] + 0.5 * dt * k1_v[0],
        velocity[1] + 0.5 * dt * k1_v[1],
        velocity[2] + 0.5 * dt * k1_v[2]
    ]
    k2_r = v2
    k2_v = acceleration(p2)

    p3 = [
        position[0] + 0.5 * dt * k2_r[0],
        position[1] + 0.5 * dt * k2_r[1],
        position[2] + 0.5 * dt * k2_r[2]
    ]
    v3 = [
        velocity[0] + 0.5 * dt * k2_v[0],
        velocity[1] + 0.5 * dt * k2_v[1],
        velocity[2] + 0.5 * dt * k2_v[2]
    ]
    k3_r = v3
    k3_v = acceleration(p3)

    p4 = [
        position[0] + dt * k3_r[0],
        position[1] + dt * k3_r[1],
        position[2] + dt * k3_r[2]
    ]
    v4 = [
        velocity[0] + dt * k3_v[0],
        velocity[1] + dt * k3_v[1],
        velocity[2] + dt * k3_v[2]
    ]
    k4_r = v4
    k4_v = acceleration(p4)

    new_position = [
        position[0] + (dt / 6.0) * (k1_r[0] + 2.0 * k2_r[0] + 2.0 * k3_r[0] + k4_r[0]),
        position[1] + (dt / 6.0) * (k1_r[1] + 2.0 * k2_r[1] + 2.0 * k3_r[1] + k4_r[1]),
        position[2] + (dt / 6.0) * (k1_r[2] + 2.0 * k2_r[2] + 2.0 * k3_r[2] + k4_r[2])
    ]

    new_velocity = [
        velocity[0] + (dt / 6.0) * (k1_v[0] + 2.0 * k2_v[0] + 2.0 * k3_v[0] + k4_v[0]),
        velocity[1] + (dt / 6.0) * (k1_v[1] + 2.0 * k2_v[1] + 2.0 * k3_v[1] + k4_v[1]),
        velocity[2] + (dt / 6.0) * (k1_v[2] + 2.0 * k2_v[2] + 2.0 * k3_v[2] + k4_v[2])
    ]

    return new_position, new_velocity


def propagate_single_state(position, velocity, total_seconds, substep_seconds=60):
    pos = position[:]
    vel = velocity[:]

    remaining = total_seconds

    while remaining > 0:
        dt = min(substep_seconds, remaining)
        pos, vel = rk4_step(pos, vel, dt)
        remaining -= dt

    return pos, vel


def propagate_objects_rk4(step_seconds, substep_seconds=60):
    for sat_id, sat in satellites.items():
        new_pos, new_vel = propagate_single_state(
            sat["position"],
            sat["velocity"],
            step_seconds,
            substep_seconds
        )
        sat["position"] = new_pos
        sat["velocity"] = new_vel

    for deb_id, deb in debris.items():
        new_pos, new_vel = propagate_single_state(
            deb["position"],
            deb["velocity"],
            step_seconds,
            substep_seconds
        )
        deb["position"] = new_pos
        deb["velocity"] = new_vel


def compute_distance_km(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return sqrt(dx * dx + dy * dy + dz * dz)


def build_forecast_tracks(objects_dict, horizon_seconds=86400, sample_seconds=300, substep_seconds=60):
    tracks = {}

    for obj_id, obj in objects_dict.items():
        pos = obj["position"][:]
        vel = obj["velocity"][:]

        samples = [(0, pos[:], vel[:])]
        elapsed = 0

        while elapsed < horizon_seconds:
            step = min(sample_seconds, horizon_seconds - elapsed)
            pos, vel = propagate_single_state(pos, vel, step, substep_seconds)
            elapsed += step
            samples.append((elapsed, pos[:], vel[:]))

        tracks[obj_id] = samples

    return tracks


def detect_collisions_kdtree(
    threshold_km=0.1,
    horizon_seconds=86400,
    sample_seconds=300,
    substep_seconds=60,
    candidate_radius_km=20.0
):
    collision_warnings.clear()

    if not satellites or not debris:
        return collision_warnings

    sat_tracks = build_forecast_tracks(
        satellites,
        horizon_seconds=horizon_seconds,
        sample_seconds=sample_seconds,
        substep_seconds=substep_seconds
    )

    deb_tracks = build_forecast_tracks(
        debris,
        horizon_seconds=horizon_seconds,
        sample_seconds=sample_seconds,
        substep_seconds=substep_seconds
    )

    debris_ids = list(deb_tracks.keys())

    warning_map = {}

    num_samples = len(next(iter(sat_tracks.values())))

    for sample_idx in range(num_samples):
        debris_positions = [deb_tracks[deb_id][sample_idx][1] for deb_id in debris_ids]
        tree = KDTree(debris_positions)

        sample_time = deb_tracks[debris_ids[0]][sample_idx][0]

        for sat_id, sat_samples in sat_tracks.items():
            sat_pos = sat_samples[sample_idx][1]

            candidate_indices = tree.query_ball_point(sat_pos, candidate_radius_km)

            for idx in candidate_indices:
                deb_id = debris_ids[idx]
                deb_pos = deb_tracks[deb_id][sample_idx][1]

                distance_km = compute_distance_km(sat_pos, deb_pos)

                if distance_km < threshold_km:
                    key = (sat_id, deb_id)

                    if key not in warning_map or distance_km < warning_map[key]["min_distance_km"]:
                        warning_map[key] = {
                            "satellite_id": sat_id,
                            "debris_id": deb_id,
                            "tca_seconds": sample_time,
                            "min_distance_km": distance_km
                        }

    collision_warnings.extend(warning_map.values())
    return collision_warnings