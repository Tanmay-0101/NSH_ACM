import React, { useState, useEffect } from 'react';

export default function StatusBar({ connected, data, onStep, stepping, simTime }) {
  const [tick, setTick] = useState(0);
  const [stepSize, setStepSize] = useState(60);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const satCount = data?.satellites?.length || 0;
  const debrisCount = data?.debris_cloud?.length || 0;
  const ts = data?.timestamp || simTime || '—';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 20,
      padding: '0 16px',
      height: '100%',
      borderBottom: '1px solid var(--border-dim)',
      background: 'var(--bg-deep)',
      fontFamily: 'Share Tech Mono, monospace',
      fontSize: 11,
      flexWrap: 'wrap',
    }}>
      {/* Logo */}
      <div style={{
        fontFamily: 'Rajdhani, sans-serif',
        fontWeight: 700,
        fontSize: 16,
        letterSpacing: '0.15em',
        color: '#00c8ff',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}>
        Orbital<span style={{ color: '#7aa8c8', fontWeight: 300 }}>Insight</span>
        <span style={{ fontSize: 8, marginLeft: 8, color: '#3a5a78', fontFamily: 'Share Tech Mono', verticalAlign: 'middle' }}>
          ACM v1.0
        </span>
      </div>

      <div style={{ width: 1, height: 20, background: 'var(--border-dim)' }} />

      {/* Connection status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: connected ? '#00ff88' : '#ff3355',
          boxShadow: connected ? '0 0 6px #00ff88' : '0 0 6px #ff3355',
          animation: connected ? 'pulse-dot 1.5s infinite' : 'none',
        }} />
        <span style={{ color: connected ? '#00ff88' : '#ff3355' }}>
          {connected ? 'UPLINK OK' : 'NO SIGNAL'}
        </span>
      </div>

      <div style={{ color: '#3a5a78' }}>|</div>

      <div style={{ color: '#7aa8c8' }}>
        <span style={{ color: '#3a5a78' }}>SATS </span>{satCount}
        <span style={{ margin: '0 8px', color: '#3a5a78' }}>|</span>
        <span style={{ color: '#3a5a78' }}>DEBRIS </span>
        <span style={{ color: debrisCount > 1000 ? '#ffaa00' : '#7aa8c8' }}>{debrisCount.toLocaleString()}</span>
      </div>

      <div style={{ color: '#3a5a78' }}>|</div>

      {/* Sim time */}
      <div style={{ color: '#7aa8c8', whiteSpace: 'nowrap' }}>
        <span style={{ color: '#3a5a78' }}>SIM-T </span>
        <span style={{ color: '#00c8ff' }}>{ts.toString().slice(0, 19).replace('T', ' ')}</span>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Sim controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color: '#3a5a78', fontSize: 10 }}>STEP</span>
        <select
          value={stepSize}
          onChange={e => setStepSize(+e.target.value)}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-mid)',
            color: '#7aa8c8',
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 10,
            padding: '3px 6px',
            borderRadius: 2,
            cursor: 'pointer',
          }}
        >
          <option value={60}>60s</option>
          <option value={300}>5 min</option>
          <option value={3600}>1 hr</option>
          <option value={21600}>6 hr</option>
          <option value={86400}>24 hr</option>
        </select>
        <button
          onClick={() => onStep(stepSize)}
          disabled={stepping}
          style={{
            padding: '4px 14px',
            fontFamily: 'Rajdhani, sans-serif',
            fontWeight: 600,
            fontSize: 11,
            letterSpacing: '0.1em',
            background: stepping ? 'rgba(0,200,255,0.05)' : 'rgba(0,200,255,0.1)',
            border: '1px solid rgba(0,200,255,0.4)',
            color: stepping ? '#3a5a78' : '#00c8ff',
            borderRadius: 2,
            cursor: stepping ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {stepping ? '...' : '▶ ADVANCE'}
        </button>
      </div>
    </div>
  );
}