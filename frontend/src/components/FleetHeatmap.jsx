import React, { useEffect, useRef } from 'react';

const MAX_FUEL = 50.0;

function FuelBar({ satId, fuelKg, status, isSelected, onClick }) {
  const pct = Math.max(0, Math.min(100, (fuelKg / MAX_FUEL) * 100));
  const color = pct > 40 ? '#00ff88' : pct > 15 ? '#ffaa00' : '#ff3355';

  return (
    <div onClick={onClick} style={{
      padding: '6px 10px',
      cursor: 'pointer',
      background: isSelected ? 'rgba(0,200,255,0.07)' : 'transparent',
      borderLeft: isSelected ? '2px solid #00c8ff' : '2px solid transparent',
      transition: 'all 0.15s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: isSelected ? '#00c8ff' : '#7aa8c8' }}>
          {satId.replace('SAT-', '')}
        </span>
        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color }}>
          {fuelKg != null ? `${fuelKg.toFixed(1)}kg` : '--'}
        </span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: color,
          borderRadius: 2, boxShadow: `0 0 6px ${color}`, transition: 'width 0.5s ease',
        }} />
      </div>
      <div style={{ marginTop: 3, fontSize: 9, fontFamily: 'Share Tech Mono, monospace',
        color: status === 'NOMINAL' ? '#00ff8880' : status === 'EVADING' ? '#ffaa0080' : '#ff335580',
        letterSpacing: '0.05em' }}>
        {status}
      </div>
    </div>
  );
}

function DvGraph({ efficiency }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#060d14';
    ctx.fillRect(0, 0, W, H);

    const avoided   = efficiency?.collisions_avoided || 0;
    const dvSpent   = efficiency?.total_dv_spent_ms || 0;
    const avgDv     = efficiency?.avg_dv_per_avoidance || 0;

    // Axes
    ctx.strokeStyle = 'rgba(0,200,255,0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(30, 10); ctx.lineTo(30, H - 20); ctx.lineTo(W - 10, H - 20); ctx.stroke();

    // Labels
    ctx.fillStyle = '#3a5a78';
    ctx.font = '8px Share Tech Mono, monospace';
    ctx.fillText('ΔV COST vs COLLISIONS AVOIDED', 35, 18);

    if (avoided === 0) {
      ctx.fillStyle = '#3a5a78';
      ctx.font = '9px Share Tech Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('No avoidance events yet', W / 2, H / 2);
      ctx.textAlign = 'left';
      return;
    }

    // Bar for ΔV spent
    const maxDv = Math.max(dvSpent, 100);
    const barW  = Math.min(((W - 50) * 0.6), (dvSpent / maxDv) * (W - 50));
    const barH  = 14;
    const barY  = H - 55;

    ctx.fillStyle = 'rgba(0,200,255,0.15)';
    ctx.fillRect(32, barY, W - 45, barH);
    ctx.fillStyle = '#00c8ff';
    ctx.fillRect(32, barY, barW, barH);
    ctx.fillStyle = '#e8f4ff';
    ctx.font = '9px Share Tech Mono, monospace';
    ctx.fillText(`ΔV: ${dvSpent.toFixed(1)} m/s total`, 36, barY + 10);

    // Bar for collisions avoided
    const barY2 = H - 32;
    const barW2 = Math.min(W - 50, avoided * 20);
    ctx.fillStyle = 'rgba(0,255,136,0.15)';
    ctx.fillRect(32, barY2, W - 45, barH);
    ctx.fillStyle = '#00ff88';
    ctx.fillRect(32, barY2, barW2, barH);
    ctx.fillStyle = '#e8f4ff';
    ctx.fillText(`Avoided: ${avoided} conjunction${avoided !== 1 ? 's' : ''}`, 36, barY2 + 10);

    // Efficiency ratio
    ctx.fillStyle = '#ffaa00';
    ctx.font = '9px Share Tech Mono, monospace';
    ctx.fillText(`Avg: ${avgDv.toFixed(1)} m/s per avoidance`, 36, barY - 8);

  }, [efficiency]);

  return (
    <canvas ref={canvasRef} width={190} height={110}
      style={{ width: '100%', height: 110, display: 'block' }} />
  );
}

export default function FleetHeatmap({ satellites = [], selectedSat, onSelectSat, efficiency }) {
  const totalFuel     = satellites.reduce((s, sat) => s + (sat.fuel_kg || 0), 0);
  const nominalCount  = satellites.filter(s => s.status === 'NOMINAL').length;
  const criticalCount = satellites.filter(s => (s.fuel_kg / MAX_FUEL) < 0.15).length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1,
        background: 'var(--border-dim)', borderBottom: '1px solid var(--border-dim)', flexShrink: 0 }}>
        {[
          { label: 'Total Sats', val: satellites.length, color: '#00c8ff' },
          { label: 'Nominal',    val: nominalCount,       color: '#00ff88' },
          { label: 'Low Fuel',   val: criticalCount,      color: criticalCount > 0 ? '#ff3355' : '#7aa8c8' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ padding: '8px 0', textAlign: 'center', background: 'var(--bg-panel)' }}>
            <div style={{ fontFamily: 'Rajdhani', fontSize: 20, fontWeight: 600, color }}>{val}</div>
            <div style={{ fontSize: 9, color: '#3a5a78', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Fuel list */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {satellites.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: '#3a5a78',
            fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
            Awaiting telemetry...
          </div>
        ) : (
          [...satellites]
            .sort((a, b) => (a.fuel_kg || 0) - (b.fuel_kg || 0))
            .map(sat => (
              <FuelBar key={sat.id} satId={sat.id} fuelKg={sat.fuel_kg}
                status={sat.status} isSelected={sat.id === selectedSat}
                onClick={() => onSelectSat(sat.id)} />
            ))
        )}
      </div>

      {/* ΔV Cost vs Collisions Avoided graph */}
      <div style={{ borderTop: '1px solid var(--border-dim)', flexShrink: 0 }}>
        <div style={{ padding: '4px 10px 2px', fontSize: 9, fontFamily: 'Share Tech Mono, monospace',
          color: '#3a5a78', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Efficiency Analysis
        </div>
        <DvGraph efficiency={efficiency} />
      </div>

      {/* Total propellant bar */}
      <div style={{ padding: '8px 10px', borderTop: '1px solid var(--border-dim)',
        background: 'var(--bg-deep)', flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: '#3a5a78', fontFamily: 'Share Tech Mono, monospace', letterSpacing: '0.05em' }}>
            FLEET PROPELLANT
          </span>
          <span style={{ fontSize: 10, color: '#00c8ff', fontFamily: 'Share Tech Mono, monospace' }}>
            {totalFuel.toFixed(1)} kg
          </span>
        </div>
        <div style={{ height: 3, background: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
          <div style={{
            width: `${satellites.length > 0 ? (totalFuel / (satellites.length * MAX_FUEL)) * 100 : 0}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #ff3355, #ffaa00, #00ff88)',
            borderRadius: 2,
          }} />
        </div>
      </div>
    </div>
  );
}