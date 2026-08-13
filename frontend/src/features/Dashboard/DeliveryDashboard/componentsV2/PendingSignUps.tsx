import { Box, IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import { useMenuData, useTheme } from 'rj-core';

import { colorOpacity, infoBg, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import GetPath from '../../utils/getPath';

interface Props {
  panel?: Panel;
  etriPath?: string;
  lableEtri?: string;
}

const PendingSignUp: React.FC<Props> = ({ panel, lableEtri }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [menuData] = useMenuData();
  const navigate = useNavigate();
  const { getUserManagementPath } = GetPath();
  const etriPath = getUserManagementPath(menuData);

  if (!panel) return null;

  const data = panel.panel_data.data;

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
            title={lableEtri || ''}
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
        gap="1rem"
      >
        <Box
          flex={1}
          display="grid"
          gap="1rem"
          gridTemplateColumns={{
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
          }}
          gridAutoRows="1fr"
        >
          {data.map((item, index) => (
            <div
              key={item.label}
              style={{
                flex: 1,
                gridColumn: index === 0 ? 'span 2' : 'auto',
                padding: '0 15px',
                borderRadius: `calc( (12 / 1920) * 100vw)`,
                display: 'flex',
                flexDirection: index === 0 ? 'row' : 'column',
                justifyContent: index === 0 ? 'space-between' : 'center',
                alignItems: index === 0 ? 'center' : 'flex-start',
                gap: '0.3rem',
                background:
                  theme === 'dark'
                    ? colorOpacity(item.color.dark, 0.2)
                    : colorOpacity(item.color.light, 0.2),
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
                  {t(item.label)}
                </span>
              </div>
              <span
                style={{
                  fontWeight: '700',
                  fontSize: `calc( (28 / 1920) * 100vw)`,
                  color: theme === 'dark' ? item.color.dark : item.color.light,
                  lineHeight: '1',
                }}
              >
                {item.value}
              </span>
            </div>
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default PendingSignUp;
