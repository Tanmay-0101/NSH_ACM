<!-- # NSH_ACM
An Autonomous Constellation Manager for collision detection and maneuver application -->
# NSH_ACM

### Autonomous Constellation Manager (ACM)

An intelligent backend system designed for the **National Space Hackathon 2026**, focused on **orbital debris avoidance and satellite constellation management**.

---

## Overview

This project implements the foundational backend APIs for an **Autonomous Constellation Manager (ACM)** — a system that monitors satellites and space debris, processes telemetry data, and enables maneuver scheduling for collision avoidance.

The current implementation provides a **robust API skeleton and data handling layer**, which will be extended with physics simulation, collision prediction, and optimization algorithms.

---

## Features Implemented

### 1. Telemetry Ingestion API

* Endpoint: `POST /api/telemetry`
* Accepts real-time orbital data (position & velocity)
* Stores and updates:

  * Satellites
  * Space debris
* Returns processed object count

---

### 2. Maneuver Scheduling API

* Endpoint: `POST /api/maneuver/schedule`
* Accepts maneuver sequences (burn commands)
* Stores scheduled maneuvers for future execution
* Includes placeholder validation:

  * Line-of-sight
  * Fuel sufficiency

---

### 3. Simulation Step API (Skeleton)

* Endpoint: `POST /api/simulate/step`
* Designed to advance simulation time
* Currently returns mock response (to be implemented)

---

### 4. Visualization Snapshot API

* Endpoint: `GET /api/visualization/snapshot`
* Provides structured data for frontend dashboard
* Includes:

  * Satellite positions
  * Fuel status
  * Debris cloud data (compressed format)

---

## Project Structure

```
backend/
│
├── main.py
├── models.py                # Pydantic models (data contracts)
├── telemetry_api.py         # Telemetry ingestion endpoint
├── maneuver_api.py          # Maneuver scheduling endpoint
├── simulation_api.py        # Simulation step endpoint (WIP)
├── visualization_api.py     # Dashboard data endpoint
├── state_manager.py         # In-memory storage for objects
├── maneuver_manager.py      # Maneuver storage logic
├── requirements.txt
```

---

## Data Models

* **Vector3D** → Represents position/velocity
* **ObjectState** → Satellite or debris object
* **TelemetryRequest** → Batch input of objects
* **BurnCommand** → Individual maneuver step
* **ManeuverRequest** → Sequence of burns
* **SimulationStepRequest** → Time step control

---

## Tech Stack

* **Backend Framework:** FastAPI
* **Language:** Python 3
* **Data Validation:** Pydantic
* **Architecture:** Modular API-based design

---

## ▶How to Run

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload
```

Server will run at:

```
http://127.0.0.1:8000
```

---

## API Endpoints

| Method | Endpoint                      | Description                    |
| ------ | ----------------------------- | ------------------------------ |
| POST   | `/api/telemetry`              | Ingest satellite & debris data |
| POST   | `/api/maneuver/schedule`      | Schedule satellite maneuvers   |
| POST   | `/api/simulate/step`          | Advance simulation (WIP)       |
| GET    | `/api/visualization/snapshot` | Get dashboard data             |

---

---

## Contributors

* Tanmay Tyagi
* Shruti

---

