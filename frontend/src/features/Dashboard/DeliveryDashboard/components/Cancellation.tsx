import { Box } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { useTheme } from 'rj-core';

import { colorOpacity, infoBg, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
}

const Cancellation: React.FC<Props> = ({ panel }) => {
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

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>
          {t(panel.panel_title)}
        </h3>
        {/* <CgArrowRight
          style={{
            color: textLabel[theme === "dark" ? "dark" : "light"],
            fontSize: "1.875rem",
          }}
        /> */}
      </div>
      <Box
        flex={1}
        display="flex"
        flexDirection="column"
        gap="1rem"
      >
        {data.map((item) => (
          <div
            key={item.label}
            style={{
              flex: 1,
              background:
                theme === 'dark'
                  ? colorOpacity(item.color.dark, 0.2)
                  : colorOpacity(item.color.light, 0.2),
              padding: '10px 15px',
              borderRadius: 8,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ fontSize: '1.125rem', fontWeight: '600' }}>
              {t(item.label)}
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: 20,
                color: theme === 'dark' ? item.color.dark : item.color.light,
              }}
            >
              {item.value}
            </span>
          </div>
        ))}
      </Box>
    </Box>
  );
};

export default Cancellation;
