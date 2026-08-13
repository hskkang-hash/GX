import {
  Box,
  IconButton,
  Stack,
  styled,
  Tooltip as MuiTooltip,
} from '@mui/material';
import LinearProgress, {
  linearProgressClasses,
} from '@mui/material/LinearProgress';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import { useMenuData, useTheme } from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import { cardBg, colorOpacity, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import GetPath from '../../utils/getPath';
import { getIcon } from '../../utils/icon';

interface Props {
  panel?: Panel;
  lableEtri?: string;
  etriPath?: string;
}

const fakeData = [
  {
    label: 'Drones',
    count: '100',
    gb: '23',
  },
  {
    label: 'Robots',
    count: '23',
    gb: '67',
  },
];

const BorderLinearProgress = styled(LinearProgress)(({ theme, dataColor }) => ({
  height: 10,
  borderRadius: 5,
  [`&.${linearProgressClasses.colorPrimary}`]: {
    backgroundColor: theme.palette.grey[200],
    ...theme.applyStyles('dark', {
      backgroundColor: theme.palette.grey[800],
    }),
  },
  [`& .${linearProgressClasses.bar}`]: {
    borderRadius: 5,
    backgroundColor: dataColor.light,
    ...theme.applyStyles('dark', {
      backgroundColor: dataColor.light,
    }),
  },
}));

const LogDataCollection: React.FC<Props> = ({ panel, lableEtri }) => {
  const [menuData] = useMenuData();
  const { getInfrastructurePath } = GetPath();
  const etriPath = getInfrastructurePath(menuData);
  const [theme] = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  if (!panel) return null;

  const data = panel.panel_data.data;
  const IconComponent = getIcon(panel.panel_config?.icon);

  return (
    <Box
      display="flex"
      flexDirection="column"
      gap="1.25rem"
      flex={1}
      height="100%"
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
            title={lableEtri}
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
      </div>
      <Box
        display="flex"
        flexDirection="row"
        flex={1}
        gap="1rem"
      >
        {data.map((item) => (
          <Box
            key={t(item.label)}
            style={{
              position: 'relative',
              padding: `${23 * (100 / 1920)}vw ${12 * (100 / 1920)}vw`,
              borderRadius: `calc( (12 / 1920) * 100vw)`,
              display: 'flex',
              height: '100%',
              flex: 1,
              flexDirection: 'column',
              background:
                theme === 'dark'
                  ? colorOpacity(item.color.dark, 0.2)
                  : colorOpacity(item.color.light, 0.2),
              gap: '0.5rem',
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
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              <Truncate
                content={t(item.label)}
                maxLengthContent={18}
                tooltipContent={t(item.label)}
              />
            </span>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                // gap: "0.5rem",
                width: '100%',
                height: '100%',
              }}
            >
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: `calc(12 * (100vw / 1920))`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: `calc(4 * (100vw / 1920))`,
                  }}
                >
                  <span
                    style={{
                      fontSize: `calc( (14 / 1920) * 100vw)`,
                      fontWeight: '600',
                    }}
                  >
                    {t('Count')}
                  </span>
                  <span style={{ fontSize: `calc( (14 / 1920) * 100vw)` }}>
                    {item?.count} {t('records')}
                  </span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: `calc(4 * (100vw / 1920))`,
                  }}
                >
                  <span
                    style={{
                      fontSize: `calc( (14 / 1920) * 100vw)`,
                      fontWeight: '600',
                    }}
                  >
                    {t('Size')}
                  </span>
                  <span style={{ fontSize: `calc( (14 / 1920) * 100vw)` }}>
                    {item?.size} {t('GB')}
                  </span>
                </div>
              </div>
              <Stack
                spacing={0.5}
                sx={{ width: '100%', marginTop: 'auto' }}
              >
                <div
                  style={{
                    fontSize: `calc( (12 / 1920) * 100vw)`,
                    fontWeight: '600',
                  }}
                >
                  {item?.size}%
                </div>
                <BorderLinearProgress
                  dataColor={item.color}
                  variant="determinate"
                  value={item?.size}
                />
              </Stack>
            </div>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default LogDataCollection;
