import { Box, IconButton } from '@mui/material';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Control } from 'react-hook-form';
import { BsCalendar } from 'react-icons/bs';
import { useTheme } from 'rj-core';

import Colors, { border as borderColor, textLabel } from '@/configs/Colors';

import DateRangeQuickSelect from '../Form/DateRangeQuickSelect';
import './styles.scss';

interface QuickDateRangeBtnProps {
  // For form control usage (like CustomDateRangePicker)
  fromName?: string;
  toName?: string;
  control?: Control<any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  format?: string;
  placeholder?: [string, string];
  heightForDashboard?: boolean;

  // For callback usage
  onDateRangeChange?: (dateRange: {
    start_date: string;
    end_date: string;
  }) => void;
  positionForDashboard?: boolean;
}

export default function QuickDateRangeBtn({
  fromName,
  toName,
  control,
  format = 'MM-DD-YYYY',
  placeholder,
  heightForDashboard = false,
  positionForDashboard = false,
  onDateRangeChange,
}: QuickDateRangeBtnProps) {
  const [theme] = useTheme();
  const [showDateRangeModal, setShowDateRangeModal] = useState(false);
  const [modalPosition, setModalPosition] = useState({ top: 0, left: 0 });

  const btnRef = useRef<HTMLButtonElement>(null);

  const calculateModalPosition = useCallback(() => {
    if (btnRef.current) {
      const buttonRect = btnRef.current.getBoundingClientRect();
      setModalPosition({
        top: buttonRect.bottom + 16,
        left: buttonRect.left + btnRef.current?.offsetWidth / 2,
      });
    }
  }, []);

  const toggleDateRangeModal = () => {
    setShowDateRangeModal((prev) => !prev);
  };

  const handleDateRangeChange = (dateRange: {
    start_date: string;
    end_date: string;
  }) => {
    // Call the original callback
    onDateRangeChange?.(dateRange);

    // Close modal after selection
    setShowDateRangeModal(false);
  };

  useEffect(() => {
    if (showDateRangeModal) {
      calculateModalPosition();
    }
  }, [showDateRangeModal, calculateModalPosition]);
  return (
    <div
      id="quick-date-range-btn-container"
      data-theme={theme === 'dark' ? 'dark' : 'light'}
    >
      <IconButton
        ref={btnRef}
        size="small"
        sx={{
          border: `1px solid ${borderColor[theme === 'dark' ? 'dark' : 'light']}`,
          borderRadius: '0.25rem',
          opacity: 1,
          color: textLabel[theme === 'dark' ? 'dark' : 'light'],
          '&:hover': {
            color:
              theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
          },
        }}
        onClick={() => {
          toggleDateRangeModal();
        }}
      >
        <BsCalendar
          style={{ fontSize: '1.2rem' }}
          color={
            showDateRangeModal
              ? theme === 'dark'
                ? 'var(--ga-primary-dark)'
                : 'var(--ga-primary)'
              : textLabel[theme === 'dark' ? 'dark' : 'light']
          }
        />
      </IconButton>

      {showDateRangeModal && (
        <Box
          className="quick-date-range-modal"
          onClick={() => setShowDateRangeModal(false)}
        >
          <Box
            className={`quick-date-range-modal-content ${positionForDashboard ? 'quick-date-range-modal-content-for-surveillance-dashboard' : ''}`}
            sx={{
              top: modalPosition.top,
              left: modalPosition.left,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <DateRangeQuickSelect
              fromName={fromName}
              toName={toName}
              control={control}
              format={format}
              placeholder={placeholder}
              onDateRangeChange={handleDateRangeChange}
            />
          </Box>
        </Box>
      )}
    </div>
  );
}
