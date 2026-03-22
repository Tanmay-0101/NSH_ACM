import React, { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function AIBriefing({ snapshotData }) {
  const [briefing, setBriefing] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [source, setSource] = useState('');

  const generateBriefing = useCallback(async () => {
    setLoading(true);
    setError('');
    setIsOpen(true);

    try {
      const res = await fetch(`${API_BASE}/api/ai/briefing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setBriefing(json.briefing || 'No briefing generated.');
      setSource(json.source || 'rules');
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      setError('Failed to connect to backend — is uvicorn running?');
    } finally {
      setLoading(false);
    }
  }, []);

  const sats          = snapshotData?.satellites || [];
  const dangerCount   = sats.filter(s => s.status === 'DANGER').length;
  const maneuverCount = sats.filter(s => s.status === 'MANEUVERING').length;
  const lowFuelCount  = sats.filter(s => s.fuel_kg < 10).length;
  const cdms          = snapshotData?.active_cdm_warnings || 0;
  const btnColor      = dangerCount > 0 || cdms > 0 ? '#ff3355' : maneuverCount > 0 ? '#ffaa00' : '#00c8ff';

  return (
    <>
      <button onClick={generateBriefing} disabled={loading} title="Generate AI Fleet Briefing" style={{
        padding: '4px 14px', fontFamily: 'Rajdhani, sans-serif', fontWeight: 700,
        fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        background: `${btnColor}18`, border: `1px solid ${btnColor}`,
        color: loading ? '#3a5a78' : btnColor, borderRadius: 2,
        cursor: loading ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
        display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
      }}>
        {dangerCount > 0 && !loading && (
          <span style={{ width:6, height:6, borderRadius:'50%', background:'#ff3355', boxShadow:'0 0 6px #ff3355', animation:'pulse-dot 0.8s infinite', flexShrink:0 }} />
        )}
        {loading ? '⏳ Analyzing...' : '⚡ AI Briefing'}
      </button>

      {isOpen && (
        <div style={{
          position:'fixed', top:44, left:0, right:0, zIndex:500,
          background:'rgba(6,13,20,0.97)', borderBottom:'1px solid rgba(0,200,255,0.2)',
          padding:'12px 20px', animation:'slideDown 0.2s ease',
        }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
            <span style={{ fontFamily:'Rajdhani, sans-serif', fontWeight:700, fontSize:11, letterSpacing:'0.15em', textTransform:'uppercase', color:'#00c8ff' }}>
              ⚡ AI Fleet Briefing
            </span>
            <span style={{
              fontSize:8, fontFamily:'Share Tech Mono, monospace',
              color: source==='ai' ? '#00ff88' : '#ffaa00',
              background: source==='ai' ? 'rgba(0,255,136,0.1)' : 'rgba(255,170,0,0.1)',
              border: `1px solid ${source==='ai' ? 'rgba(0,255,136,0.3)' : 'rgba(255,170,0,0.3)'}`,
              padding:'1px 6px', borderRadius:2,
            }}>
              {source === 'ai' ? 'Claude AI' : 'Rule-based'}
            </span>
            {[
              { label:`${sats.length} sats`, color:'#00c8ff', show:true },
              { label:`${dangerCount} danger`, color:'#ff3355', show:dangerCount>0 },
              { label:`${cdms} CDM`, color:'#ff3355', show:cdms>0 },
              { label:`${lowFuelCount} low fuel`, color:'#ffaa00', show:lowFuelCount>0 },
            ].filter(p=>p.show).map((p,i) => (
              <span key={i} style={{ padding:'1px 7px', borderRadius:2, fontSize:9, fontFamily:'Share Tech Mono, monospace', color:p.color, background:`${p.color}18`, border:`1px solid ${p.color}40` }}>
                {p.label}
              </span>
            ))}
            <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8 }}>
              {lastUpdated && <span style={{ fontSize:9, fontFamily:'Share Tech Mono, monospace', color:'#3a5a78' }}>{lastUpdated}</span>}
              <button onClick={generateBriefing} disabled={loading} style={{ fontSize:9, fontFamily:'Share Tech Mono, monospace', background:'transparent', border:'1px solid rgba(0,200,255,0.2)', color:'#7aa8c8', padding:'2px 8px', borderRadius:2, cursor:'pointer' }}>↻ Refresh</button>
              <button onClick={() => setIsOpen(false)} style={{ fontSize:14, background:'transparent', border:'none', color:'#3a5a78', cursor:'pointer', padding:'0 4px' }}>✕</button>
            </div>
          </div>
          <div style={{
            fontFamily:'Exo 2, sans-serif', fontSize:13, lineHeight:1.7,
            color: loading ? '#3a5a78' : error ? '#ff3355' : '#e8f4ff',
            borderLeft:`3px solid ${dangerCount>0 ? '#ff3355' : '#00c8ff'}`,
            paddingLeft:14, maxWidth:1100,
          }}>
            {loading ? 'Analyzing fleet telemetry...' : error ? error : briefing}
          </div>
        </div>
      )}
      <style>{`@keyframes slideDown { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }`}</style>
    </>
  );
}