import { IconButton, Skeleton } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { IoChevronBack, IoChevronForward } from 'react-icons/io5';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import { RegionDrone } from '../hooks/useSurveillanceDashboard';

interface RegionDronesListProps {
  data: RegionDrone[] | null;
  isLoading?: boolean;
  // Pagination props
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  isLoadingPage?: boolean;
}

const RegionDronesList: React.FC<RegionDronesListProps> = ({
  data,
  isLoading = false,
  currentPage = 1,
  totalPages = 1,
  onPageChange,
  isLoadingPage = false,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const statusColorByCode: Record<string, string> = {
    available: '#2ECC71',
    on_mission: '#F39C12',
    warning: '#E74C3C',
    inactive: '#9E9E9E',
  };

  const getStatusColor = (statusCode?: string) =>
    statusCode ? statusColorByCode[statusCode] || '#9E9E9E' : '#9E9E9E';

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          gap: '1rem',
          paddingBottom: '1rem',
          overflowX: 'auto',
        }}
      >
        {[1, 2, 3, 4].map((i) => (
          <Skeleton
            key={i}
            variant="rectangular"
            width={300}
            height={150}
            sx={{
              borderRadius: '0.75rem',
              flexShrink: 0,
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.05)',
            }}
          />
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: theme === 'dark' ? Colors.Gray5 : '#999',
          minHeight: '150px',
        }}
      >
        {t('SurveillanceDashboard.No drones data')}
      </div>
    );
  }

  // Handler for previous page
  const handlePrevPage = () => {
    if (currentPage > 1 && onPageChange) {
      onPageChange(currentPage - 1);
    }
  };

  // Handler for next page
  const handleNextPage = () => {
    if (currentPage < totalPages && onPageChange) {
      onPageChange(currentPage + 1);
    }
  };

  const hasPagination = totalPages > 1;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: '0.5rem',
        height: '100%',
      }}
    >
      {/* Region cards grid */}
      <div
        className="region-drones-scroll"
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr 1fr',
          gap: '1rem',
          paddingBottom: '0.5rem',
          height: '100%',
          flex: 1,
          opacity: isLoadingPage ? 0.6 : 1,
          transition: 'opacity 0.2s ease',
        }}
      >
        {data.map((region, regionIndex) => (
        <div
          className="region-drone-scroll"
          key={`region-${regionIndex}`}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            padding: '1rem',
            borderRadius: '0.75rem',
            backgroundColor: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
            overflowX: 'auto',
          }}
        >
          <style>
            {`
            .region-drone-scroll::-webkit-scrollbar {
              height: 8px;
            }
            .region-drone-scroll::-webkit-scrollbar-track {
              background: ${theme === 'dark' ? '#2D2E30' : '#F0F0F0'};
              border-radius: 4px;
            }
            .region-drone-scroll::-webkit-scrollbar-thumb {
              background: ${theme === 'dark' ? '#4D4E50' : '#C0C0C0'};
              border-radius: 4px;
            }
            .region-drone-scroll::-webkit-scrollbar-thumb:hover {
              background: ${theme === 'dark' ? '#5D5E60' : '#A0A0A0'};
            }
          `}
          </style>
          {/* Region Header */}
          <div
            style={{
              fontSize: '1rem',
              fontWeight: 600,
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              marginBottom: '0.5rem',
            }}
          >
            {region.region}
          </div>

          {/* Drones - Horizontal Scroll */}
          {region.drones && region.drones.length > 0 ? (
            <div
              className="region-drones-horizontal-scroll"
              style={{
                display: 'flex',
                gap: '0.5rem',
                overflowX: 'auto',
                paddingBottom: '0.5rem',
              }}
            >
              <style>
                {`
              .region-drones-horizontal-scroll::-webkit-scrollbar {
                height: 8px;
              }
              .region-drones-horizontal-scroll::-webkit-scrollbar-track {
                background: ${theme === 'dark' ? '#2D2E30' : '#F0F0F0'};
                border-radius: 4px;
              }
              .region-drones-horizontal-scroll::-webkit-scrollbar-thumb {
                background: ${theme === 'dark' ? '#4D4E50' : '#C0C0C0'};
                border-radius: 4px;
              }
              .region-drones-horizontal-scroll::-webkit-scrollbar-thumb:hover {
                background: ${theme === 'dark' ? '#5D5E60' : '#A0A0A0'};
              }
            `}
              </style>
              {region.drones.map((drone, droneIndex) => (
                <div
                  key={drone.device_id}
                  style={{
                    minWidth: '140px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '0.5rem',
                    border: `2px solid ${drone.color}`,
                    background: 'transparent',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    flexShrink: 0,
                  }}
                >
                  {/* Colored Indicator */}
                  <div
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: getStatusColor(drone.status_code),
                      flexShrink: 0,
                    }}
                  />

                  {/* Drone Code/Name */}
                  <span
                    style={{
                      fontSize: '0.875rem',
                      fontWeight: 500,
                      color: theme === 'dark' ? '#FFF' : '#333',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {drone.device_name || drone.serial_number}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div
              style={{
                fontSize: '0.875rem',
                color: theme === 'dark' ? Colors.Gray5 : '#999',
                fontStyle: 'italic',
                padding: '1rem',
                textAlign: 'center',
              }}
            >
              {t('SurveillanceDashboard.No drones data')}
            </div>
          )}
        </div>
      ))}
      </div>

      {/* Pagination controls - only show when there are multiple pages */}
      {hasPagination && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: '0.25rem',
          }}
        >
          {/* Previous button */}
          <IconButton
            onClick={handlePrevPage}
            disabled={currentPage <= 1 || isLoadingPage}
            size="small"
            sx={{
              width: 32,
              height: 32,
              border: `1px solid ${theme === 'dark' ? '#4D4E50' : '#E0E0E0'}`,
              borderRadius: '50%',
              backgroundColor: theme === 'dark' ? '#2D2E30' : '#FFFFFF',
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              '&:hover': {
                backgroundColor: theme === 'dark' ? '#3D3E40' : '#F5F5F5',
              },
              '&:disabled': {
                opacity: 0.4,
                color: theme === 'dark' ? Colors.Gray5 : '#999',
              },
            }}
          >
            <IoChevronBack size={16} />
          </IconButton>

          {/* Next button */}
          <IconButton
            onClick={handleNextPage}
            disabled={currentPage >= totalPages || isLoadingPage}
            size="small"
            sx={{
              width: 32,
              height: 32,
              border: `1px solid ${theme === 'dark' ? '#4D4E50' : '#E0E0E0'}`,
              borderRadius: '50%',
              backgroundColor: theme === 'dark' ? '#2D2E30' : '#FFFFFF',
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              '&:hover': {
                backgroundColor: theme === 'dark' ? '#3D3E40' : '#F5F5F5',
              },
              '&:disabled': {
                opacity: 0.4,
                color: theme === 'dark' ? Colors.Gray5 : '#999',
              },
            }}
          >
            <IoChevronForward size={16} />
          </IconButton>
        </div>
      )}
    </div>
  );
};

export default RegionDronesList;
