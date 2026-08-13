import { IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { useNavigate } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';
import { useMenuData, useTheme } from 'rj-core';

import { axisColor, textLabel } from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import GetPath from '../../utils/getPath';

interface Props {
  panel?: Panel;
}

const DeliveryStats: React.FC<Props> = ({ panel }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  if (!panel) return null;

  const data = panel.panel_data.data;

  console.log('data', data);

  // Calculate dynamic domain and ticks for Y-axis
  const maxValue = data.length > 0 ? Math.max(...data.map((d) => d.value)) : 0;

  // Round up to the nearest multiple of 25 for the top of the domain.
  // This provides nice padding and satisfies cases like a max value of 8x resulting in a 100 domain top.
  const yAxisTop = Math.max(25, Math.ceil(maxValue / 25) * 25);

  // Generate 5 evenly-spaced ticks for the Y-axis.
  const tickCount = 5;
  const tickInterval = yAxisTop / (tickCount - 1);
  const ticks = Array.from({ length: tickCount }, (_, i) =>
    Math.round(i * tickInterval),
  );

  const [menuData] = useMenuData();
  const navigate = useNavigate();
  const { getEtriPath } = GetPath();
  const etriPath = getEtriPath(menuData);

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
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
      <div style={{ flex: 1 }}>
        <ResponsiveContainer
          width="100%"
          height="100%"
        >
          <BarChart
            data={data}
            margin={{
              top: 20,
              right: 10,
              left: -35,
              bottom: -10,
            }}
          >
            <CartesianGrid
              strokeDasharray="1 1"
              stroke={axisColor[theme === 'dark' ? 'dark' : 'light']}
              strokeWidth={1}
              strokeOpacity={1}
            />
            <XAxis
              dataKey="label"
              tickFormatter={(tick) => t(tick as string)}
              tickLine={false}
              // axisLine={false}
              fontSize={12}
              stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              fontSize={12}
              ticks={ticks}
              domain={[0, yAxisTop]}
              stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
            />
            <Bar
              dataKey="value"
              fill={
                theme === 'dark'
                  ? 'var(--ga-primary-dark)'
                  : 'var(--ga-primary)'
              }
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
            >
              <LabelList
                dataKey="value"
                position="top"
                fontSize={12}
                fill={textLabel[theme === 'dark' ? 'dark' : 'light']}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DeliveryStats;
