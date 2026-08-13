import { Box } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import { cardBg, infoBg } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
  panelStyles?: React.CSSProperties;
}

const DeliveryItems: React.FC<Props> = ({ panel, panelStyles }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  if (!panel) return null;

  const data = panel.panel_data.data;
  const IconComponent = getIcon(panel.panel_config?.icon);

  return (
    <Box
      display="flex"
      flexDirection="column"
      gap="1.25rem"
      flex={1}
    >
      <Box
        style={{
          background: infoBg[theme === 'dark' ? 'dark' : 'light'],
          borderRadius: '50%',
          padding: '2rem',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 64,
          height: 64,
        }}
      >
        {IconComponent && <IconComponent style={{ width: 32, height: 32 }} />}
      </Box>

      <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{t(panel.panel_title)}</h3>

      <Box
        display="grid"
        gap="1.5rem"
        style={{
          marginTop: '0.5rem',
          flex: 1,
          gridTemplateColumns: 'repeat(3, 1fr)',
          gridAutoRows: '1fr',
          ...panelStyles,
        }}
      >
        {data.map((item) => (
          <Box
            key={item.label}
            style={{
              position: 'relative',
              background: infoBg[theme === 'dark' ? 'dark' : 'light'],
              padding: '1rem',
              borderRadius: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              margin: '0.25rem 0',
            }}
          >
            <span
              style={{
                position: 'absolute',
                top: '0',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: cardBg[theme === 'dark' ? 'dark' : 'light'],
                padding: '2px 4px',
                borderRadius: 4,
                fontSize: '0.875rem',
                fontWeight: '600',
                textAlign: 'center',
                width: '5rem',
              }}
            >
              {t(item.label)}
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: '1.75rem',
                color: theme === 'dark' ? item.color.dark : item.color.light,
              }}
            >
              {item.value}
            </span>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default DeliveryItems;
