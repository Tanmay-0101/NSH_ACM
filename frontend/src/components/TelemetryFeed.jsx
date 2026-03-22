import React, { useEffect, useRef } from 'react';

export default function TelemetryFeed({ satellites = [], cdmWarnings = 0, connected }) {
  const logRef = useRef(null);
  const prevSatsRef = useRef({});

  // Build log entries from satellite state changes
  const logLines = [];

  satellites.forEach(sat => {
    const prev = prevSatsRef.current[sat.id];
    if (prev && prev.status !== sat.status) {
      logLines.push({
        time: new Date().toISOString().slice(11, 19),
        type: sat.status === 'NOMINAL' ? 'INFO' : sat.status === 'EVADING' ? 'WARN' : 'CRIT',
        msg: `${sat.id} → ${sat.status}`,
      });
    }
    prevSatsRef.current[sat.id] = sat;
  });

  const staticLines = [
    ...(cdmWarnings > 0 ? [{
      time: new Date().toISOString().slice(11, 19),
      type: 'WARN',
      msg: `${cdmWarnings} active CDM warning${cdmWarnings > 1 ? 's' : ''}`,
    }] : []),
    {
      time: new Date().toISOString().slice(11, 19),
      type: 'INFO',
      msg: `Telemetry snapshot: ${satellites.length} sats`,
    },
    ...logLines,
  ];

  const typeColor = { INFO: '#00c8ff', WARN: '#ffaa00', CRIT: '#ff3355', OK: '#00ff88' };

  return (
    <div style={{
      height: '100%',
      overflowY: 'auto',
      padding: '6px 10px',
      fontFamily: 'Share Tech Mono, monospace',
      fontSize: 10,
    }}>
      {satellites.length === 0 && (
        <div style={{ color: '#3a5a78', paddingTop: 8 }}>
          Awaiting telemetry uplink...
        </div>
      )}
      {satellites.map(sat => (
        <div key={sat.id} style={{
          display: 'flex',
          gap: 8,
          padding: '2px 0',
          borderBottom: '1px solid rgba(0,200,255,0.04)',
        }}>
          <span style={{ color: '#3a5a78', flexShrink: 0 }}>
            {new Date().toISOString().slice(11, 19)}
          </span>
          <span style={{
            color: sat.status === 'NOMINAL' ? '#00ff88'
              : sat.status === 'EVADING' ? '#ffaa00'
              : '#ff3355',
            flexShrink: 0,
            width: 50,
          }}>
            {sat.status}
          </span>
          <span style={{ color: '#7aa8c8' }}>{sat.id}</span>
          <span style={{ color: '#3a5a78', marginLeft: 'auto', flexShrink: 0 }}>
            {sat.fuel_kg != null ? `⛽ ${sat.fuel_kg.toFixed(1)}` : ''}
          </span>
        </div>
      ))}
      {cdmWarnings > 0 && (
        <div style={{
          marginTop: 6,
          padding: '4px 8px',
          background: 'rgba(255,170,0,0.1)',
          border: '1px solid rgba(255,170,0,0.3)',
          borderRadius: 2,
          color: '#ffaa00',
          fontSize: 10,
        }}>
          ⚠ {cdmWarnings} conjunction warning{cdmWarnings > 1 ? 's' : ''} active
        </div>
      )}
    </div>
  );
}