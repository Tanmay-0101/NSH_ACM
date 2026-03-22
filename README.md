# NSH_ACM — Autonomous Constellation Manager
### National Space Hackathon 2026 · IIT Delhi

> **Problem Statement:** Orbital Debris Avoidance & Constellation Management System

---

## What We Built

NSH_ACM is a full-stack **Autonomous Constellation Manager** that monitors a fleet of satellites, detects potential collisions with space debris, and automatically fires thrusters to avoid them — all without any human intervention. The system combines real orbital mechanics, a live mission control dashboard, and a complete REST API that can be stress-tested by the hackathon grader.

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
        ├── hooks.js                    # 1s polling, sim step control
        ├── index.css                   # Dark mission control theme
        ├── index.js
        └── components/
            ├── GroundTrackMap.jsx      # Canvas Mercator map, trails, terminator
            ├── BullseyePlot.jsx        # Polar conjunction proximity chart
            ├── FleetHeatmap.jsx        # Fuel gauges + ΔV efficiency graph
            ├── ManeuverGantt.jsx       # Burn/cooldown timeline
            ├── StatusBar.jsx           # Uplink, sim time, step controls
            └── TelemetryFeed.jsx       # Live status log
```

---

## Core Features

### 1. Physics Engine (`physics_engine.py`)
Implements real orbital mechanics as specified in the problem statement:
- **RK4 4th-order integrator** with 10-second sub-steps for numerical accuracy
- **J2 perturbation** — accounts for Earth's equatorial bulge causing nodal regression and apsidal precession. Uses exact formula from PS: `a_J2 = (3/2) × J2 × μ × RE² / |r|⁵ × [x(5z²/r²-1), y(5z²/r²-1), z(5z²/r²-3)]`
- **Tsiolkovsky rocket equation** — `Δm = m × (1 - e^(-|ΔV| / Isp×g₀))` with `Isp=300s`, `g₀=9.80665 m/s²`
- **RTN ↔ ECI rotation matrix** — maneuvers planned in local Radial-Transverse-Normal frame, converted to ECI before execution
- **ECI → geodetic** with Greenwich Sidereal Time for accurate lat/lon display

### 2. Collision Detection (`collision_detector.py`)
- **KD-tree spatial indexing** (scipy) — O(N log N) instead of O(N²) brute force
- Coarse 50km pre-filter, then exact Euclidean distance check on candidates
- Conjunction threshold: **100m** per PS spec
- Risk levels: SAFE / WARNING (<5km) / CRITICAL (<1km) / COLLISION (<100m)
- **24-hour predictive assessment** — propagates all objects forward at 5-min intervals to flag future conjunctions

### 3. Autonomous COLA Engine (`autonomous_cola.py`)
The heart of the system — makes it truly autonomous:
- **Auto-detects** any CDM at WARNING/CRITICAL/COLLISION level on every simulation tick
- **Auto-schedules evasion burn** — prograde RTN burn (most fuel-efficient) converted to ECI, scheduled immediately after signal latency (10s) + cooldown
- **Auto-pairs recovery burn** — retrograde burn scheduled ~90 minutes after evasion to return satellite to its nominal slot
- **Station-keeping monitoring** — tracks each satellite's 10km bounding box, logs outage seconds when drift exceeds threshold
- **EOL management** — satellites at ≤5% fuel automatically get a graveyard raise burn
- **Efficiency tracking** — logs total ΔV spent and conjunctions avoided for UI graph

### 4. Maneuver System
- **Heap priority queue** (`maneuver_manager.py`) — burns sorted by time, executed automatically on each simulation tick
- **Full validation chain** (`maneuver_engine.py`):
  - Signal latency: min 10s ahead of current sim time
  - ΔV cap: 15 m/s per burn
  - Fuel budget: Tsiolkovsky pre-check
  - Thruster cooldown: 600s between burns on same satellite
  - Ground station LOS check
- Both manual (via API) and autonomous (via COLA) burns flow through same queue

### 5. Ground Station Network (`ground_station.py`)
All 6 stations from PS spec with exact coordinates and elevation masks:

| Station | Lat | Lon | Min Elevation |
|---------|-----|-----|---------------|
| ISTRAC Bengaluru | 13.03° | 77.52° | 5° |
| Svalbard | 78.23° | 15.41° | 5° |
| Goldstone | 35.43° | -116.89° | 10° |
| Punta Arenas | -53.15° | -70.92° | 5° |
| IIT Delhi | 28.55° | 77.19° | 15° |
| McMurdo | -77.85° | 166.67° | 5° |

---

## The 10-Step Simulation Pipeline

Every call to `POST /api/simulate/step` runs this full pipeline:

```
1.  Register nominal slots (before propagation — captures initial position)
2.  Execute due burns from priority queue
3.  Propagate ALL objects with RK4 + J2
4.  Detect collisions on new positions (KD-tree)
5.  Set satellite status: DANGER if CDM detected, NOMINAL if threat cleared
6.  Run Autonomous COLA — auto-schedule evasion + recovery for any CDM
7.  Update station-keeping — log outage if satellite drifts >10km
8.  24hr predictive scan (every 10 ticks)
9.  Auto-schedule future evasion burns for predicted conjunctions
10. Advance simulation clock
```

---

## Satellite Status Lifecycle

```
NOMINAL ──► DANGER ──► MANEUVERING ──► NOMINAL
   │           │              │
