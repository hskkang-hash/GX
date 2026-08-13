import { Box } from '@mui/material';
import { IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import { useMenuData, useTheme } from 'rj-core';

import { colorOpacity, infoBg, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import getEtriPath from '../../utils/getPath';
import GetPath from '../../utils/getPath';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
}

const StatusCard: React.FC<Props> = ({ panel }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [menuData] = useMenuData();
  const navigate = useNavigate();
  if (!panel) return null;

  const data = panel.panel_data.data;
  const IconComponent = getIcon(panel.panel_config?.icon);
  const { getEtriPath } = GetPath();
  const etriPath = getEtriPath(menuData);

  return (
    <Box
      display="flex"
      flexDirection="column"
      gap="1.25rem"
      flex={1}
    >
      <div
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
            title={etriPath == '/etri-order' ? t('Go to ETRI ORDER') : t('Go to ETRI TRACKING')}
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
                navigate(etriPath);
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
      </div>

      <Box
        display="flex"
        flexDirection="row"
        flex={1}
        gap="1.5rem"
      >
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
                padding: '0 clamp(0.5rem, 1vw, 2rem)',
                borderRadius: 'calc( (12 / 1920) * 100vw)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.25rem',
                }}
              >
                <span
                  style={{
                    fontSize: `calc( (16 / 1920) * 100vw)`,
                    fontWeight: '600',
                  }}
                >
                  {t(item?.label)}
                </span>
                <span
                  style={{
                    fontSize: `calc( (14 / 1920) * 100vw)`,
                    fontWeight: '400',
                  }}
                >
                  {'(' + t(item?.date) + ')'}
                </span>
              </div>
              <span
                style={{
                  fontWeight: '700',
                  paddingLeft: '0.5rem',
                  fontSize: `calc( (32 / 1920) * 100vw)`,
                  color: theme === 'dark' ? item.color.dark : item.color.light,
                }}
              >
                {item.value}
              </span>
            </div>
          ))}
        </Box>
        {/* BELL */}
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Box
            style={{
              background: infoBg[theme === 'dark' ? 'dark' : 'light'],
              borderRadius: '50%',
              padding: 'clamp(0.5rem, 2vw, 1.5rem)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              // aspectRatio: "1 / 1",
              width: `calc(80 * (100vw / 1920))px`,
              height: `calc(80 * (100vw / 1920))px`,
            }}
          >
            {IconComponent && <IconComponent />}
          </Box>
        </div>
      </Box>
    </Box>
  );
};

export default StatusCard;
