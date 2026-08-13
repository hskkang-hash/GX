import { Box } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import { infoBg } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
  panelStyles?: React.CSSProperties;
}

const RegionalOrderStats: React.FC<Props> = ({ panel, panelStyles }) => {
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
        display="flex"
        flexDirection="column"
        gap="1rem"
        style={{ marginTop: '0.5rem', flex: 1, ...panelStyles }}
      >
        {data.map((item) => (
          <Box
            key={item.label}
            style={{
              background: infoBg[theme === 'dark' ? 'dark' : 'light'],
              padding: '1rem 1.25rem',
              borderRadius: 12,
              display: 'flex',
              flex: 1,
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: '1.125rem', fontWeight: '600' }}>
              {t(item.label)}
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: '1.875rem',
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

export default RegionalOrderStats;
