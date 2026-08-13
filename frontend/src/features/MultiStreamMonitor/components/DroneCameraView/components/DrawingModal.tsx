import React from 'react';

import { DrawingControls } from './DrawingControls';
import { StatusInfo } from './StatusInfo';
import { VideoControls } from './VideoControls';

interface DrawingModalProps {
  isDrawingEnabled: boolean;
  drawingMode: 'pen' | 'eraser' | 'shape';
  shapeType: 'rectangle' | 'circle' | 'oval' | 'line';
  brushSize: number;
  brushColor: string;
  showShapeOptions: boolean;
  isRecording: boolean;
  isConnected: boolean;
  activeUsers: Set<{
    user: string;
    joined_at?: string;
    last_activity?: string;
    is_online?: boolean;
  }>;
  droneCode: string;
  droneName: string;
  onToggleDrawing: () => void;
  onDrawingModeChange: (mode: 'pen' | 'eraser' | 'shape') => void;
  onShapeTypeChange: (type: 'rectangle' | 'circle' | 'oval' | 'line') => void;
  onBrushSizeChange: (size: number) => void;
  onBrushColorChange: (color: string) => void;
  onShowShapeOptionsChange: (show: boolean) => void;
  onToggleRecording: () => void;
  onCaptureFrame: () => void;
  onClearCanvas: () => void;
  onClose: () => void;
  children: React.ReactNode;
}

export const DrawingModal: React.FC<DrawingModalProps> = ({
  isDrawingEnabled,
  drawingMode,
  shapeType,
  brushSize,
  brushColor,
  showShapeOptions,
  isRecording,
  isConnected,
  activeUsers,
  droneCode,
  droneName,
  onToggleDrawing,
  onDrawingModeChange,
  onShapeTypeChange,
  onBrushSizeChange,
  onBrushColorChange,
  onShowShapeOptionsChange,
  onToggleRecording,
  onCaptureFrame,
  onClearCanvas,
  onClose,
  children,
}) => {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
    >
      {/* Close Button */}
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          width: '40px',
          height: '40px',
          backgroundColor: 'transparent',
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          fontSize: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          backdropFilter: 'blur(8px)',
          cursor: 'pointer',
          zIndex: 9999,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        }}
        title="Close Drawing Mode"
      >
        ✕
      </button>

      {/* Main Content */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '80px 20px 100px 20px',
        }}
      >
        {/* Video Stream Container */}
        <div
          className="video-wrapper"
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
          }}
        >
          {children}

          <StatusInfo
            isDrawingEnabled={isDrawingEnabled}
            isConnected={isConnected}
            activeUsers={activeUsers}
            isRecording={isRecording}
            droneCode={droneCode}
            droneName={droneName}
          />

          <DrawingControls
            isDrawingEnabled={isDrawingEnabled}
            drawingMode={drawingMode}
            shapeType={shapeType}
            brushSize={brushSize}
            brushColor={brushColor}
            showShapeOptions={showShapeOptions}
            onToggleDrawing={onToggleDrawing}
            onDrawingModeChange={onDrawingModeChange}
            onShapeTypeChange={onShapeTypeChange}
            onBrushSizeChange={onBrushSizeChange}
            onBrushColorChange={onBrushColorChange}
            onShowShapeOptionsChange={onShowShapeOptionsChange}
            onClearCanvas={onClearCanvas}
          />

          <VideoControls
            isRecording={isRecording}
            onToggleRecording={onToggleRecording}
            onCaptureFrame={onCaptureFrame}
          />
        </div>
      </div>
    </div>
  );
};
