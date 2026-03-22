import { useState, useEffect, useRef, useCallback } from 'react';

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

export function useSimControl() {
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
      return json;
    } catch (e) {
      console.error('Sim step error:', e);
    } finally {
      setStepping(false);
    }
  }, []);

  return { step, stepping };
}

export function useManeuverHistory() {
  const [history, setHistory] = useState([]);

  const addManeuver = useCallback((maneuver) => {
    setHistory(prev => [{
      ...maneuver,
      timestamp: new Date().toISOString(),
      id: Date.now(),
    }, ...prev].slice(0, 50));
  }, []);

  return { history, addManeuver };
}