# NSH_ACM — Autonomous Constellation Manager
### National Space Hackathon 2026 · IIT Delhi

> **Problem Statement:** Orbital Debris Avoidance & Constellation Management System

---

## What We Built

NSH_ACM is a full-stack **Autonomous Constellation Manager** that monitors a fleet of satellites, detects potential collisions with space debris, and automatically fires thrusters to avoid them — all without any human intervention. The system combines real orbital mechanics, a live mission control dashboard, an AI-powered fleet briefing engine, and a complete REST API that can be stress-tested by the hackathon grader.

The key differentiator is the **Autonomous COLA Engine** (`autonomous_cola.py`) — when the system detects a conjunction under 100m, it automatically calculates, schedules, and executes both the evasion burn and the paired recovery burn without a single manual API call.

---

## Project Structure

```
NSH_ACM/
├── Dockerfile                          # Ubuntu 22.04, port 8000
├── README.md
├── backend/
│   ├── main.py                         # FastAPI app, router registration
│   ├── models.py                       # Pydantic request/response models
│   ├── state_manager.py                # In-memory ECI store, ECI→geodetic, fuel tracking
│   ├── physics_engine.py               # RK4 + J2 propagator, Tsiolkovsky, RTN↔ECI
│   ├── collision_detector.py           # KD-tree O(N log N) conjunction assessment
│   ├── autonomous_cola.py              # Autonomous evasion, recovery, EOL management
│   ├── maneuver_engine.py              # ΔV application, cooldown enforcement
│   ├── maneuver_manager.py             # Heap priority queue of scheduled burns
│   ├── ground_station.py               # LOS check, elevation mask, 6 stations
│   ├── ai_briefing_api.py              # POST /api/ai/briefing — AI fleet summary
│   ├── telemetry_api.py                # POST /api/telemetry
│   ├── maneuver_api.py                 # POST /api/maneuver/schedule
│   ├── simulation_api.py               # POST /api/simulate/step (full pipeline)
│   ├── visualization_api.py            # GET  /api/visualization/snapshot
│   └── requirements.txt
└── frontend/
    ├── public/index.html
    └── src/
        ├── App.jsx                     # 3-column mission control layout
        ├── ErrorBoundary.jsx
        ├── hooks.js                    # 1s polling, sim step control, maneuver history
        ├── index.css                   # Dark mission control theme
        ├── index.js
        └── components/
            ├── GroundTrackMap.jsx      # Canvas Mercator map, trails, terminator, predicted trajectory
            ├── BullseyePlot.jsx        # Polar conjunction proximity chart
            ├── FleetHeatmap.jsx        # Fuel gauges + ΔV efficiency graph
            ├── ManeuverGantt.jsx       # Burn/cooldown timeline with AUTO badges
            ├── StatusBar.jsx           # Uplink, sim time, step controls, AI briefing button
            ├── TelemetryFeed.jsx       # Live status log
            └── AIBriefing.jsx          # AI-powered fleet status summarizer
```

---

## Core Features

### 1. Physics Engine (`physics_engine.py`)
Implements real orbital mechanics as specified in the problem statement:
- **RK4 4th-order integrator** with 10-second sub-steps for numerical accuracy
- **J2 perturbation** — Earth's equatorial bulge. Exact formula: `a_J2 = (3/2) × J2 × μ × RE² / |r|⁵ × [x(5z²/r²-1), y(5z²/r²-1), z(5z²/r²-3)]`
- **Tsiolkovsky rocket equation** — `Δm = m × (1 - e^(-|ΔV| / Isp×g₀))` with `Isp=300s`, `g₀=9.80665 m/s²`
- **RTN ↔ ECI rotation matrix** — maneuvers planned in local frame, converted to ECI before execution
- **ECI → geodetic** with Greenwich Sidereal Time for accurate lat/lon on map

### 2. Collision Detection (`collision_detector.py`)
- **KD-tree spatial indexing** (scipy) — O(N log N) instead of O(N²) brute force
- Coarse 50km pre-filter, then exact Euclidean distance on candidates
- Conjunction threshold: **100m** per PS spec
- Risk levels: SAFE / WARNING (<5km) / CRITICAL (<1km) / COLLISION (<100m)
- **24-hour predictive assessment** — propagates all objects forward at 5-min intervals

