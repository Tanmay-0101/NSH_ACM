"""
visualization_api.py
--------------------
GET /api/visualization/snapshot

Returns live satellite + debris positions from state_manager.
No more hardcoded data.
"""

from fastapi import APIRouter
import state_manager

router = APIRouter()


@router.get("/api/visualization/snapshot")
def get_snapshot():
    return state_manager.build_snapshot()