import React from 'react';

const MAX_FUEL = 50.0;

function FuelBar({ satId, fuelKg, status, isSelected, onClick }) {
  const pct = Math.max(0, Math.min(100, (fuelKg / MAX_FUEL) * 100));
  const color = pct > 40 ? '#00ff88' : pct > 15 ? '#ffaa00' : '#ff3355';

  return (
    <div
      onClick={onClick}
      style={{
        padding: '6px 10px',
        cursor: 'pointer',
        background: isSelected ? 'rgba(0,200,255,0.07)' : 'transparent',
        borderLeft: isSelected ? '2px solid #00c8ff' : '2px solid transparent',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{
          fontFamily: 'Share Tech Mono, monospace',
          fontSize: 10,
          color: isSelected ? '#00c8ff' : '#7aa8c8',
        }}>
          {satId.replace('SAT-', '')}
        </span>
        <span style={{
          fontFamily: 'Share Tech Mono, monospace',
          fontSize: 10,
          color,
        }}>
          {fuelKg != null ? `${fuelKg.toFixed(1)}kg` : '--'}
        </span>
      </div>
      <div style={{
        height: 4,
        background: 'rgba(255,255,255,0.06)',
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: color,
          borderRadius: 2,
          boxShadow: `0 0 6px ${color}`,
          transition: 'width 0.5s ease',
        }} />
      </div>
      <div style={{
        marginTop: 3,
        fontSize: 9,
        fontFamily: 'Share Tech Mono, monospace',
        color: status === 'NOMINAL' ? '#00ff8880' : status === 'EVADING' ? '#ffaa0080' : '#ff335580',
        letterSpacing: '0.05em',
      }}>
        {status}
      </div>
    </div>
  );
}

export default function FleetHeatmap({ satellites = [], selectedSat, onSelectSat }) {
  const totalFuel = satellites.reduce((s, sat) => s + (sat.fuel_kg || 0), 0);
  const nominalCount = satellites.filter(s => s.status === 'NOMINAL').length;
  const criticalCount = satellites.filter(s => (s.fuel_kg / MAX_FUEL) < 0.15).length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Summary stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 1,
        background: 'var(--border-dim)',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        {[
          { label: 'Total Sats', val: satellites.length, color: '#00c8ff' },
          { label: 'Nominal', val: nominalCount, color: '#00ff88' },
          { label: 'Low Fuel', val: criticalCount, color: criticalCount > 0 ? '#ff3355' : '#7aa8c8' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{
            padding: '8px 0',
            textAlign: 'center',
            background: 'var(--bg-panel)',
          }}>
            <div style={{ fontFamily: 'Rajdhani', fontSize: 20, fontWeight: 600, color }}>
              {val}
            </div>
            <div style={{ fontSize: 9, color: '#3a5a78', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Fuel list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {satellites.length === 0 ? (
          <div style={{
            padding: 20,
            textAlign: 'center',
            color: '#3a5a78',
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 11,
          }}>
            Awaiting telemetry...
          </div>
        ) : (
          [...satellites]
            .sort((a, b) => (a.fuel_kg || 0) - (b.fuel_kg || 0))
            .map(sat => (
              <FuelBar
                key={sat.id}
                satId={sat.id}
                fuelKg={sat.fuel_kg}
                status={sat.status}
                isSelected={sat.id === selectedSat}
                onClick={() => onSelectSat(sat.id)}
              />
            ))
        )}
      </div>

      {/* Total fuel bar */}
      <div style={{
        padding: '8px 10px',
        borderTop: '1px solid var(--border-dim)',
        background: 'var(--bg-deep)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: '#3a5a78', fontFamily: 'Share Tech Mono, monospace', letterSpacing: '0.05em' }}>
            FLEET TOTAL PROPELLANT
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