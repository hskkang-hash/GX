import { Box, IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import { useMenuData, useTheme } from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import { cardBg, infoBg, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import getEtriPath from '../../utils/getPath';
import GetPath from '../../utils/getPath';
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
  const [menuData] = useMenuData();
  const navigate = useNavigate();
  const { getEtriPath } = GetPath();
  const etriPath = getEtriPath(menuData);

  return (
    <Box
      display="flex"
      flexDirection="column"
      gap="0.5rem"
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
        display="grid"
        columnGap="1.2rem"
        rowGap="1rem"
        style={{
          aspectRatio: '1',
          flex: 1,
          gridTemplateColumns: 'repeat(3, 1fr)',
          overflowY: 'auto',
          maxHeight: 'clamp(10rem, 30vh, 18rem)',
          ...panelStyles,
        }}
      >
        {data.map((item) => (
          <Box
            key={item.label}
            style={{
              position: 'relative',
              background: infoBg[theme === 'dark' ? 'dark' : 'light'],
              borderRadius: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              margin: '0.25rem 0',
              height: `${(83.5 * 100) / 1920}vw`,
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
                fontSize: `calc( (14 / 1920) * 100vw)`,
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              <Truncate
                content={t(item.label)}
                maxLengthContent={13}
              />
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: `calc( (24 / 1920) * 100vw)`,
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
