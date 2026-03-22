import React, { useEffect, useRef } from 'react';

const WORLD_W = 800;
const WORLD_H = 400;

function latlonToXY(lat, lon, w, h) {
  const x = ((lon + 180) / 360) * w;
  const y = ((90 - lat) / 180) * h;
  return [x, y];
}

function getSolarDeclination() {
  const now = new Date();
  const dayOfYear = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
  return -23.45 * Math.cos((2 * Math.PI / 365) * (dayOfYear + 10));
}

// Simple ground track predictor — advance lat/lon along orbit
// Uses approximate orbital period for LEO (~92 min) 
function predictGroundTrack(lat, lon, steps = 30, stepMinutes = 3) {
  const points = [];
  const EARTH_ROT_DEG_PER_MIN = 0.25; // Earth rotates ~0.25°/min
  const ORBIT_INC_DEG = 51.6; // approximate ISS-like inclination
  
  let curLat = lat;
  let curLon = lon;
  
  for (let i = 0; i < steps; i++) {
    // Approximate: move along great circle, account for Earth rotation
    curLon = ((curLon - EARTH_ROT_DEG_PER_MIN * stepMinutes + 180) % 360) - 180;
    // Simple sinusoidal lat oscillation based on inclination
    const t = (i * stepMinutes) / (92); // fraction of orbital period
    curLat = ORBIT_INC_DEG * Math.sin(2 * Math.PI * t + Math.asin(lat / ORBIT_INC_DEG || 0));
    curLat = Math.max(-90, Math.min(90, curLat));
    points.push([curLat, curLon]);
  }
  return points;
}

