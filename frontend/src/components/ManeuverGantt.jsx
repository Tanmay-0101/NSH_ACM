import React, { useState } from 'react';

const COOLDOWN_S = 600;

function TimeBlock({ label, start, duration, color, dimColor, width = 120 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
      <div style={{
        width: 80,
        fontSize: 9,
        fontFamily: 'Share Tech Mono, monospace',
        color: '#7aa8c8',
        flexShrink: 0,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {label}
      </div>
      <div style={{ flex: 1, height: 18, background: 'rgba(255,255,255,0.03)', borderRadius: 2, position: 'relative' }}>
        {/* Burn block */}
        <div style={{
          position: 'absolute',
          left: `${start}%`,
          width: `${Math.max(duration, 2)}%`,
          height: '100%',
          background: color,
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 4,
          overflow: 'hidden',
        }}>
          <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#000', whiteSpace: 'nowrap' }}>
            BURN
          </span>
        </div>
        {/* Cooldown block */}
        <div style={{
          position: 'absolute',
          left: `${start + Math.max(duration, 2)}%`,
          width: `${Math.min(20, 100 - start - duration)}%`,
          height: '100%',
          background: dimColor,
          borderRadius: '0 2px 2px 0',
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 4,
          overflow: 'hidden',
        }}>
          <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}>
            COOLDOWN
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ManeuverGantt({ maneuverHistory = [] }) {
  const [filter, setFilter] = useState('ALL');

  const filtered = maneuverHistory.filter(m =>
    filter === 'ALL' || m.type === filter
  );

  // Demo blocks when no real history
  const demoBlocks = [
    // { id: 1, satId: 'Alpha-04', burnId: 'EVASION_1', type: 'EVASION', time: '14:15:30', status: 'EXECUTED', dvMag: 0.015 },
    // { id: 2, satId: 'Alpha-04', burnId: 'RECOVERY_1', type: 'RECOVERY', time: '15:45:30', status: 'SCHEDULED', dvMag: 0.014 },
    // { id: 3, satId: 'Beta-07', burnId: 'EVASION_1', type: 'EVASION', time: '16:00:00', status: 'SCHEDULED', dvMag: 0.008 },
    // { id: 4, satId: 'Gamma-12', burnId: 'EOL_1', type: 'EOL', time: '18:30:00', status: 'PENDING', dvMag: 0.012 },
  ];

  const display = maneuverHistory.length > 0 ? filtered : demoBlocks;

  const typeColors = {
    EVASION:  { bg: 'rgba(255,170,0,0.8)',   dim: 'rgba(255,170,0,0.15)' },
    RECOVERY: { bg: 'rgba(0,200,255,0.8)',   dim: 'rgba(0,200,255,0.12)' },
    EOL:      { bg: 'rgba(255,51,85,0.8)',   dim: 'rgba(255,51,85,0.12)' },
    STATION:  { bg: 'rgba(0,255,136,0.8)',   dim: 'rgba(0,255,136,0.12)' },
  };

  const statusDot = {
    EXECUTED:  '#00ff88',
    SCHEDULED: '#ffaa00',
    PENDING:   '#00c8ff',
    FAILED:    '#ff3355',
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Filter tabs */}
      <div style={{
        display: 'flex',
        gap: 1,
        padding: '6px 10px',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        {['ALL', 'EVASION', 'RECOVERY', 'EOL'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '3px 10px',
            fontSize: 9,
            fontFamily: 'Rajdhani, sans-serif',
            fontWeight: 600,
            letterSpacing: '0.1em',
            background: filter === f ? 'var(--accent-cyan-dim)' : 'transparent',
            color: filter === f ? '#00c8ff' : '#3a5a78',
            border: filter === f ? '1px solid rgba(0,200,255,0.3)' : '1px solid transparent',
            borderRadius: 2,
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}>
            {f}
          </button>
        ))}
      </div>

      {/* Timeline header */}
      <div style={{
        display: 'flex',
        padding: '4px 10px 4px 96px',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        {['T+0h', 'T+6h', 'T+12h', 'T+18h', 'T+24h'].map((t, i) => (
          <div key={t} style={{
            flex: 1,
            fontSize: 8,
            fontFamily: 'Share Tech Mono, monospace',
            color: '#3a5a78',
            textAlign: i === 0 ? 'left' : 'center',
          }}>{t}</div>
        ))}
      </div>

      {/* Gantt rows */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
        {display.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#3a5a78',
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 11,
            paddingTop: 20,
          }}>
            No maneuvers {filter !== 'ALL' ? `of type ${filter}` : ''}
          </div>
        ) : (
          display.map((m, i) => {
            const { bg, dim } = typeColors[m.type] || typeColors.EVASION;
            const startPct = (i * 18) % 70;
            return (
              <div key={m.id || i} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                  <div style={{
                    width: 6, height: 6,
                    borderRadius: '50%',
                    background: statusDot[m.status] || '#7aa8c8',
                    boxShadow: `0 0 4px ${statusDot[m.status] || '#7aa8c8'}`,
                    flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: 9,
                    fontFamily: 'Share Tech Mono, monospace',
                    color: '#7aa8c8',
                  }}>
                    {m.satId || m.satelliteId} · {m.burnId} · {m.time || m.timestamp?.slice(11, 19)}
                  </span>
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: 8,
                    fontFamily: 'Share Tech Mono, monospace',
                    color: '#3a5a78',
                  }}>
                    {m.dvMag ? `ΔV ${(m.dvMag * 1000).toFixed(1)} m/s` : ''}
                  </span>
                </div>
                <TimeBlock
                  label={`${m.satId || ''} ${m.type || ''}`}
                  start={startPct}
                  duration={5}
                  color={bg}
                  dimColor={dim}
                />
              </div>
            );
          })
        )}
      </div>

      {/* Legend */}
      <div style={{
        padding: '6px 10px',
        borderTop: '1px solid var(--border-dim)',
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
      }}>
        {Object.entries(typeColors).map(([type, { bg }]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 10, height: 6, background: bg, borderRadius: 1 }} />
            <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#3a5a78' }}>
              {type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}