### 3. Autonomous COLA Engine (`autonomous_cola.py`)
The heart of the system — makes it truly autonomous:
- **Auto-detects** any CDM at WARNING/CRITICAL/COLLISION level on every tick
- **Auto-schedules evasion burn** — prograde RTN burn, scheduled immediately after signal latency + cooldown
- **Auto-pairs recovery burn** — retrograde burn ~90 minutes later to return satellite to nominal slot
- **Station-keeping monitoring** — tracks 10km bounding box, logs outage seconds
- **EOL management** — satellites at ≤5% fuel get automatic graveyard raise burn
- **Efficiency tracking** — total ΔV spent and conjunctions avoided logged for UI graph

### 4. Maneuver System
- **Heap priority queue** (`maneuver_manager.py`) — burns sorted by simulation time, executed automatically
- **Full validation chain**: signal latency (10s), ΔV cap (15 m/s), fuel budget, thruster cooldown (600s), ground station LOS
- Uses **simulation clock** (not real UTC) for consistent timing across all operations
- Both manual (via API) and autonomous (via COLA) burns flow through the same queue

### 5. Ground Station Network (`ground_station.py`)
All 6 stations from PS spec:

| Station | Lat | Lon | Min Elevation |
|---------|-----|-----|---------------|
| ISTRAC Bengaluru | 13.03° | 77.52° | 5° |
| Svalbard | 78.23° | 15.41° | 5° |
| Goldstone | 35.43° | -116.89° | 10° |
| Punta Arenas | -53.15° | -70.92° | 5° |
| IIT Delhi | 28.55° | 77.19° | 15° |
| McMurdo | -77.85° | 166.67° | 5° |

### 6. AI Fleet Briefing (`ai_briefing_api.py` + `AIBriefing.jsx`)
When managing 50+ satellites, reading individual telemetry becomes impractical. The **⚡ AI Briefing** button in the top bar generates an instant plain-English summary of the entire constellation:
- Calls `POST /api/ai/briefing` on the backend
- Backend reads live snapshot (all satellites, fuel, CDM warnings, efficiency stats)
- Generates a 4-6 sentence operational briefing like a Flight Dynamics Officer would speak
- **Rule-based fallback** works without any API key — always produces a meaningful briefing
- **Claude AI mode** available when API key is configured in `ai_briefing_api.py`
- Button turns **red** when active CDM warnings exist, **amber** during maneuvering, **cyan** when nominal
- Briefing panel shows quick stat pills (sats, danger count, CDMs, low fuel) at a glance

---

## The 10-Step Simulation Pipeline

Every call to `POST /api/simulate/step` runs:

```
1.  Register nominal slots (before propagation)
2.  Execute due burns from priority queue
3.  Propagate ALL objects with RK4 + J2
4.  Detect collisions (KD-tree)
5.  Set satellite status: DANGER if CDM, NOMINAL if threat cleared
6.  Run Autonomous COLA — auto-schedule evasion + recovery
7.  Update station-keeping — log outage if drift >10km
8.  24hr predictive scan (every 10 ticks)
9.  Auto-schedule future burns for predicted conjunctions
10. Advance simulation clock
```

---

## Satellite Status Lifecycle

```
NOMINAL ──► DANGER ──► MANEUVERING ──► NOMINAL
   │           │              │
Default    CDM detected   Burn fired,
           debris <5km    cooldown active
```

| Status | Meaning | Map Color |
|--------|---------|-----------|
| `NOMINAL` | Healthy, in slot, no threats | 🟢 Green diamond |
| `DANGER` | Active CDM — debris within 5km | 🔴 Red + pulsing ring |
| `MANEUVERING` | Burn recently executed, cooldown active | 🟡 Amber diamond |
| `LOW_FUEL` | Fuel below 20% | 🟡 Amber diamond |
| `CRITICAL` | Fuel below 5% — EOL imminent | 🔴 Red diamond |
| `GRAVEYARD` | Decommissioned | ⚫ Gray diamond |

---

## Orbital Insight Dashboard

Built in React with Canvas 2D API — handles 50+ satellites and 10,000+ debris at 60fps.

**4 Required Modules (all implemented):**

**Ground Track Map** — Mercator projection with real-time satellite diamonds (color by status), historical 90-min trail, dashed yellow predicted trajectory (next 90 min), terminator shadow, orange debris dots, white crosshair ground station markers ⊕.

**Conjunction Bullseye** — Polar chart showing debris approach vectors relative to selected satellite. Color-coded rings: green (safe) / yellow (<5km) / red (<1km).

