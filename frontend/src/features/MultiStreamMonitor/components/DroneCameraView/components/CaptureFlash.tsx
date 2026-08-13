import React, { useEffect, useState } from 'react';

interface CaptureFlashProps {
  isVisible: boolean;
  onComplete?: () => void;
}

export const CaptureFlash: React.FC<CaptureFlashProps> = ({
  isVisible,
  onComplete,
}) => {
  const [showFlash, setShowFlash] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setShowFlash(true);

      // Hide flash after animation
      const timer = setTimeout(() => {
        setShowFlash(false);
        if (onComplete) {
          onComplete();
        }
      }, 200); // Flash duration

      return () => clearTimeout(timer);
    }
  }, [isVisible, onComplete]);

  if (!showFlash) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'var(--ga-primary)',
        opacity: showFlash ? 0.6 : 0,
        zIndex: 1000,
        pointerEvents: 'none',
        transition: 'opacity 0.2s ease-out',
        animation: 'captureFlash 0.2s ease-out',
      }}
    >
      <style>{`
        @keyframes captureFlash {
          0% {
            opacity: 0;
          }
          50% {
            opacity: 0.65;
          }
          100% {
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};
