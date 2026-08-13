import { IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
} from 'recharts';
import { useMenuData, useTheme } from 'rj-core';

import { border, cardBg, textLabel } from '@/configs/Colors';

import { Panel, PanelDataItem } from '../../types/IDashboard';
import GetPath from '../../utils/getPath';

interface Props {
  panel?: Panel;
}

const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [menuData] = useMenuData();

  if (active && payload && payload.length) {
    const name = payload[0].name;
    if (!name) return null;

    return (
      <div
        style={{
          backgroundColor: cardBg[theme === 'dark' ? 'dark' : 'light'],
          border: `1px solid ${border[theme === 'dark' ? 'dark' : 'light']}`,
          padding: '10px',
          borderRadius: '5px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        }}
      >
        <p style={{ margin: 0, fontWeight: 'bold' }}>{t(name)}</p>
        <p style={{ margin: 0, color: payload[0].payload.color.light }}>
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: payload[0].payload.color.light,
              marginRight: '5px',
            }}
          ></span>
          {`${payload[0].value}`}
        </p>
      </div>
    );
  }
  return null;
};

const DeliveryProgress: React.FC<Props> = ({ panel }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [menuData] = useMenuData();
  const { getEtriPath } = GetPath();
  const etriPath = getEtriPath(menuData);
  const navigate = useNavigate();

  if (!panel) return null;

  const data = panel.panel_data.data;
  const percentage = panel.panel_data.percentage;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: `calc(15 * (100vw / 1920))px`,
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

      <div style={{ display: 'flex', flexDirection: 'row', flex: 1 }}>
        {/* Pie Chart */}
        <div style={{ position: 'relative', width: '60%', padding: '0.25rem' }}>
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <PieChart>
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: 'transparent' }}
                wrapperStyle={{ zIndex: 1000 }}
              />
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius="72%"
                outerRadius="100%"
                stroke="none"
                fill={
                  theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)'
                }
                dataKey="value"
                nameKey="label"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      theme === 'dark' ? entry.color.dark : entry.color.light
                    }
                    cursor="pointer"
                  // strokeWidth={0}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
              fontSize: `calc( (28 / 1920) * 100vw)`,
              fontWeight: 'bold',
            }}
          >
            {percentage}%
          </div>
        </div>
        {/* Label */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              flexWrap: 'wrap',
              paddingLeft: '2rem',
              gap: '0.5rem',
              // justifyContent: "center",
            }}
          >
            {data.map((item: PanelDataItem) => (
              <div
                key={item.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginRight: 15,
                  marginBottom: 5,
                }}
              >
                <span
                  style={{
                    width: 10,
                    height: 10,
                    backgroundColor:
                      theme === 'dark' ? item.color.dark : item.color.light,
                    borderRadius: '50%',
                    marginRight: 5,
                  }}
                ></span>
                <span style={{ fontSize: `calc( (14 / 1920) * 100vw)` }}>
                  {t(item.label)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeliveryProgress;
