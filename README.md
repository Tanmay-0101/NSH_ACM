# NSH_ACM — Autonomous Constellation Manager

> **National Space Hackathon 2026** · Hosted by IIT Delhi
> Problem Statement: Orbital Debris Avoidance & Constellation Management System

---

## Overview

**NSH_ACM** is a full-stack Autonomous Constellation Manager (ACM) built for the National Space Hackathon 2026. It ingests high-frequency orbital telemetry, propagates satellite and debris trajectories using real orbital mechanics (RK4 + J2), detects conjunctions using spatial indexing, autonomously schedules collision avoidance maneuvers, and provides a live mission control dashboard — **Orbital Insight**.

---

## Project Structure

```
NSH_ACM/
│
├── Dockerfile                         # Ubuntu 22.04, exposes port 8000
├── README.md
├── .gitignore
│
├── backend/
│   ├── main.py                        # FastAPI app entry point, router registration
│   ├── models.py                      # Pydantic request/response models
│   ├── state_manager.py               # In-memory ECI state store + ECI→geodetic
│   ├── physics_engine.py              # RK4 + J2 propagator, RTN↔ECI, Tsiolkovsky
│   ├── collision_detector.py          # KD-tree spatial indexing, CDM generation
│   ├── maneuver_engine.py             # ΔV application, fuel depletion, cooldown
│   ├── maneuver_manager.py            # Heap priority queue of scheduled burns
│   ├── ground_station.py              # LOS check, elevation mask, blackout zones
│   ├── telemetry_api.py               # POST /api/telemetry
│   ├── maneuver_api.py                # POST /api/maneuver/schedule
│   ├── simulation_api.py              # POST /api/simulate/step
│   ├── visualization_api.py           # GET  /api/visualization/snapshot
│   └── requirements.txt
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.jsx                    # 3-column mission control grid layout
        ├── ErrorBoundary.jsx          # React error boundary with debug display
        ├── hooks.js                   # useSnapshot (1s polling), useSimControl
        ├── index.css                  # Global dark theme — mission control aesthetic
        ├── index.js                   # React entry point
        └── components/
            ├── GroundTrackMap.jsx     # Canvas 2D Mercator, 10k+ debris @ 60fps
            ├── BullseyePlot.jsx       # Polar conjunction proximity chart
            ├── FleetHeatmap.jsx       # Per-satellite fuel gauges + fleet stats
            ├── ManeuverGantt.jsx      # Burn/cooldown timeline, filter by type
            ├── StatusBar.jsx          # Uplink status, sim time, step controls
            └── TelemetryFeed.jsx      # Live satellite log with CDM banners
```

---

## Features

### Physics Engine (`physics_engine.py`)
- **RK4 4th-order integrator** with 10s sub-steps for high accuracy
- **J2 perturbation** — Earth's equatorial bulge (nodal regression, apsidal precession)
- **Impulsive burn model** — `apply_delta_v_eci()` adds ΔV instantaneously to velocity
- **Tsiolkovsky rocket equation** — `Δm = m × (1 - e^(-|ΔV| / Isp·g₀))`
- **RTN ↔ ECI rotation matrix** — maneuvers planned in local frame, executed in ECI
- **ECI → geodetic** with Greenwich Sidereal Time for accurate lat/lon on map

### Collision Detection (`collision_detector.py`)
- **KD-tree spatial indexing** (scipy) — O(N log N) vs brute-force O(N²)
- Conjunction threshold: **100 m** per problem statement
- CDM warning count returned on every telemetry ACK response

### Maneuver System
- **Heap-based priority queue** (`maneuver_manager.py`) sorted by burn time
- **Full validation chain** (`maneuver_engine.py`):
  - Signal latency enforcement (min 10s ahead)
  - ΔV cap: 15 m/s per burn
  - Fuel budget check (Tsiolkovsky pre-calculation)
  - Thruster cooldown: 600s between burns
  - Ground station LOS verification
- **EOL detection** at 5% fuel → graveyard orbit flag

### Ground Station Network (`ground_station.py`)
- 6 stations per PS spec: ISTRAC Bengaluru, Svalbard, Goldstone, Punta Arenas, IIT Delhi, McMurdo
- Geometric LOS with elevation mask angle and Earth curvature

### Orbital Insight Dashboard (React)
- **Ground Track Map** — Mercator, satellite trails, terminator line, debris cloud, ground stations
- **Conjunction Bullseye** — polar chart, debris color-coded by miss distance (green/yellow/red)
- **Fleet Heatmap** — real-time fuel bars sorted by lowest fuel first, fleet-wide stats
- **Maneuver Gantt** — burn + cooldown blocks, filterable by EVASION / RECOVERY / EOL
- **Telemetry Log** — live status feed, CDM warning banners
- Auto-polls `/api/visualization/snapshot` every second

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/telemetry` | Ingest satellite & debris ECI state vectors |
| `POST` | `/api/maneuver/schedule` | Validate and queue a burn sequence |
| `POST` | `/api/simulate/step` | Advance sim with RK4+J2 propagation |
| `GET`  | `/api/visualization/snapshot` | Live snapshot for dashboard polling |

Full interactive docs available at `http://localhost:8000/docs`

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
Dashboard opens at `http://localhost:3000`

### Docker (required for submission)
```bash
docker build -t nsh-acm .
docker run -p 8000:8000 nsh-acm
```

---

## End-to-End Test (PowerShell)

**1. Ingest telemetry:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/telemetry" `
  -Method POST -ContentType "application/json" `
  -Body '{"timestamp":"2026-03-22T10:00:00Z","objects":[{"id":"SAT-Alpha-01","type":"SATELLITE","r":{"x":6778,"y":0,"z":0},"v":{"x":0,"y":7.67,"z":0}},{"id":"DEB-001","type":"DEBRIS","r":{"x":6800,"y":100,"z":50},"v":{"x":0.1,"y":7.5,"z":0.2}}]}'
```

**2. Propagate 1 orbit (~90 min):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" `
  -Method POST -ContentType "application/json" `
  -Body '{"step_seconds": 5400}'
```

**3. Schedule a maneuver:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/maneuver/schedule" `
  -Method POST -ContentType "application/json" `
  -Body '{"satelliteId":"SAT-Alpha-01","maneuver_sequence":[{"burn_id":"EVASION_1","burnTime":"2026-03-22T11:30:00Z","deltaV_vector":{"x":0.002,"y":0.010,"z":-0.001}}]}'
```

**4. Advance past burn time — watch fuel drop:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/step" `
  -Method POST -ContentType "application/json" `
  -Body '{"step_seconds": 7200}'
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Physics | NumPy, SciPy (KD-tree) |
| Frontend | React 18, Canvas 2D API |
| Fonts | Rajdhani, Share Tech Mono, Exo 2 |
| Container | Docker (ubuntu:22.04) |

---

## Evaluation Criteria

| Criteria | Weight | Our Implementation |
|----------|--------|--------------------|
| Safety Score | 25% | KD-tree CDM detection + autonomous evasion burns |
| Fuel Efficiency | 20% | Tsiolkovsky equation, prograde-first RTN strategy |
| Constellation Uptime | 15% | Station-keeping check, recovery burn pairing |
| Algorithmic Speed | 15% | O(N log N) KD-tree, vectorised RK4 sub-steps |
| UI/UX & Visualization | 15% | 60fps Canvas dashboard, all 4 required PS modules |
| Code Quality | 10% | Modular architecture, typed functions, docstrings |

---

## Contributors

- **Tanmay Tyagi**
- **Shruti**