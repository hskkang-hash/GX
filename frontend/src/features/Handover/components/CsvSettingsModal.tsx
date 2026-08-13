import { Checkbox, FormControlLabel } from '@mui/material';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal, useTheme } from 'rj-core';

type CsvField = string;

interface CsvFieldItem {
  accessor: string;
  Header: string;
}

interface CsvSettingsModalProps {
  show: boolean;
  onHide: () => void;
  onDownload: (selectedFields: string[]) => void;
  CSV_FIELDS: CsvFieldItem[];
}

export const CsvSettingsModal = ({
  show,
  onHide,
  onDownload,
  CSV_FIELDS,
}: CsvSettingsModalProps): React.JSX.Element => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [selectedFields, setSelectedFields] = useState<Set<CsvField>>(
    new Set(),
  );

  const allFieldsSelected = useMemo(() => {
    return selectedFields.size === CSV_FIELDS.length;
  }, [selectedFields, CSV_FIELDS.length]);

  const leftColumnFields = useMemo(() => {
    const midPoint = Math.ceil(CSV_FIELDS.length / 2);
    return CSV_FIELDS.slice(0, midPoint);
  }, [CSV_FIELDS]);

  const rightColumnFields = useMemo(() => {
    const midPoint = Math.ceil(CSV_FIELDS.length / 2);
    return CSV_FIELDS.slice(midPoint);
  }, [CSV_FIELDS]);

  const handleToggleField = useCallback((field: CsvField) => {
    setSelectedFields((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(field)) {
        newSet.delete(field);
      } else {
        newSet.add(field);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (allFieldsSelected) {
      setSelectedFields(new Set());
    } else {
      setSelectedFields(new Set(CSV_FIELDS.map((field) => field.accessor)));
    }
  }, [allFieldsSelected, CSV_FIELDS]);

  const handleDownload = useCallback(() => {
    onDownload(Array.from(selectedFields));
    onHide();
  }, [onDownload, onHide, selectedFields]);

  const handleCancel = useCallback(() => {
    setSelectedFields(new Set());
    onHide();
  }, [onHide]);

  useEffect(() => {
    if (show) {
      setSelectedFields(new Set());
    }
  }, [show]);

  return (
    <CustomModal
      title={t('CSV Settings')}
      show={show}
      onHide={handleCancel}
      id="csv-settings-modal"
    >
      <div style={{ width: '40rem' }}>
        <div
          style={{
            color: theme === 'dark' ? '#9ca3af' : '#6c757d',
            fontSize: '0.875rem',
          }}
        >
          {t('Please select information you want to download.')}
        </div>

        <div>
          <FormControlLabel
            control={
              <Checkbox
                checked={allFieldsSelected}
                onChange={handleSelectAll}
                sx={{
                  color: theme === 'dark' ? '#e5e7eb' : '#212529',
                  '&.Mui-checked': {
                    color: '#1d9be2',
                  },
                  '&:hover': {
                    backgroundColor:
                      theme === 'dark'
                        ? 'rgba(29, 155, 226, 0.1)'
                        : 'rgba(29, 155, 226, 0.04)',
                  },
                }}
              />
            }
            label={
              <span
                style={{
                  fontWeight: 500,
                  fontSize: '1rem',
                  color: theme === 'dark' ? '#e5e7eb' : '#212529',
                }}
              >
                {t('Select All')}
              </span>
            }
          />
        </div>

        <div>
          <div
            style={{
              fontWeight: 600,
              fontSize: '1rem',
              color: theme === 'dark' ? '#e5e7eb' : '#212529',
            }}
          >
            {t('Notice')}
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '1rem',
            }}
          >
            <div>
              {leftColumnFields.map((field) => (
                <div key={field.accessor}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedFields.has(field.accessor)}
                        onChange={() => handleToggleField(field.accessor)}
                        sx={{
                          color: theme === 'dark' ? '#e5e7eb' : '#212529',
                          '&.Mui-checked': {
                            color: '#1d9be2',
                          },
                          '&:hover': {
                            backgroundColor:
                              theme === 'dark'
                                ? 'rgba(29, 155, 226, 0.1)'
                                : 'rgba(29, 155, 226, 0.04)',
                          },
                        }}
                      />
                    }
                    label={
                      <span
                        style={{
                          color: theme === 'dark' ? '#e5e7eb' : '#212529',
                        }}
                      >
                        {t(field.Header)}
                      </span>
                    }
                  />
                </div>
              ))}
            </div>
            <div>
              {rightColumnFields.map((field) => (
                <div key={field.accessor}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedFields.has(field.accessor)}
                        onChange={() => handleToggleField(field.accessor)}
                        sx={{
                          color: theme === 'dark' ? '#e5e7eb' : '#212529',
                          '&.Mui-checked': {
                            color: '#1d9be2',
                          },
                          '&:hover': {
                            backgroundColor:
                              theme === 'dark'
                                ? 'rgba(29, 155, 226, 0.1)'
                                : 'rgba(29, 155, 226, 0.04)',
                          },
                        }}
                      />
                    }
                    label={
                      <span
                        style={{
                          color: theme === 'dark' ? '#e5e7eb' : '#212529',
                        }}
                      >
                        {t(field.Header)}
                      </span>
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        <ActionBtn
          leftButtons={[
            <CustomBtn
              variant="filled"
              color="primary"
              size="lg"
              label={t('handover.Download')}
              type="button"
              onClick={handleDownload}
              disabled={selectedFields.size === 0}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              variant="outline"
              color="secondary"
              size="lg"
              label={t('handover.Cancel')}
              type="button"
              onClick={handleCancel}
            />,
          ]}
        />
      </div>
    </CustomModal>
  );
};
