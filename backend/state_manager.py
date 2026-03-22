from datetime import datetime, timedelta

satellites = {}
debris = {}
collision_warnings = []

current_timestamp = "2026-03-12T08:00:00.000Z"

def update_objects(objects):
    processed = 0

    for obj in objects:
        state = {
            "id": obj.id,
            "position": [obj.r.x, obj.r.y, obj.r.z],
            "velocity": [obj.v.x, obj.v.y, obj.v.z],
            "type": obj.type
        }

        if obj.type == "SATELLITE":
            if obj.id in satellites:
                fuel_kg = satellites[obj.id].get("fuel_kg", 50.0)
            else:
                fuel_kg = 50.0

            state["fuel_kg"] = fuel_kg
            satellites[obj.id] = state
        else:
            debris[obj.id] = state

        processed += 1

    return processed


def advance_simulation_time(step_seconds):
    global current_timestamp

    current_time = datetime.fromisoformat(current_timestamp.replace("Z", ""))
    new_time = current_time + timedelta(seconds=step_seconds)
    current_timestamp = new_time.isoformat() + "Z"

    return current_timestamp


def get_current_timestamp():
    return current_timestamp