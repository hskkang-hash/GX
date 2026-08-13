import React, { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FaUsers } from 'react-icons/fa';

interface StatusInfoProps {
  isDrawingEnabled: boolean;
  isConnected: boolean;
  activeUsers: Set<{
    user: string;
    joined_at?: string;
    last_activity?: string;
    is_online?: boolean;
  }>;
  isRecording: boolean;
  droneCode: string;
  droneName: string;
  droneColor?: string;
  gridColumn?: number;
}

export const StatusInfo: React.FC<StatusInfoProps> = ({
  isDrawingEnabled,
  isConnected,
  activeUsers,
  isRecording,
  droneCode,
  droneName,
  droneColor = '#0CBA47',
  gridColumn,
}) => {
  const { t } = useTranslation();
  const participantsListRef = useRef<HTMLUListElement>(null);

  // Auto-scroll to bottom when new users join
  useEffect(() => {
    if (participantsListRef.current) {
      participantsListRef.current.scrollTo({
        top: participantsListRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [activeUsers.size]);

  if (!isDrawingEnabled) {
    return (
      <>
        {/* Drone Info - Top Left */}
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            backgroundColor: droneColor,
            color: '#fff',
            padding: '0.5rem 0.875rem',
            borderRadius: '0.5rem',
            fontSize: (gridColumn === 1 || gridColumn === 2) ? '1rem' : '0.875rem',
            fontWeight: '600',
            zIndex: 999,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            textTransform: 'uppercase',
          }}
        >
          {droneName}
        </div>

        {/* Connection Status */}
        {(isConnected || activeUsers.size >= 0) && (
          <div
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              backdropFilter: 'blur(8px)',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              zIndex: 999,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <FaUsers size={16} />
            <span>
              {activeUsers.size} {t('Participants')}
            </span>
          </div>
        )}
      </>
    );
  }
  console.log(activeUsers);
  return (
    <>
      {/* Drone Info in Drawing Mode */}
      <div
        style={{
          position: 'absolute',
          top: '1rem',
          left: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 11000,
        }}
      >
        <div
          style={{
            backgroundColor: '#D6F8E2',
            color: '#0CBA47',
            padding: '0.5rem 1rem',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <div
            style={{
              width: '10px',
              height: '10px',
              backgroundColor: '#0CBA47',
              borderRadius: '50%',
            }}
          />
          {droneName}
        </div>
      </div>

      {/* Participants - Bottom Right */}
      <div
        style={{
          position: 'absolute',
          bottom: '1rem',
          right: '1rem',
          backgroundColor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(8px)',
          color: 'black',
          padding: '1rem 2rem 1rem 0.875rem',
          borderRadius: '8px',
          fontSize: '12px',
          zIndex: 11000,
        }}
      >
        <div style={{ fontWeight: '600', fontSize: '1rem' }}>
          {t('Participants')}:
        </div>
        <ul
          ref={participantsListRef}
          style={{
            margin: 0,
            padding: 0,
            paddingLeft: '0.625rem',
            marginTop: '0.25rem',
            listStyle: 'none',
            maxHeight: '120px',
            overflowY: 'auto',
            scrollBehavior: 'smooth',
          }}
        >
          {Array.from(activeUsers).map((user, index) => (
            <li
              key={`${index}`}
              style={{
                padding: '4px 0',
                fontSize: '12px',
              }}
            >
              • {user?.user}
            </li>
          ))}
        </ul>
      </div>

      {/* ESC Hint - Bottom Right */}
      {/* <div
        style={{
          position: 'absolute',
          bottom: '1rem',
          right: '1rem',
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(8px)',
          color: 'rgba(255, 255, 255, 0.8)',
          padding: '8px 12px',
          borderRadius: '8px',
          fontSize: '12px',
          zIndex: 11000,
        }}
      >
        Press ESC to exit
      </div> */}
    </>
  );
};
