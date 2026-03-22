import React, { useState, useCallback } from 'react';
import GroundTrackMap from './components/GroundTrackMap';
import BullseyePlot from './components/BullseyePlot';
import FleetHeatmap from './components/FleetHeatmap';
import ManeuverGantt from './components/ManeuverGantt';
import StatusBar from './components/StatusBar';
import TelemetryFeed from './components/TelemetryFeed';
import { useSnapshot, useSimControl, useManeuverHistory } from './hooks';

export default function App() {
  const { data, error, connected } = useSnapshot(1000);
  const { step, stepping } = useSimControl();
  const { history: maneuverHistory } = useManeuverHistory();
  const [selectedSat, setSelectedSat] = useState(null);
  const [activePanel, setActivePanel] = useState('gantt');

  const satellites = Array.isArray(data?.satellites) ? data.satellites : [];
  const debrisCloud = Array.isArray(data?.debris_cloud) ? data.debris_cloud : [];
  const cdmWarnings = data?.active_cdm_warnings || 0;

  const handleSelectSat = useCallback((id) => {
    setSelectedSat(prev => prev === id ? null : id);
  }, []);

  const selectedSatData = satellites.find(s => s.id === selectedSat) || null;

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#020408',
      overflow: 'hidden',
    }}>
      {/* Top status bar */}
      <div style={{ height: 44, flexShrink: 0, minHeight: 44 }}>
        <StatusBar
          connected={connected}
          data={data}
          onStep={step}
          stepping={stepping}
          simTime={data?.timestamp}
        />
      </div>

      {/* Main content grid */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '220px 1fr 220px',
        gridTemplateRows: '1fr 200px',
        gap: '1px',
        background: 'rgba(0,200,255,0.06)',
        overflow: 'hidden',
        minHeight: 0,
      }}>

        {/* LEFT: Fleet heatmap spans both rows */}
        <div style={{
          gridColumn: '1',
          gridRow: '1 / 3',
          background: '#0a1520',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: 1,
            background: 'linear-gradient(90deg, transparent, #00c8ff, transparent)',
            opacity: 0.4,
          }} />
          <div style={{
            padding: '8px 14px',
            borderBottom: '1px solid rgba(0,200,255,0.08)',
            fontFamily: 'Rajdhani, sans-serif',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color: '#00c8ff',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: '#00c8ff',
              boxShadow: '0 0 6px #00c8ff',
            }} />
            Fleet Resources
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <FleetHeatmap
              satellites={satellites}
              selectedSat={selectedSat}
              onSelectSat={handleSelectSat}
            />
          </div>
        </div>

        {/* CENTER TOP: Ground track map */}
        <div style={{
          gridColumn: '2',
          gridRow: '1',
          background: '#0a1520',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: 1,
            background: 'linear-gradient(90deg, transparent, #00c8ff, transparent)',
            opacity: 0.4,
          }} />
          <div style={{
            padding: '8px 14px',
            borderBottom: '1px solid rgba(0,200,255,0.08)',
            fontFamily: 'Rajdhani, sans-serif',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color: '#00c8ff',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: '#00c8ff',
            }} />
            Ground Track — Mercator Projection
            <span style={{
              marginLeft: 'auto',
              fontSize: 9,
              color: '#3a5a78',
              fontFamily: 'Share Tech Mono, monospace',
            }}>
              {debrisCloud.length.toLocaleString()} debris · {satellites.length} sats
            </span>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>
            <GroundTrackMap
              satellites={satellites}
              debrisCloud={debrisCloud}
              selectedSat={selectedSat}
              onSelectSat={handleSelectSat}
            />
          </div>
        </div>

        {/* RIGHT: Bullseye spans both rows */}
        <div style={{
          gridColumn: '3',
          gridRow: '1 / 3',
          background: '#0a1520',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: 1,
            background: 'linear-gradient(90deg, transparent, #00c8ff, transparent)',
            opacity: 0.4,
          }} />
          <div style={{
            padding: '8px 14px',
            borderBottom: '1px solid rgba(0,200,255,0.08)',
            fontFamily: 'Rajdhani, sans-serif',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color: '#00c8ff',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: '#00c8ff',
            }} />
            Conjunction Bullseye
          </div>

          {selectedSatData ? (
            <div style={{
              padding: '8px 12px',
              borderBottom: '1px solid rgba(0,200,255,0.08)',
              fontFamily: 'Share Tech Mono, monospace',
              fontSize: 10,
              flexShrink: 0,
            }}>
              <div style={{ color: '#00c8ff', marginBottom: 6, fontSize: 11 }}>
                {selectedSatData.id}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', rowGap: 3 }}>
                {[
                  ['LAT', `${(selectedSatData.lat || 0).toFixed(3)}°`],
                  ['LON', `${(selectedSatData.lon || 0).toFixed(3)}°`],
                  ['FUEL', `${(selectedSatData.fuel_kg || 0).toFixed(2)} kg`],
                  ['STATUS', selectedSatData.status || '—'],
                ].map(([k, v]) => (
                  <React.Fragment key={k}>
                    <span style={{ color: '#3a5a78' }}>{k}</span>
                    <span style={{
                      textAlign: 'right',
                      color: k === 'STATUS'
                        ? (selectedSatData.status === 'NOMINAL' ? '#00ff88' : '#ffaa00')
                        : '#e8f4ff',
                    }}>{v}</span>
                  </React.Fragment>
                ))}
              </div>
            </div>
          ) : (
            <div style={{
              padding: '8px 12px',
              borderBottom: '1px solid rgba(0,200,255,0.08)',
              fontFamily: 'Share Tech Mono, monospace',
              fontSize: 10,
              color: '#3a5a78',
              flexShrink: 0,
            }}>
              Click a satellite to inspect
            </div>
          )}

          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: 4 }}>
            <BullseyePlot
              selectedSat={selectedSat}
              debrisCloud={debrisCloud}
              satellites={satellites}
            />
          </div>

          {cdmWarnings > 0 && (
            <div style={{
              margin: '0 8px 8px',
              padding: '5px 10px',
              background: 'rgba(255,51,85,0.1)',
              border: '1px solid rgba(255,51,85,0.3)',
              borderRadius: 2,
              fontFamily: 'Share Tech Mono, monospace',
              fontSize: 10,
              color: '#ff3355',
              flexShrink: 0,
            }}>
              ⚠ {cdmWarnings} ACTIVE CDM{cdmWarnings > 1 ? 'S' : ''}
            </div>
          )}
        </div>

        {/* CENTER BOTTOM: Gantt / Telemetry tabs */}
        <div style={{
          gridColumn: '2',
          gridRow: '2',
          background: '#0a1520',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: 1,
            background: 'linear-gradient(90deg, transparent, #00c8ff, transparent)',
            opacity: 0.4,
          }} />

          <div style={{
            display: 'flex',
            borderBottom: '1px solid rgba(0,200,255,0.08)',
            flexShrink: 0,
          }}>
            {[
              { id: 'gantt', label: 'Maneuver Timeline' },
              { id: 'telemetry', label: 'Telemetry Log' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActivePanel(tab.id)}
                style={{
                  padding: '7px 14px',
                  fontFamily: 'Rajdhani, sans-serif',
                  fontWeight: 600,
                  fontSize: 10,
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  background: activePanel === tab.id ? 'rgba(0,200,255,0.07)' : 'transparent',
                  color: activePanel === tab.id ? '#00c8ff' : '#3a5a78',
                  borderBottom: activePanel === tab.id ? '2px solid #00c8ff' : '2px solid transparent',
                  borderTop: 'none',
                  borderLeft: 'none',
                  borderRight: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {tab.label}
              </button>
            ))}
            {cdmWarnings > 0 && (
              <div style={{
                marginLeft: 'auto',
                display: 'flex',
                alignItems: 'center',
                paddingRight: 12,
                gap: 6,
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#ff3355' }} />
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#ff3355' }}>
                  {cdmWarnings} CDM
                </span>
              </div>
            )}
          </div>

          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            {activePanel === 'gantt'
              ? <ManeuverGantt maneuverHistory={maneuverHistory} />
              : <TelemetryFeed satellites={satellites} cdmWarnings={cdmWarnings} connected={connected} />
            }
          </div>
        </div>

      </div>

      {/* Offline toast */}
      {error && (
        <div style={{
          position: 'fixed',
          bottom: 16, right: 16,
          background: 'rgba(10,21,32,0.95)',
          border: '1px solid rgba(255,51,85,0.4)',
          borderRadius: 4,
          padding: '8px 16px',
          fontFamily: 'Share Tech Mono, monospace',
          fontSize: 11,
          color: '#ff3355',
          zIndex: 999,
        }}>
          API offline — retrying ({error})
        </div>
      )}
    </div>
  );
}