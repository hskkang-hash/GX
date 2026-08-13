import React from 'react';

interface AISettingsFormSkeletonProps {
  theme?: string;
  rowCount?: number;
}

const SkeletonBox: React.FC<{
  width?: string;
  height?: string;
  theme?: string;
}> = ({ width = '100%', height = '20px', theme = 'light' }) => (
  <div
    style={{
      width,
      height,
      backgroundColor: theme === 'dark' ? '#3C3D3E' : '#E5E7EB',
      borderRadius: '4px',
      background:
        theme === 'dark'
          ? 'linear-gradient(90deg, #3C3D3E 25%, #4B5563 50%, #3C3D3E 75%)'
          : 'linear-gradient(90deg, #E5E7EB 25%, #F3F4F6 50%, #E5E7EB 75%)',
      backgroundSize: '200% 100%',
      animation: 'skeleton-loading 1.5s ease-in-out infinite',
    }}
  />
);

export const AISettingsFormSkeleton: React.FC<AISettingsFormSkeletonProps> = ({
  theme = 'light',
  rowCount = 3,
}) => {
  return (
    <div
      style={{
        backgroundColor: theme === 'dark' ? '#1f1f20' : 'white',
        color: theme === 'dark' ? '#F9FAFB' : '#111827',
        borderRadius: '8px',
        gap: '1rem',
        paddingBottom: '0 !important',
      }}
    >
      <style>
        {`
          @keyframes skeleton-loading {
            0% {
              background-position: -200% 0;
            }
            100% {
              background-position: 200% 0;
            }
          }
        `}
      </style>

      {/* Table Skeleton */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        {/* Table Header Skeleton */}
        <thead>
          <tr
            style={{
              backgroundColor: theme === 'dark' ? '#2D2E30' : '#F8FAFC',
              border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
              borderRadius: '8px',
            }}
          >
            {/* Drag Handle Header */}
            <th
              style={{
                padding: '16px',
                textAlign: 'left',
                minWidth: '40px',
                borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
              }}
            >
              <SkeletonBox
                width="20px"
                height="16px"
                theme={theme}
              />
            </th>

            {/* Drone Header */}
            <th
              style={{
                padding: '16px',
                textAlign: 'left',
                minWidth: '120px',
                borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
              }}
            >
              <SkeletonBox
                width="60px"
                height="16px"
                theme={theme}
              />
            </th>

            {/* Stream URL Header */}
            <th
              style={{
                padding: '16px',
                textAlign: 'left',
                minWidth: '300px',
                borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
              }}
            >
              <SkeletonBox
                width="80px"
                height="16px"
                theme={theme}
              />
            </th>

            {/* AI Model Header */}
            <th
              style={{
                padding: '16px',
                textAlign: 'left',
                minWidth: '150px',
                borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
              }}
            >
              <SkeletonBox
                width="70px"
                height="16px"
                theme={theme}
              />
            </th>

            {/* Display Header */}
            <th style={{ padding: '16px', textAlign: 'center', width: '80px' }}>
              <SkeletonBox
                width="50px"
                height="16px"
                theme={theme}
              />
            </th>
          </tr>
        </thead>

        {/* Table Body Skeleton */}
        <tbody>
          {Array.from({ length: rowCount }, (_, index) => (
            <tr
              key={index}
              style={{
                border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E5E7EB'}`,
                backgroundColor: theme === 'dark' ? '#1f1f20' : 'white',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              }}
            >
              {/* Drag Handle Cell */}
              <td
                style={{
                  padding: '16px',
                  textAlign: 'center',
                  minWidth: '40px',
                  borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                }}
              >
                <SkeletonBox
                  width="24px"
                  height="24px"
                  theme={theme}
                />
              </td>

              {/* Drone Name Cell */}
              <td
                style={{
                  padding: '16px',
                  minWidth: '120px',
                  borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                }}
              >
                <SkeletonBox
                  width={`${80 + Math.random() * 40}px`}
                  height="20px"
                  theme={theme}
                />
              </td>

              {/* Stream URL Cell */}
              <td
                style={{
                  padding: '16px',
                  minWidth: '200px',
                  borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                }}
              >
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                    backgroundColor: theme === 'dark' ? '#2a2a2a' : '#F9FAFB',
                  }}
                >
                  <SkeletonBox
                    width="100%"
                    height="20px"
                    theme={theme}
                  />
                </div>
              </td>

              {/* AI Model Dropdown Cell */}
              <td
                style={{
                  padding: '16px',
                  minWidth: '150px',
                  borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                }}
              >
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                    backgroundColor: theme === 'dark' ? '#2a2a2a' : '#F9FAFB',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <SkeletonBox
                    width="80%"
                    height="20px"
                    theme={theme}
                  />
                  <SkeletonBox
                    width="12px"
                    height="12px"
                    theme={theme}
                  />
                </div>
              </td>

              {/* Display Toggle Cell */}
              <td
                style={{
                  padding: '16px',
                  textAlign: 'center',
                  minWidth: '100px',
                }}
              >
                <SkeletonBox
                  width="18px"
                  height="18px"
                  theme={theme}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Action Buttons Skeleton */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'center',
          marginTop: '24px',
        }}
      >
        <SkeletonBox
          width="100px"
          height="44px"
          theme={theme}
        />
        <SkeletonBox
          width="100px"
          height="44px"
          theme={theme}
        />
      </div>
    </div>
  );
};