**Fleet Heatmap** — Per-satellite fuel bars sorted lowest first. Live ΔV cost vs collisions avoided efficiency graph.

**Maneuver Gantt** — Burn + cooldown timeline, filterable by EVASION / RECOVERY / EOL. AUTO badge marks autonomous burns. Shows fuel remaining after each burn.

**AI Fleet Briefing** — One-click English summary of entire constellation health. Accessible from top bar.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/telemetry` | Ingest ECI state vectors, returns CDM count |
| `POST` | `/api/maneuver/schedule` | Validate and queue manual burn sequence |
| `POST` | `/api/simulate/step` | Run full autonomous pipeline for N seconds |
| `GET`  | `/api/visualization/snapshot` | Live lat/lon snapshot for dashboard |
| `POST` | `/api/ai/briefing` | Generate AI plain-English fleet status summary |

Full interactive docs: `http://localhost:8000/docs`

---

## How to Run

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```
Dashboard: `http://localhost:3000`

### Docker
```bash
docker build -t nsh-acm .
docker run -p 8000:8000 nsh-acm
```

---

## Proving Autonomous Avoidance (Test Case)

**1. Restart uvicorn** to reset sim clock to `2026-03-22T10:00:00Z`.

**2. Send collision course telemetry:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/telemetry" -Method POST -ContentType "application/json" -Body '{"timestamp":"2026-03-22T10:00:00Z","objects":[{"id":"SAT-Alpha-01","type":"SATELLITE","r":{"x":6778.0,"y":0.0,"z":0.0},"v":{"x":0.0,"y":7.67,"z":0.0}},{"id":"DEB-001","type":"DEBRIS","r":{"x":6778.05,"y":0.0,"z":0.0},"v":{"x":0.01,"y":7.66,"z":0.01}}]}'
```

**3. First tick — COLA fires automatically:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":60}'
```
✅ `"auto_burns_scheduled": 2` — evasion + recovery queued with zero human input. Diamond turns **red**.

**4. Advance past evasion burn:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":3600}'
```
✅ `"maneuvers_executed": 1`, fuel 50kg → 48.5kg, diamond turns **amber**.

**5. Advance past recovery burn:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":7200}'
```
✅ `"maneuvers_executed": 1` again, satellite returns to **green** NOMINAL.

**6. Click ⚡ AI Briefing** — get plain English summary of the entire sequence.

---

## Manual Maneuver Scheduling (Important Note)

All `burnTime` values must be **ahead of the current simulation clock** (shown as `SIM-T` in the dashboard), not real UTC time. The system uses a single consistent simulation clock for all operations.

Example — if `SIM-T` shows `2026-03-22T10:00:00`:
```json
{
  "satelliteId": "SAT-DELHI",
  "maneuver_sequence": [{
    "burn_id": "BURN-1",
    "burnTime": "2026-03-22T10:20:00.000Z",
    "deltaV_vector": {"x": 0.0, "y": 0.005, "z": 0.0}
  }]
}
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn, httpx |
| Physics | NumPy, SciPy (KDTree) |
| AI | Anthropic Claude API (rule-based fallback included) |
| Frontend | React 18, Canvas 2D API |
| Fonts | Rajdhani, Share Tech Mono, Exo 2 |
| Container | Docker (ubuntu:22.04) |

---

## Evaluation Criteria Coverage

| Criteria | Weight | How We Address It |
|----------|--------|-------------------|
| **Safety Score** | 25% | KD-tree CDM detection + autonomous COLA auto-schedules evasion burns every tick. Zero collisions in test case. |
| **Fuel Efficiency** | 20% | Tsiolkovsky equation per burn. Prograde-first RTN strategy. Recovery burn at 0.95× evasion ΔV. |
| **Constellation Uptime** | 15% | 10km station-keeping box every tick. Outage seconds logged. Recovery burns return satellite to slot. |
| **Algorithmic Speed** | 15% | O(N log N) KD-tree. Vectorised RK4 via NumPy. 24hr prediction every 10 ticks only. |
| **UI/UX & Visualization** | 15% | All 4 PS modules. 60fps Canvas. Status color coding + pulsing danger alerts. AI briefing for fleet overview. |
| **Code Quality** | 10% | Single-responsibility modules. Typed functions. Structured logging. Clear docstrings. |

---

## Contributors

- **Tanmay Tyagi**
- **Shruti**