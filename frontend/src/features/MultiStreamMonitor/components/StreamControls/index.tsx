import React from 'react';
import { FiMonitor, FiWifi } from 'react-icons/fi';
import { MdHd, MdNetworkCheck } from 'react-icons/md';
import { SiWebrtc } from 'react-icons/si';

import { StreamProtocol, StreamQuality } from '../../hooks/useDynamicStream';

interface StreamControlsProps {
  currentProtocol: StreamProtocol;
  currentQuality: StreamQuality;
  isConnected: boolean;
  isLoading: boolean;
  connectionMetrics: {
    latency: number;
    bandwidth: number;
    packetLoss: number;
    connectionStability: number;
  };
  canSwitchToWebRTC: boolean;
  canSwitchToHLS: boolean;
  onProtocolSwitch: (protocol: StreamProtocol) => void;
  onQualityChange: (quality: StreamQuality) => void;
  className?: string;
}

const StreamControlsComponent: React.FC<StreamControlsProps> = ({
  currentProtocol,
  currentQuality,
  isConnected,
  isLoading,
  connectionMetrics,
  canSwitchToWebRTC,
  canSwitchToHLS,
  onProtocolSwitch,
  onQualityChange,
  className = '',
}) => {
  const getProtocolIcon = (protocol: StreamProtocol) => {
    switch (protocol) {
      case 'webrtc':
        return <SiWebrtc size={14} />;
      case 'hls':
        return <FiMonitor size={14} />;
      case 'auto':
        return <MdNetworkCheck size={14} />;
      default:
        return <FiWifi size={14} />;
    }
  };

  const getQualityIcon = (quality: StreamQuality) => {
    switch (quality) {
      case 'high':
        return <MdHd size={14} />;
      case 'medium':
        return <FiMonitor size={14} />;
      case 'low':
        return <FiWifi size={14} />;
      default:
        return <MdHd size={14} />;
    }
  };

  const getConnectionColor = () => {
    if (!isConnected && isLoading) return '#ffa500'; // Orange for loading
    if (!isConnected) return '#dc3545'; // Red for disconnected
    if (connectionMetrics.connectionStability > 80) return '#28a745'; // Green for good
    if (connectionMetrics.connectionStability > 60) return '#ffc107'; // Yellow for fair
    return '#dc3545'; // Red for poor
  };

  const formatLatency = (latency: number) => {
    return `${Math.round(latency)}ms`;
  };

  const formatBandwidth = (bandwidth: number) => {
    if (bandwidth < 1) return `${Math.round(bandwidth * 1000)}kbps`;
    return `${bandwidth.toFixed(1)}Mbps`;
  };

  const formatPacketLoss = (packetLoss: number) => {
    return `${packetLoss.toFixed(1)}%`;
  };

  return (
    <div className={`stream-controls ${className}`}>
      {/* Connection Status Indicator */}
      <div className="connection-status">
        <div
          className="status-dot"
          style={{
            backgroundColor: getConnectionColor(),
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            marginRight: '6px',
            animation: isLoading ? 'pulse 1.5s infinite' : 'none',
          }}
        />
        <span className="status-text">
          {isLoading
            ? 'Connecting...'
            : isConnected
              ? 'Connected'
              : 'Disconnected'}
        </span>
      </div>

      {/* Protocol Selector */}
      <div className="protocol-selector">
        <label className="selector-label">Protocol:</label>
        <div className="button-group">
          <button
            className={`protocol-btn ${currentProtocol === 'auto' ? 'active' : ''}`}
            onClick={() => onProtocolSwitch('auto')}
            title="Auto-select best protocol"
          >
            {getProtocolIcon('auto')}
            Auto
          </button>
          {canSwitchToHLS && (
            <button
              className={`protocol-btn ${currentProtocol === 'hls' ? 'active' : ''}`}
              onClick={() => onProtocolSwitch('hls')}
              title="HTTP Live Streaming"
            >
              {getProtocolIcon('hls')}
              HLS
            </button>
          )}
          {canSwitchToWebRTC && (
            <button
              className={`protocol-btn ${currentProtocol === 'webrtc' ? 'active' : ''}`}
              onClick={() => onProtocolSwitch('webrtc')}
              title="WebRTC Real-time Communication"
            >
              {getProtocolIcon('webrtc')}
              WebRTC
            </button>
          )}
        </div>
      </div>

      {/* Quality Selector */}
      <div className="quality-selector">
        <label className="selector-label">Quality:</label>
        <div className="button-group">
          {(['high', 'medium', 'low'] as StreamQuality[]).map((quality) => (
            <button
              key={quality}
              className={`quality-btn ${currentQuality === quality ? 'active' : ''}`}
              onClick={() => onQualityChange(quality)}
              title={`${quality.charAt(0).toUpperCase() + quality.slice(1)} quality`}
            >
              {getQualityIcon(quality)}
              {quality.charAt(0).toUpperCase() + quality.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Connection Metrics */}
      <div className="connection-metrics">
        <div className="metrics-grid">
          <div className="metric">
            <span className="metric-label">Latency:</span>
            <span className="metric-value">
              {formatLatency(connectionMetrics.latency)}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Bandwidth:</span>
            <span className="metric-value">
              {formatBandwidth(connectionMetrics.bandwidth)}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Loss:</span>
            <span className="metric-value">
              {formatPacketLoss(connectionMetrics.packetLoss)}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Stability:</span>
            <span className="metric-value">
              {Math.round(connectionMetrics.connectionStability)}%
            </span>
          </div>
        </div>
      </div>

      <style jsx>{`
        .stream-controls {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 12px;
          background: rgba(0, 0, 0, 0.8);
          border-radius: 8px;
          color: white;
          font-size: 12px;
          min-width: 200px;
        }

        .connection-status {
          display: flex;
          align-items: center;
          font-weight: 500;
        }

        .status-text {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .protocol-selector,
        .quality-selector {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .selector-label {
          font-size: 10px;
          text-transform: uppercase;
          font-weight: 600;
          color: #ccc;
          letter-spacing: 0.5px;
        }

        .button-group {
          display: flex;
          gap: 4px;
        }

        .protocol-btn,
        .quality-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 8px;
          border: 1px solid #444;
          background: rgba(255, 255, 255, 0.1);
          color: #ccc;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 10px;
          text-transform: uppercase;
          font-weight: 500;
          letter-spacing: 0.3px;
        }

        .protocol-btn:hover,
        .quality-btn:hover {
          background: rgba(255, 255, 255, 0.2);
          color: white;
          border-color: #666;
        }

        .protocol-btn.active,
        .quality-btn.active {
          background: #007bff;
          border-color: #0056b3;
          color: white;
        }

        .connection-metrics {
          border-top: 1px solid #444;
          padding-top: 8px;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 6px;
        }

        .metric {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .metric-label {
          font-size: 10px;
          color: #999;
          text-transform: uppercase;
          font-weight: 500;
        }

        .metric-value {
          font-size: 10px;
          font-weight: 600;
          color: #ccc;
        }

        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        /* Responsive design */
        @media (max-width: 768px) {
          .stream-controls {
            min-width: 180px;
            padding: 10px;
            font-size: 11px;
          }

          .button-group {
            flex-wrap: wrap;
          }

          .protocol-btn,
          .quality-btn {
            padding: 5px 6px;
            font-size: 9px;
          }
        }
      `}</style>
    </div>
  );
};

// Memoize the component to prevent unnecessary re-renders
export const StreamControls = React.memo(
  StreamControlsComponent,
  (prevProps, nextProps) => {
    // Custom comparison to prevent re-renders unless significant changes occur
    return (
      prevProps.currentProtocol === nextProps.currentProtocol &&
      prevProps.currentQuality === nextProps.currentQuality &&
      prevProps.isConnected === nextProps.isConnected &&
      prevProps.isLoading === nextProps.isLoading &&
      prevProps.canSwitchToWebRTC === nextProps.canSwitchToWebRTC &&
      prevProps.canSwitchToHLS === nextProps.canSwitchToHLS &&
      Math.abs(
        prevProps.connectionMetrics.latency -
          nextProps.connectionMetrics.latency,
      ) < 10 &&
      Math.abs(
        prevProps.connectionMetrics.bandwidth -
          nextProps.connectionMetrics.bandwidth,
      ) < 5 &&
      Math.abs(
        prevProps.connectionMetrics.packetLoss -
          nextProps.connectionMetrics.packetLoss,
      ) < 0.5 &&
      Math.abs(
        prevProps.connectionMetrics.connectionStability -
          nextProps.connectionMetrics.connectionStability,
      ) < 5
    );
  },
);