Default    CDM detected   Burn fired,
           debris <5km    cooldown active
           (turns red     (turns amber
            on map)        on map)
```

| Status | Meaning | Map Color |
|--------|---------|-----------|
| `NOMINAL` | Healthy, in slot, no threats | 🟢 Green diamond |
| `DANGER` | Active CDM warning — debris within 5km | 🔴 Red diamond + pulsing ring |
| `MANEUVERING` | Burn recently executed, cooldown active | 🟡 Amber diamond |
| `LOW_FUEL` | Fuel below 20% | 🟡 Amber diamond |
| `CRITICAL` | Fuel below 5% — EOL imminent | 🔴 Red diamond |
| `GRAVEYARD` | Decommissioned, graveyard burn fired | ⚫ Gray diamond |

---

## Orbital Insight Dashboard

Built in React with Canvas 2D API — handles 50+ satellites and 10,000+ debris at 60fps.

**4 Required Modules (all implemented):**

**Ground Track Map** — Mercator projection with:
- Real-time satellite positions (diamond markers, color by status)
- Historical trail (last 90 minutes of orbit)
- Dashed predicted trajectory (next 90 minutes, yellow)
- Terminator line (day/night boundary shadow)
- Debris cloud (orange dots, batched Canvas rendering)
- Ground stations (white crosshair circle markers ⊕)

**Conjunction Bullseye** — Polar chart showing debris approach vectors relative to selected satellite. Color-coded rings: green (safe) / yellow (<5km) / red (<1km).

**Fleet Heatmap** — Per-satellite fuel bars sorted by lowest fuel first. Includes live ΔV cost vs collisions avoided efficiency graph.

**Maneuver Gantt** — Chronological burn timeline with BURN and COOLDOWN blocks. Filterable by EVASION / RECOVERY / EOL.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/telemetry` | Ingest ECI state vectors, returns CDM count |
| `POST` | `/api/maneuver/schedule` | Validate and queue manual burn sequence |
| `POST` | `/api/simulate/step` | Run full autonomous pipeline for N seconds |
| `GET`  | `/api/visualization/snapshot` | Live lat/lon snapshot for dashboard |

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

**1. Send a satellite on collision course with debris (50m apart):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/telemetry" -Method POST -ContentType "application/json" -Body '{"timestamp":"2026-03-22T10:00:00Z","objects":[{"id":"SAT-Alpha-01","type":"SATELLITE","r":{"x":6778.0,"y":0.0,"z":0.0},"v":{"x":0.0,"y":7.67,"z":0.0}},{"id":"DEB-001","type":"DEBRIS","r":{"x":6778.05,"y":0.0,"z":0.0},"v":{"x":0.01,"y":7.66,"z":0.01}}]}'
```

**2. Run one simulation tick — COLA fires automatically:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":60}'
```
Expected: `"auto_burns_scheduled": 2` — evasion + recovery scheduled with zero human input.
Dashboard: satellite diamond turns **red with pulsing ring**.

**3. Advance past burn time:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":3600}'
```
Expected: `"maneuvers_executed": 1`, fuel drops from 50kg → ~48.5kg, diamond turns amber.

**4. Advance past recovery burn:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" -Method POST -ContentType "application/json" -Body '{"step_seconds":7200}'
```
Expected: `"maneuvers_executed": 1` again, satellite returns to NOMINAL (green).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Physics | NumPy, SciPy (KDTree) |
| Frontend | React 18, Canvas 2D API |
| Fonts | Rajdhani, Share Tech Mono, Exo 2 |
| Container | Docker (ubuntu:22.04) |

---

## Evaluation Criteria Coverage

| Criteria | Weight | How We Address It |
|----------|--------|-------------------|
| **Safety Score** | 25% | KD-tree CDM detection + `autonomous_cola.py` auto-schedules evasion burns on every tick. Proven zero collisions in test case. |
| **Fuel Efficiency** | 20% | Tsiolkovsky equation tracks exact fuel per burn. Prograde-first RTN strategy minimizes ΔV. Recovery burn paired at 0.95× evasion magnitude. |
| **Constellation Uptime** | 15% | 10km station-keeping box monitored every tick. Outage seconds logged. Recovery burns return satellite to nominal slot. |
| **Algorithmic Speed** | 15% | KD-tree O(N log N) spatial index. Vectorised RK4 via NumPy. 24hr prediction runs every 10 ticks to avoid CPU overhead. |
| **UI/UX & Visualization** | 15% | All 4 PS-required modules implemented. Canvas 2D handles 10k+ debris at 60fps. Status-driven color coding with pulsing danger alerts. |
| **Code Quality** | 10% | Modular single-responsibility files. Typed function signatures. Structured logging throughout. Clear docstrings on all public functions. |

---

## Contributors

- **Tanmay Tyagi**
- **Shruti**