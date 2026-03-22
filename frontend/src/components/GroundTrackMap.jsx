import React, { useEffect, useRef, useState } from 'react';

// Pure Canvas 2D ground track — PixiJS-style performance via raw Canvas API
// Handles 10k+ debris objects at 60fps

const WORLD_W = 800;
const WORLD_H = 400;

function latlonToXY(lat, lon, w, h) {
  const x = ((lon + 180) / 360) * w;
  const y = ((90 - lat) / 180) * h;
  return [x, y];
}

// Terminator line: solar declination approx
function getSolarDeclination() {
  const now = new Date();
  const dayOfYear = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
  return -23.45 * Math.cos((2 * Math.PI / 365) * (dayOfYear + 10));
}

export default function GroundTrackMap({ satellites = [], debrisCloud = [], selectedSat, onSelectSat }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const trailsRef = useRef({});

  // Update trails
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
    const W = canvas.width;
    const H = canvas.height;

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

      // Equator & Prime Meridian highlight
      ctx.strokeStyle = 'rgba(0,200,255,0.15)';
      ctx.lineWidth = 1;
      const [, eqY] = latlonToXY(0, 0, W, H);
      ctx.beginPath(); ctx.moveTo(0, eqY); ctx.lineTo(W, eqY); ctx.stroke();
      const [pmX] = latlonToXY(0, 0, W, H);
      ctx.beginPath(); ctx.moveTo(pmX, 0); ctx.lineTo(pmX, H); ctx.stroke();

      // Terminator shadow
      const decl = getSolarDeclination();
      const termX = ((new Date().getUTCHours() * 60 + new Date().getUTCMinutes()) / 1440) * W;
      const shadowX = (termX + W / 2) % W;
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      if (shadowX + W / 2 > W) {
        ctx.fillRect(shadowX - W / 2, 0, W, H);
      } else {
        ctx.fillRect(shadowX, 0, W / 2, H);
      }

      // Ground stations
      const groundStations = [
        { name: 'ISTRAC', lat: 13.03, lon: 77.52 },
        { name: 'Svalbard', lat: 78.23, lon: 15.41 },
        { name: 'Goldstone', lat: 35.43, lon: -116.89 },
        { name: 'Punta Arenas', lat: -53.15, lon: -70.92 },
        { name: 'IIT Delhi', lat: 28.55, lon: 77.19 },
        { name: 'McMurdo', lat: -77.85, lon: 166.67 },
      ];
      groundStations.forEach(gs => {
        const [x, y] = latlonToXY(gs.lat, gs.lon, W, H);
        ctx.strokeStyle = 'rgba(0,255,136,0.5)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = 'rgba(0,255,136,0.8)';
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();
      });

      // Debris cloud (tiny dots, batched)
      ctx.fillStyle = 'rgba(255,100,50,0.5)';
      debrisCloud.forEach(([, lat, lon]) => {
        const [x, y] = latlonToXY(lat, lon, W, H);
        ctx.fillRect(x - 0.5, y - 0.5, 1.5, 1.5);
      });

      // Satellite trails
      Object.entries(trailsRef.current).forEach(([satId, trail]) => {
        if (trail.length < 2) return;
        const isSel = satId === selectedSat;
        ctx.strokeStyle = isSel ? 'rgba(0,200,255,0.6)' : 'rgba(0,200,255,0.2)';
        ctx.lineWidth = isSel ? 1.5 : 0.8;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        trail.forEach(([lat, lon], i) => {
          const [x, y] = latlonToXY(lat, lon, W, H);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Satellites
      satellites.forEach(sat => {
        const [x, y] = latlonToXY(sat.lat, sat.lon, W, H);
        const isSel = sat.id === selectedSat;
        const color = sat.status === 'NOMINAL' ? '#00ff88'
          : sat.status === 'EVADING' ? '#ffaa00'
          : sat.status === 'GRAVEYARD' ? '#444' : '#ff3355';

        if (isSel) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.globalAlpha = 0.4;
          ctx.beginPath();
          ctx.arc(x, y, 14, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // Diamond shape
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(x, y - 5);
        ctx.lineTo(x + 4, y);
        ctx.lineTo(x, y + 5);
        ctx.lineTo(x - 4, y);
        ctx.closePath();
        ctx.fill();

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
    const my = (e.clientY - rect.top) * scaleY;

    let closest = null, minDist = 20;
    satellites.forEach(sat => {
      const [x, y] = latlonToXY(sat.lat, sat.lon, canvas.width, canvas.height);
      const d = Math.hypot(mx - x, my - y);
      if (d < minDist) { minDist = d; closest = sat.id; }
    });
    if (closest) onSelectSat(closest);
  }

  return (
    <canvas
      ref={canvasRef}
      width={WORLD_W}
      height={WORLD_H}
      onClick={handleClick}
      style={{ width: '100%', height: '100%', cursor: 'crosshair', display: 'block' }}
    />
  );
}