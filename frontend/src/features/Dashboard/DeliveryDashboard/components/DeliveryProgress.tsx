import { IconButton, Tooltip as MuiTooltip } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CgArrowRight } from 'react-icons/cg';
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

interface Props {
  panel?: Panel;
}

interface RolePermission {
  permit_read: boolean;
  permit_create: boolean;
  permit_update: boolean;
  permit_delete: boolean;
  permit_export?: boolean;
  permit_import?: boolean;
}

interface MenuItem {
  id: number;
  menu_name: string;
  path: string;
  icon_name: string;
  role_permissions: RolePermission[];
  sub_menus: MenuItem[];
  tabs?: TabItem[];
}

interface TabItem {
  id: number;
  name: string;
  path: string;
  ordering: number;
  parent_menu_id: number;
  parent_tab_id: number | null;
  name_translations: string | null;
  role_permissions: RolePermission[];
}

const getEtriPath = (menuData: MenuItem[]): string | null => {
  const etriPaths: string[] = [];

  const checkMenu = (menus: MenuItem[]) => {
    menus.forEach((menu: MenuItem) => {
      if (menu.path === '/etri-tracking' || menu.path === '/etri-order') {
        etriPaths.push(menu.path);
      }
      if (menu.sub_menus && menu.sub_menus.length > 0) {
        checkMenu(menu.sub_menus);
      }
      if (menu.tabs && menu.tabs.length > 0) {
        menu.tabs.forEach((tab: TabItem) => {
          if (tab.path === '/etri-tracking' || tab.path === '/etri-order') {
            etriPaths.push(tab.path);
          }
        });
      }
    });
  };

  checkMenu(menuData);

  if (etriPaths.includes('/etri-tracking')) {
    return '/etri-tracking';
  } else if (etriPaths.includes('/etri-order')) {
    return '/etri-order';
  }

  return null;
};

const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [menuData] = useMenuData();
  console.log('menuData', menuData);

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
  const navigate = useNavigate();

  if (!panel) return null;

  const data = panel.panel_data.data;
  const total = data.reduce(
    (acc: number, item: PanelDataItem) => acc + item.value,
    0,
  );

  const etriPath = getEtriPath(menuData);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 15,
        }}
      >
        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>
          {t(panel.panel_title)}
        </h3>
        {etriPath && (
          <MuiTooltip
            title={t('Go to ETRI')}
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
              <CgArrowRight
                style={{
                  fontSize: '1.875rem',
                }}
              />
            </IconButton>
          </MuiTooltip>
        )}
      </div>
      <div style={{ position: 'relative', flex: 1 }}>
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
              innerRadius="70%"
              outerRadius="90%"
              fill={
                theme === 'dark'
                  ? 'var(--ga-primary-dark)'
                  : 'var(--ga-primary)'
              }
              paddingAngle={2}
              dataKey="value"
              nameKey="label"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={theme === 'dark' ? entry.color.dark : entry.color.light}
                  cursor="pointer"
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
            fontSize: 36,
            fontWeight: 'bold',
          }}
        >
          {total}
        </div>
      </div>
      <div
        style={{
          marginTop: 15,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
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
            <span>{t(item.label)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DeliveryProgress;