export default function GroundTrackMap({ satellites = [], debrisCloud = [], selectedSat, onSelectSat }) {
  const canvasRef = useRef(null);
  const animRef   = useRef(null);
  const trailsRef = useRef({});

  useEffect(() => {
    satellites.forEach(sat => {
      if (!trailsRef.current[sat.id]) trailsRef.current[sat.id] = [];
      const trail = trailsRef.current[sat.id];
      trail.push([sat.lat, sat.lon]);
      if (trail.length > 90) trail.shift();
    });
  }, [satellites]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;

    function draw() {
      ctx.clearRect(0, 0, W, H);

      // Ocean background
      ctx.fillStyle = '#020d1a';
      ctx.fillRect(0, 0, W, H);

      // Grid lines
      ctx.strokeStyle = 'rgba(0,200,255,0.05)';
      ctx.lineWidth = 0.5;
      for (let lon = -180; lon <= 180; lon += 30) {
        const [x] = latlonToXY(0, lon, W, H);
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
      for (let lat = -90; lat <= 90; lat += 30) {
        const [, y] = latlonToXY(lat, 0, W, H);
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }

      // Equator & Prime Meridian
      ctx.strokeStyle = 'rgba(0,200,255,0.15)';
      ctx.lineWidth = 1;
      const [, eqY] = latlonToXY(0, 0, W, H);
      ctx.beginPath(); ctx.moveTo(0, eqY); ctx.lineTo(W, eqY); ctx.stroke();
      const [pmX] = latlonToXY(0, 0, W, H);
      ctx.beginPath(); ctx.moveTo(pmX, 0); ctx.lineTo(pmX, H); ctx.stroke();

      // Terminator shadow
      const now = new Date();
      const termX = ((now.getUTCHours() * 60 + now.getUTCMinutes()) / 1440) * W;
      const shadowX = (termX + W / 2) % W;
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      if (shadowX + W / 2 > W) {
        ctx.fillRect(shadowX - W / 2, 0, W, H);
      } else {
        ctx.fillRect(shadowX, 0, W / 2, H);
      }

      // Ground stations
      const groundStations = [
        { name: 'ISTRAC',     lat: 13.03,   lon: 77.52   },
        { name: 'Svalbard',   lat: 78.23,   lon: 15.41   },
        { name: 'Goldstone',  lat: 35.43,   lon: -116.89 },
        { name: 'Punta',      lat: -53.15,  lon: -70.92  },
        { name: 'IIT Delhi',  lat: 28.55,   lon: 77.19   },
        { name: 'McMurdo',    lat: -77.85,  lon: 166.67  },
      ];
      groundStations.forEach(gs => {
        const [x, y] = latlonToXY(gs.lat, gs.lon, W, H);
        // Outer ring — white/dim
        ctx.strokeStyle = 'rgba(180,180,180,0.5)';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.stroke();
        // Inner filled circle — white
        ctx.fillStyle = 'rgba(200,200,200,0.25)';
        ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.fill();
        // Center dot
        ctx.fillStyle = 'rgba(220,220,220,0.9)';
        ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
        // Cross inside circle
        ctx.strokeStyle = 'rgba(220,220,220,0.7)';
        ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.moveTo(x - 4, y); ctx.lineTo(x + 4, y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x, y - 4); ctx.lineTo(x, y + 4); ctx.stroke();
        // Label — small and dim
        ctx.fillStyle = 'rgba(180,180,180,0.6)';
        ctx.font = '7px Share Tech Mono, monospace';
        ctx.fillText(gs.name, x + 9, y + 3);
      });

      // Debris cloud — bright orange circles, visible at map scale
      debrisCloud.forEach(([id, lat, lon]) => {
        const [x, y] = latlonToXY(lat, lon, W, H);
        // Glow effect
        ctx.fillStyle = 'rgba(255,80,20,0.25)';
        ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
        // Core dot
        ctx.fillStyle = 'rgba(255,120,40,0.95)';
        ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
      });

      // Historical trails (last 90 min)
      Object.entries(trailsRef.current).forEach(([satId, trail]) => {
        if (trail.length < 2) return;
        const isSel = satId === selectedSat;
        ctx.strokeStyle = isSel ? 'rgba(0,200,255,0.6)' : 'rgba(0,200,255,0.2)';
        ctx.lineWidth = isSel ? 1.5 : 0.8;
        ctx.setLineDash([]);
        ctx.beginPath();
        trail.forEach(([lat, lon], i) => {
          const [x, y] = latlonToXY(lat, lon, W, H);
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
      });

      // Predicted trajectory (dashed, next 90 min)
      satellites.forEach(sat => {
        const predicted = predictGroundTrack(sat.lat, sat.lon, 30, 3);
        if (predicted.length < 2) return;
        const isSel = sat.id === selectedSat;
        ctx.strokeStyle = isSel ? 'rgba(255,200,0,0.7)' : 'rgba(255,200,0,0.25)';
        ctx.lineWidth = isSel ? 1.2 : 0.7;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        predicted.forEach(([lat, lon], i) => {
          const [x, y] = latlonToXY(lat, lon, W, H);
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Satellites
      satellites.forEach(sat => {
        const [x, y] = latlonToXY(sat.lat, sat.lon, W, H);
        const isSel = sat.id === selectedSat;
        const color = sat.status === 'NOMINAL'     ? '#00ff88'
          : sat.status === 'DANGER'      ? '#ff3355'
          : sat.status === 'MANEUVERING' ? '#ffaa00'
          : sat.status === 'EVADING'     ? '#ffaa00'
          : sat.status === 'LOW_FUEL'    ? '#ffaa00'
          : sat.status === 'CRITICAL'    ? '#ff3355'
          : sat.status === 'GRAVEYARD'   ? '#555555'
          : '#ff3355';

        // Pulsing red ring when DANGER
        if (sat.status === 'DANGER') {
          const pulse = 0.3 + 0.5 * Math.abs(Math.sin(Date.now() / 400));
          ctx.strokeStyle = '#ff3355';
          ctx.lineWidth = 2;
          ctx.globalAlpha = pulse;
          ctx.beginPath(); ctx.arc(x, y, 18, 0, Math.PI * 2); ctx.stroke();
          ctx.globalAlpha = 1;
        }

        if (isSel) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.globalAlpha = 0.4;
          ctx.beginPath(); ctx.arc(x, y, 14, 0, Math.PI * 2); ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // Diamond — larger when DANGER
        const size = sat.status === 'DANGER' ? 7 : 5;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(x, y - size); ctx.lineTo(x + size - 1, y);
        ctx.lineTo(x, y + size); ctx.lineTo(x - (size - 1), y);
        ctx.closePath(); ctx.fill();

        if (isSel || satellites.length < 20) {
          ctx.fillStyle = 'rgba(232,244,255,0.85)';
          ctx.font = '9px Share Tech Mono, monospace';
          ctx.fillText(sat.id.replace('SAT-', ''), x + 6, y - 3);
        }
      });

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [satellites, debrisCloud, selectedSat]);

  function handleClick(e) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top)  * scaleY;

    let closest = null, minDist = 20;
    satellites.forEach(sat => {
      const [x, y] = latlonToXY(sat.lat, sat.lon, canvas.width, canvas.height);
      const d = Math.hypot(mx - x, my - y);
      if (d < minDist) { minDist = d; closest = sat.id; }
    });
    if (closest) onSelectSat(closest);
  }

  return (
    <canvas ref={canvasRef} width={WORLD_W} height={WORLD_H}
      onClick={handleClick}
      style={{ width: '100%', height: '100%', cursor: 'crosshair', display: 'block' }} />
  );
}