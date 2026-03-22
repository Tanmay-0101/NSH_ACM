import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function useSnapshot(intervalMs = 1000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchSnapshot() {
      try {
        const res = await fetch(`${API_BASE}/api/visualization/snapshot`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setConnected(true);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message);
          setConnected(false);
        }
      }
    }

    fetchSnapshot();
    const id = setInterval(fetchSnapshot, intervalMs);
    return () => { cancelled = true; clearInterval(id); };
  }, [intervalMs]);

  return { data, error, connected };
}

export function useManeuverHistory() {
  const [history, setHistory] = useState([]);

  // Called by useSimControl after each step with the full step response
  const addFromStepResponse = useCallback((stepResponse) => {
    if (!stepResponse) return;

    const burnReports = stepResponse.burn_reports || [];
    const simTime = stepResponse.new_timestamp || new Date().toISOString();

    const newEntries = burnReports
      .filter(r => r.success)
      .map(r => {
        const burnId = r.burn_id || '';
        // Determine type from burn_id name
        const type = burnId.includes('RECOVERY') ? 'RECOVERY'
          : burnId.includes('EVASION')  ? 'EVASION'
          : burnId.includes('GRAVEYARD') ? 'EOL'
          : 'STATION';

        return {
          id:          `${burnId}_${Date.now()}`,
          burnId:      burnId,
          satId:       r.satellite_id || '—',
          type:        type,
          status:      r.success ? 'EXECUTED' : 'FAILED',
          timestamp:   simTime,
          fuelLeft:    r.fuel_remaining_kg,
          isAuto:      burnId.startsWith('AUTO_'),
        };
      });

    if (newEntries.length > 0) {
      setHistory(prev => [...newEntries, ...prev].slice(0, 100));
    }
  }, []);

  return { history, addFromStepResponse };
}

export function useSimControl(onStepComplete) {
  const [stepping, setStepping] = useState(false);

  const step = useCallback(async (seconds = 60) => {
    setStepping(true);
    try {
      const res = await fetch(`${API_BASE}/api/simulate/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_seconds: seconds }),
      });
      const json = await res.json();
      // Fire callback so App.jsx can forward to maneuver history
      if (onStepComplete) onStepComplete(json);
      return json;
    } catch (e) {
      console.error('Sim step error:', e);
    } finally {
      setStepping(false);
    }
  }, [onStepComplete]);

  return { step, stepping };
}