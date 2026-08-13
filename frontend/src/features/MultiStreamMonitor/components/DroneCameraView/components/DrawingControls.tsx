import React, { useState } from 'react';
import {
  BsBorderWidth,
  BsEraser,
  BsPencil,
  BsSquare,
  BsTrash,
} from 'react-icons/bs';
import { GiStraightPipe } from 'react-icons/gi';
import { TbOvalVertical } from 'react-icons/tb';

interface DrawingControlsProps {
  isDrawingEnabled: boolean;
  drawingMode: 'pen' | 'eraser' | 'shape';
  shapeType: 'rectangle' | 'circle' | 'oval' | 'line';
  brushSize: number;
  brushColor: string;
  showShapeOptions: boolean;
  onToggleDrawing: () => void;
  onDrawingModeChange: (mode: 'pen' | 'eraser' | 'shape') => void;
  onShapeTypeChange: (type: 'rectangle' | 'circle' | 'oval' | 'line') => void;
  onBrushSizeChange: (size: number) => void;
  onBrushColorChange: (color: string) => void;
  onShowShapeOptionsChange: (show: boolean) => void;
  onClearCanvas: () => void;
}

export const DrawingControls: React.FC<DrawingControlsProps> = ({
  isDrawingEnabled,
  drawingMode,
  shapeType,
  brushSize,
  brushColor,
  showShapeOptions,
  onToggleDrawing,
  onDrawingModeChange,
  onShapeTypeChange,
  onBrushSizeChange,
  onBrushColorChange,
  onShowShapeOptionsChange,
  onClearCanvas,
}) => {
  const [showBrushSizeOptions, setShowBrushSizeOptions] = useState(false);

  const colorOpacity = (color: string, opacity: number) => {
    if (color.startsWith('#')) {
      const hex = color.slice(1);
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }
    return color;
  };

  const handleShapeToolClick = () => {
    if (drawingMode === 'shape') {
      onShowShapeOptionsChange(!showShapeOptions);
    } else {
      onDrawingModeChange('shape');
      onShowShapeOptionsChange(true);
    }
  };

  const handleShapeSelect = (
    type: 'rectangle' | 'circle' | 'oval' | 'line',
  ) => {
    onShapeTypeChange(type);
    onShowShapeOptionsChange(false);
  };

  const handleBrushSizeClick = () => {
    setShowBrushSizeOptions(!showBrushSizeOptions);
  };

  const handleBrushSizeSelect = (size: number) => {
    onBrushSizeChange(size);
    setShowBrushSizeOptions(false);
  };

  // Predefined brush sizes
  const brushSizes = [1, 3, 5, 8, 10, 12, 14, 16];

  if (!isDrawingEnabled) {
    return (
      <div
        style={{
          position: 'absolute',
          bottom: '10px',
          right: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          zIndex: 2000,
        }}
      >
        <button
          onClick={onToggleDrawing}
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            color: '#374151',
            border: 'none',
            borderRadius: '50%',
            cursor: 'pointer',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
            backdropFilter: 'blur(8px)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title="Enable Drawing"
        >
          <BsPencil />
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '1rem',
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: colorOpacity('#ffffff', 0.8),
        backdropFilter: 'blur(12px)',
        padding: '0.375rem',
        borderRadius: '0.625rem',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        zIndex: 11000,
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
      }}
    >
      {/* Pen Tool */}
      <button
        onClick={() => {
          onDrawingModeChange('pen');
          onShowShapeOptionsChange(false);
        }}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: drawingMode === 'pen' ? 'white' : 'transparent',
          color: drawingMode === 'pen' ? '#3B82F6' : '#374151',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          fontSize: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
        }}
        title="Pen Tool"
      >
        <BsPencil />
      </button>

      {/* Shape Tool with Dropdown */}
      <div style={{ position: 'relative' }}>
        <button
          onClick={handleShapeToolClick}
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: drawingMode === 'shape' ? 'white' : 'transparent',
            color: drawingMode === 'shape' ? '#3B82F6' : '#374151',
            border: 'none',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
          }}
          title="Shape Tools"
        >
          {drawingMode === 'shape' ? (
            shapeType === 'rectangle' ? (
              <BsSquare />
            ) : shapeType === 'oval' ? (
              <TbOvalVertical />
            ) : shapeType === 'line' ? (
              '📏'
            ) : (
              <BsSquare />
            )
          ) : (
            <BsSquare />
          )}
        </button>

        {/* Shape Options Dropdown */}
        {showShapeOptions && (
          <div
            style={{
              position: 'absolute',
              bottom: '60px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: 'rgba(255, 255, 255, 0.98)',
              backdropFilter: 'blur(12px)',
              padding: '12px',
              borderRadius: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              zIndex: 12000,
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
            }}
          >
            {/* <button
              onClick={() => handleShapeSelect('rectangle')}
              style={{
                padding: '10px 16px',
                backgroundColor: shapeType === 'rectangle' ? 'var(--ga-primary)' : 'transparent',
                color: shapeType === 'rectangle' ? 'white' : '#374151',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease',
              }}
            >
              <BsSquare />
            </button> */}
            <button
              onClick={() => handleShapeSelect('oval')}
              style={{
                padding: '10px 16px',
                backgroundColor:
                  shapeType === 'oval' ? 'var(--ga-primary)' : 'transparent',
                color: shapeType === 'oval' ? 'white' : '#374151',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease',
              }}
            >
              <TbOvalVertical />
            </button>
            <button
              onClick={() => handleShapeSelect('line')}
              style={{
                padding: '10px 16px',
                backgroundColor:
                  shapeType === 'line' ? 'var(--ga-primary)' : 'transparent',
                color: shapeType === 'line' ? 'white' : '#374151',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease',
              }}
            >
              <GiStraightPipe />
            </button>
          </div>
        )}
      </div>

      {/* Color Picker */}
      {(drawingMode === 'pen' || drawingMode === 'shape') && (
        <input
          type="color"
          value={brushColor}
          onChange={(e) => onBrushColorChange(e.target.value)}
          style={{
            width: '26px',
            height: '26px',
            border: '2px solid #E5E7EB',
            borderRadius: '50%',
            cursor: 'pointer',
            background: 'none',
            padding: '0',
          }}
          title="Color Picker"
        />
      )}

      {/* Brush Size Button with Dropdown */}
      {(drawingMode === 'pen' || drawingMode === 'eraser') && (
        <div style={{ position: 'relative' }}>
          <button
            onClick={handleBrushSizeClick}
            style={{
              width: '32px',
              height: '32px',
              backgroundColor: showBrushSizeOptions ? 'white' : 'transparent',
              color: showBrushSizeOptions ? '#3B82F6' : '#374151',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
              fontWeight: 'bold',
            }}
            title="Brush Size"
          >
            <BsBorderWidth size={20} />
          </button>

          {/* Brush Size Options Dropdown */}
          {showBrushSizeOptions && (
            <div
              style={{
                position: 'absolute',
                bottom: '60px',
                left: '50%',
                transform: 'translateX(-50%)',
                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                backdropFilter: 'blur(12px)',
                padding: '12px',
                borderRadius: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                zIndex: 12000,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                minWidth: '80px',
              }}
            >
              {brushSizes.map((size) => (
                <button
                  key={size}
                  onClick={() => handleBrushSizeSelect(size)}
                  style={{
                    padding: '8px 12px',
                    backgroundColor:
                      brushSize === size ? '#3B82F6' : 'transparent',
                    color: brushSize === size ? 'white' : '#374151',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {size}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Eraser Tool */}
      <button
        onClick={() => {
          onDrawingModeChange('eraser');
          onShowShapeOptionsChange(false);
        }}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: drawingMode === 'eraser' ? 'white' : 'transparent',
          color: drawingMode === 'eraser' ? '#3B82F6' : '#374151',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          fontSize: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
        }}
        title="Eraser Tool"
      >
        <BsEraser />
      </button>

      {/* Erase All Tool */}
      <button
        onClick={onClearCanvas}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: 'transparent',
          color: '#EF4444',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          fontSize: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
        title="Erase All Drawings"
      >
        <BsTrash />
      </button>
    </div>
  );
};
