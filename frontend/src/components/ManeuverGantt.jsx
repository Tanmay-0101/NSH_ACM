import React, { useState } from 'react';

function TimeBlock({ type, color, dimColor }) {
  return (
    <div style={{ flex: 1, height: 16, background: 'rgba(255,255,255,0.03)', borderRadius: 2, position: 'relative', display: 'flex' }}>
      <div style={{
        width: '30%',
        height: '100%',
        background: color,
        borderRadius: '2px 0 0 2px',
        display: 'flex', alignItems: 'center', paddingLeft: 4, overflow: 'hidden',
      }}>
        <span style={{ fontSize: 7, fontFamily: 'Share Tech Mono, monospace', color: '#000', whiteSpace: 'nowrap', fontWeight: 700 }}>
          BURN
        </span>
      </div>
      <div style={{
        width: '70%',
        height: '100%',
        background: dimColor,
        borderRadius: '0 2px 2px 0',
        display: 'flex', alignItems: 'center', paddingLeft: 4, overflow: 'hidden',
      }}>
        <span style={{ fontSize: 7, fontFamily: 'Share Tech Mono, monospace', color: 'rgba(255,255,255,0.35)', whiteSpace: 'nowrap' }}>
          COOLDOWN 600s
        </span>
      </div>
    </div>
  );
}

export default function ManeuverGantt({ maneuverHistory = [] }) {
  const [filter, setFilter] = useState('ALL');

  const typeColors = {
    EVASION:  { bg: 'rgba(255,170,0,0.85)',  dim: 'rgba(255,170,0,0.12)' },
    RECOVERY: { bg: 'rgba(0,200,255,0.85)',  dim: 'rgba(0,200,255,0.10)' },
    EOL:      { bg: 'rgba(255,51,85,0.85)',  dim: 'rgba(255,51,85,0.10)' },
    STATION:  { bg: 'rgba(0,255,136,0.85)',  dim: 'rgba(0,255,136,0.10)' },
  };

  const statusDot = {
    EXECUTED:  '#00ff88',
    SCHEDULED: '#ffaa00',
    FAILED:    '#ff3355',
  };

  const filtered = maneuverHistory.filter(m =>
    filter === 'ALL' || m.type === filter
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 1, padding: '5px 10px', borderBottom: '1px solid var(--border-dim)', flexShrink: 0 }}>
        {['ALL', 'EVASION', 'RECOVERY', 'EOL'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '3px 10px',
            fontSize: 9,
            fontFamily: 'Rajdhani, sans-serif',
            fontWeight: 600,
            letterSpacing: '0.1em',
            background: filter === f ? 'rgba(0,200,255,0.1)' : 'transparent',
            color: filter === f ? '#00c8ff' : '#3a5a78',
            border: filter === f ? '1px solid rgba(0,200,255,0.3)' : '1px solid transparent',
            borderRadius: 2,
            cursor: 'pointer',
          }}>
            {f}
            {/* count badge */}
            {f !== 'ALL' && maneuverHistory.filter(m => m.type === f).length > 0 && (
              <span style={{
                marginLeft: 4, fontSize: 8,
                color: f === 'EVASION' ? '#ffaa00' : f === 'RECOVERY' ? '#00c8ff' : '#ff3355',
              }}>
                {maneuverHistory.filter(m => m.type === f).length}
              </span>
            )}
          </button>
        ))}
        <span style={{
          marginLeft: 'auto',
          fontSize: 9,
          fontFamily: 'Share Tech Mono, monospace',
          color: '#3a5a78',
          alignSelf: 'center',
        }}>
          {maneuverHistory.length} total burns
        </span>
      </div>

      {/* Burn list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 10px' }}>
        {filtered.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#3a5a78',
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 11,
            paddingTop: 24,
          }}>
            {maneuverHistory.length === 0
              ? 'No burns executed yet — advance simulation to trigger COLA'
              : `No ${filter} burns`}
          </div>
        ) : (
          filtered.map((m, i) => {
            const { bg, dim } = typeColors[m.type] || typeColors.EVASION;
            return (
              <div key={m.id || i} style={{
                marginBottom: 8,
                padding: '6px 8px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 3,
                borderLeft: `2px solid ${bg}`,
              }}>
                {/* Row 1: status dot + burn id + time */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: statusDot[m.status] || '#7aa8c8',
                    boxShadow: `0 0 4px ${statusDot[m.status] || '#7aa8c8'}`,
                    flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: 9, fontFamily: 'Share Tech Mono, monospace', color: '#7aa8c8',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                  }}>
                    {m.satId} · {m.burnId?.replace('AUTO_', '').replace(/_\d+$/, '') || m.type}
                  </span>
                  <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#3a5a78', flexShrink: 0 }}>
                    {m.timestamp?.slice(11, 19)}
                  </span>
                </div>

                {/* Row 2: Gantt bar */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {/* Type badge */}
                  <span style={{
                    fontSize: 8, fontFamily: 'Share Tech Mono, monospace',
                    color: bg.replace('0.85', '1'),
                    background: dim,
                    padding: '1px 5px', borderRadius: 2,
                    flexShrink: 0,
                  }}>
                    {m.type}
                  </span>
                  <TimeBlock type={m.type} color={bg} dimColor={dim} />
                  {/* Fuel remaining */}
                  {m.fuelLeft != null && (
                    <span style={{
                      fontSize: 8, fontFamily: 'Share Tech Mono, monospace',
                      color: m.fuelLeft < 5 ? '#ff3355' : '#3a5a78',
                      flexShrink: 0,
                    }}>
                      {m.fuelLeft.toFixed(1)}kg
                    </span>
                  )}
                  {/* Auto badge */}
                  {m.isAuto && (
                    <span style={{
                      fontSize: 7, fontFamily: 'Share Tech Mono, monospace',
                      color: '#00c8ff', background: 'rgba(0,200,255,0.1)',
                      padding: '1px 4px', borderRadius: 2, flexShrink: 0,
                    }}>
                      AUTO
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Legend */}
      <div style={{
        padding: '5px 10px',
        borderTop: '1px solid var(--border-dim)',
        display: 'flex', gap: 10, flexWrap: 'wrap', flexShrink: 0,
      }}>
        {Object.entries(typeColors).map(([type, { bg }]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <div style={{ width: 10, height: 6, background: bg, borderRadius: 1 }} />
            <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#3a5a78' }}>{type}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#00c8ff',
            background: 'rgba(0,200,255,0.1)', padding: '0 3px', borderRadius: 2 }}>AUTO</span>
          <span style={{ fontSize: 8, fontFamily: 'Share Tech Mono, monospace', color: '#3a5a78' }}>= autonomous</span>
        </div>
      </div>
    </div>
  );
}