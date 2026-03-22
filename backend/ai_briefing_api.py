"""
ai_briefing_api.py
------------------
POST /api/ai/briefing

Calls Anthropic API server-side and returns a plain English
fleet status briefing. Avoids CORS issues with direct browser calls.
"""

from fastapi import APIRouter
import httpx
import state_manager
from autonomous_cola import cola_engine

router = APIRouter()

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
# Paste your API key here — get it from https://console.anthropic.com
ANTHROPIC_API_KEY = "YOUR_API_KEY_HERE"


def build_prompt(snapshot: dict) -> str:
    sats      = snapshot.get("satellites", [])
    debris    = snapshot.get("debris_cloud", [])
    cdms      = snapshot.get("active_cdm_warnings", 0)
    eff       = snapshot.get("efficiency_stats", {})
    ts        = snapshot.get("timestamp", "unknown")

    sat_lines = "\n".join([
        f"- {s['id']}: status={s['status']}, fuel={s.get('fuel_kg',0):.1f}kg "
        f"({s.get('fuel_kg',0)/50*100:.0f}%), lat={s.get('lat',0):.2f}, lon={s.get('lon',0):.2f}"
        for s in sats
    ]) or "No satellites tracked"

    return f"""You are a Flight Dynamics Officer AI at a satellite mission control center.
Analyze this real-time constellation snapshot and give a concise operational briefing.

TIMESTAMP: {ts}
FLEET SIZE: {len(sats)} satellites
DEBRIS TRACKED: {len(debris)} objects
ACTIVE CDM WARNINGS: {cdms}
COLLISIONS AVOIDED: {eff.get('collisions_avoided', 0)}
TOTAL DV SPENT: {eff.get('total_dv_spent_ms', 0)} m/s

SATELLITE STATUS:
{sat_lines}

Write a briefing in 4-6 sentences covering:
1. Overall fleet health
2. Any satellites in DANGER or MANEUVERING and why
3. Fuel situation — who is lowest, any concerns
4. Collisions avoided and efficiency
5. One recommended action, or "All systems nominal" if everything is fine

Be direct and clear. Plain English only. No bullet points."""


@router.post("/api/ai/briefing")
async def get_briefing():
    snapshot = state_manager.build_snapshot()
    prompt   = build_prompt(snapshot)

    if ANTHROPIC_API_KEY == "YOUR_API_KEY_HERE":
        # No API key — return a rule-based briefing instead
        return rule_based_briefing(snapshot)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ANTHROPIC_API,
                headers={
                    "x-api-key":           ANTHROPIC_API_KEY,
                    "anthropic-version":   "2023-06-01",
                    "content-type":        "application/json",
                },
                json={
                    "model":      "claude-sonnet-4-20250514",
                    "max_tokens": 400,
                    "messages":   [{"role": "user", "content": prompt}],
                },
            )
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            return {"briefing": text, "source": "ai"}

    except Exception as e:
        # Fallback to rule-based if API fails
        return rule_based_briefing(snapshot)


def rule_based_briefing(snapshot: dict) -> dict:
    """
    Generates a plain English briefing from rules when
    no API key is available. Always works offline.
    """
    sats   = snapshot.get("satellites", [])
    cdms   = snapshot.get("active_cdm_warnings", 0)
    eff    = snapshot.get("efficiency_stats", {})

    if not sats:
        return {
            "briefing": "No satellites currently tracked. Send telemetry via POST /api/telemetry to initialize the constellation.",
            "source": "rules"
        }

    total        = len(sats)
    nominal      = [s for s in sats if s["status"] == "NOMINAL"]
    danger       = [s for s in sats if s["status"] == "DANGER"]
    maneuvering  = [s for s in sats if s["status"] == "MANEUVERING"]
    graveyard    = [s for s in sats if s["status"] == "GRAVEYARD"]
    low_fuel     = [s for s in sats if s.get("fuel_kg", 50) < 10]
    avoided      = eff.get("collisions_avoided", 0)
    dv_spent     = eff.get("total_dv_spent_ms", 0)

    lines = []

    # Overall health
    if len(nominal) == total:
        lines.append(f"All {total} satellite{'s are' if total > 1 else ' is'} operating nominally with no active threats.")
    else:
        lines.append(f"Fleet of {total} satellites: {len(nominal)} nominal, {len(danger)} in danger, {len(maneuvering)} maneuvering.")

    # Danger satellites
    if danger:
        names = ", ".join(s["id"] for s in danger)
        lines.append(f"{names} {'are' if len(danger) > 1 else 'is'} in DANGER status — active conjunction warning, autonomous evasion burn has been scheduled.")

    # Maneuvering
    if maneuvering:
        names = ", ".join(s["id"] for s in maneuvering)
        lines.append(f"{names} {'are' if len(maneuvering) > 1 else 'is'} MANEUVERING — evasion burn recently executed, thruster in cooldown.")

    # Fuel
    if low_fuel:
        names = ", ".join(f"{s['id']} ({s.get('fuel_kg',0):.1f}kg)" for s in low_fuel)
        lines.append(f"Low fuel alert: {names}. Monitor closely — EOL graveyard burn will trigger at 2.5kg.")
    else:
        min_fuel_sat = min(sats, key=lambda s: s.get("fuel_kg", 50))
        lines.append(f"Fuel levels healthy. Lowest is {min_fuel_sat['id']} at {min_fuel_sat.get('fuel_kg',0):.1f}kg ({min_fuel_sat.get('fuel_kg',0)/50*100:.0f}%).")

    # Efficiency
    if avoided > 0:
        lines.append(f"{avoided} collision{'s' if avoided > 1 else ''} successfully avoided using {dv_spent:.1f} m/s total ΔV — autonomous COLA performing efficiently.")

    # Graveyard
    if graveyard:
        names = ", ".join(s["id"] for s in graveyard)
        lines.append(f"{names} has been decommissioned and moved to graveyard orbit.")

    # Recommendation
    if not danger and not maneuvering and not low_fuel:
        lines.append("No immediate action required — all systems nominal.")
    elif danger:
        lines.append("Recommendation: Monitor conjunction — autonomous system is handling evasion, verify recovery burn is scheduled.")
    elif low_fuel:
        lines.append("Recommendation: Plan deorbit strategy for low-fuel satellites before EOL threshold is reached.")

    return {
        "briefing": " ".join(lines),
        "source": "rules"
    }