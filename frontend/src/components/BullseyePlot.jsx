import React, { useEffect, useRef } from 'react';

export default function BullseyePlot({ selectedSat, debrisCloud = [], satellites = [] }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const maxR = Math.min(W, H) / 2 - 20;

    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#060d14';
    ctx.fillRect(0, 0, W, H);

    // Rings
    const rings = [
      { r: maxR * 0.25, label: '1 km', color: 'rgba(255,51,85,0.3)' },
      { r: maxR * 0.5,  label: '5 km', color: 'rgba(255,170,0,0.2)' },
      { r: maxR * 0.75, label: '25 km', color: 'rgba(0,200,255,0.1)' },
      { r: maxR,        label: '100 km', color: 'rgba(0,200,255,0.05)' },
    ];

    rings.forEach(({ r, label, color }) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = 'rgba(122,168,200,0.5)';
      ctx.font = '9px Share Tech Mono, monospace';
      ctx.fillText(label, cx + r + 3, cy - 3);
    });

    // Crosshairs
    ctx.strokeStyle = 'rgba(0,200,255,0.15)';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy); ctx.stroke();
    ctx.setLineDash([]);

    // Center satellite
    const sat = satellites.find(s => s.id === selectedSat);
    if (!sat) {
      ctx.fillStyle = 'rgba(122,168,200,0.4)';
      ctx.font = '11px Exo 2, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Select a satellite', cx, cy);
      ctx.textAlign = 'left';
      return;
    }

    // Plot nearby debris as if they were close approaches
    // In real system these would come from CDM data with TCA and relative position
    // Here we simulate relative positions from lat/lon delta
    debrisCloud.slice(0, 200).forEach(([id, dLat, dLon, alt]) => {
      const dlat = dLat - sat.lat;
      const dlon = dLon - sat.lon;
      const dist = Math.sqrt(dlat * dlat + dlon * dlon) * 111; // rough km

      if (dist > 150) return;

      const angle = Math.atan2(dlon, dlat);
      const r = Math.min((dist / 100) * maxR, maxR);
      const px = cx + r * Math.sin(angle);
      const py = cy - r * Math.cos(angle);

      // Color by distance
      let color;
      if (dist < 1)       color = '#ff3355';
      else if (dist < 5)  color = '#ffaa00';
      else if (dist < 25) color = '#ffdd44';
      else                color = '#00c8ff';

      ctx.fillStyle = color;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      ctx.arc(px, py, dist < 5 ? 3 : 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    // Center dot — selected satellite
    ctx.fillStyle = '#00ff88';
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#00ff88';
    ctx.font = '9px Share Tech Mono, monospace';
    ctx.fillText(selectedSat || '', cx + 8, cy - 8);

    // Legend
    const legend = [
      { color: '#ff3355', label: 'Critical < 1 km' },
      { color: '#ffaa00', label: 'Warning < 5 km' },
      { color: '#ffdd44', label: 'Caution < 25 km' },
      { color: '#00c8ff', label: 'Safe' },
    ];
    legend.forEach(({ color, label }, i) => {
      const lx = 8, ly = H - 80 + i * 18;
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(lx + 4, ly + 4, 3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(122,168,200,0.7)';
      ctx.font = '9px Share Tech Mono, monospace';
      ctx.fillText(label, lx + 12, ly + 8);
    });

  }, [selectedSat, debrisCloud, satellites]);

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={300}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
}