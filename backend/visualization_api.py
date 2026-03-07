from fastapi import APIRouter

router=APIRouter()

@router.get("/api/visualization/snapshot")
def get_snapshot():
    return {
        "timestamp": "2026-03-12T08:00:00.000Z",
        "satellites": [
            {
                "id": "SAT-Alpha-04",
                "lat": 28.545,
                "lon": 77.192,
                "fuel_kg": 48.5,
                "status": "NOMINAL"
            }
        ],
        "debris_cloud": [
            ["DEB-99421", 12.42, -45.21, 400.5],
            ["DEB-99422", 12.55, -45.10, 401.2]
        ]
    }