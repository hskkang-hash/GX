import { Box, IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import { useMenuData, useTheme } from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import Colors, { textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import GetPath from '../../utils/getPath';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
}

const DeviceItems: React.FC<Props> = ({ panel }) => {
  const navigate = useNavigate();
  const [menuData] = useMenuData();
  const { getInfrastructurePath } = GetPath();
  const etriPath = getInfrastructurePath(menuData);

  if (!panel) return null;
  const [theme] = useTheme();
  const { t } = useTranslation();
  const data = panel.panel_data.data;

  const getIconComponent = (icon: string) => {
    const IconComponent = getIcon(icon);
    if (!IconComponent) return null;
    return <IconComponent />;
  };

  return (
    <Box
      display="flex"
      flexDirection="column"
      style={{ gap: 'clamp(0.5rem, 0.75vw, 1.25rem)' }}
      flex={1}
    >
      <Box
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: `calc( (17 / 1920) * 100vw)`,
            fontWeight: 'bold',
          }}
        >
          {t(panel.panel_title)}
        </h3>
        {etriPath && (
          <MuiTooltip
            title={t('Go to Drones/Robots and Infrastructure')}
            arrow
            placement="top"
          >
            <IconButton
              sx={{
                color: textLabel[theme === 'dark' ? 'dark' : 'light'],
                padding: 0,
                minWidth: 0,
                width: 'auto',
                '&:hover': {
                  color:
                    theme === 'dark'
                      ? 'var(--ga-primary-dark)'
                      : 'var(--ga-primary)',
                  transform: 'scale(1.2)',
                  transition: 'all 0.4s ease-in-out',
                  background: 'transparent',
                },
                '&:active': {
                  background: 'transparent',
                },
              }}
              onClick={() => {
                navigate(etriPath || '');
              }}
            >
              <LiaLongArrowAltRightSolid
                style={{
                  fontSize: '1.875rem',
                }}
              />
            </IconButton>
          </MuiTooltip>
        )}
      </Box>
      <Box
        display="flex"
        flexDirection="row"
        flexWrap="nowrap"
        justifyContent="space-between"
        gap="1rem"
        overflowX="hidden"
        flex={1}
      >
        {data.map((item) => (
          <Box
            key={item.label}
            style={{
              background: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
              padding: 'clamp(0.5rem, 0.75vw, 1rem) 0',
              borderRadius: 'calc( (12 / 1920) * 100vw)',
              flex: '1 1 0',
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '100%',
            }}
          >
            <div
              style={{
                fontSize: `calc( (16 / 1920) * 100vw)`,
                fontWeight: 600,
                textAlign: 'center',
              }}
            >
              <Truncate
                content={t(item.label)}
                maxLengthContent={10}
              />
            </div>

            <div
              style={{
                aspectRatio: '1',
                // width: "clamp(30px, 5vw, 50px)",
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: `calc(60 * (100vw / 1920))px`,
                width: `calc(60 * (100vw / 1920))px`,
              }}
            >
              {item.icon && getIconComponent(item.icon)}
            </div>

            <div
              style={{
                fontSize: `calc( (28 / 1920) * 100vw)`,
                fontWeight: 700,
                color: Colors.PrimaryDark,
              }}
            >
              {item.value}
            </div>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default DeviceItems;
