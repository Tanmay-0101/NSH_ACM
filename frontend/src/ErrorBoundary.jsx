import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  componentDidCatch(error, info) {
    this.setState({ error, info });
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: 32,
          fontFamily: 'Share Tech Mono, monospace',
          fontSize: 12,
          color: '#ff3355',
          background: '#020408',
          minHeight: '100vh',
        }}>
          <div style={{ color: '#00c8ff', fontSize: 16, marginBottom: 16 }}>
            ORBITAL INSIGHT — RENDER ERROR
          </div>
          <div style={{ marginBottom: 12, color: '#ffaa00' }}>
            {this.state.error.toString()}
          </div>
          <pre style={{
            background: '#0a1520',
            padding: 16,
            borderRadius: 4,
            color: '#7aa8c8',
            fontSize: 11,
            overflow: 'auto',
            border: '1px solid rgba(0,200,255,0.1)',
          }}>
            {this.state.info?.componentStack}
          </pre>
          <button
            onClick={() => this.setState({ error: null, info: null })}
            style={{
              marginTop: 16,
              padding: '8px 20px',
              background: 'rgba(0,200,255,0.1)',
              border: '1px solid rgba(0,200,255,0.4)',
              color: '#00c8ff',
              fontFamily: 'Rajdhani, sans-serif',
              fontSize: 13,
              cursor: 'pointer',
              borderRadius: 2,
            }}
          >
            RETRY
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}