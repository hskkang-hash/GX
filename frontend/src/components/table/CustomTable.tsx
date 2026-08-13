import { ConfigProvider, Table, TableProps } from 'antd';
import { Empty } from 'antd';
import React, { type ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import './CustomTable.scss';

interface CustomTableProps<T = Record<string, unknown>> {
  columns: TableProps<T>['columns'];
  data: T[];
  size?: 'small' | 'middle' | 'large';
  customRowBg?: {
    darkBg: string;
    lightBg: string;
  };
}

export const CustomTable = <T extends Record<string, unknown>>({
  columns,
  data,
  size = 'small',
  customRowBg,
}: CustomTableProps<T>): ReactElement => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <ConfigProvider
      theme={{
        components: {
          Table: {
            headerBg: theme === 'dark' ? '#2D2E30' : '#ECECEF',
            headerColor: theme === 'dark' ? '#ECECEF' : '#2D2E30',
            borderColor: theme === 'dark' ? '#3C3D3E' : '#DDDFE2',
            headerBorderRadius: 0,
            rowHoverBg: 'transparent',
          },
        },
        token: {
          colorBgContainer: customRowBg
            ? theme === 'dark'
              ? customRowBg.darkBg
              : customRowBg.lightBg
            : 'transparent',
          colorText: theme === 'dark' ? '#ECECEF' : '#2D2E30',
          motionDurationMid: '0s',
          motionDurationSlow: '0s',
          fontWeightStrong: 400,
        },
      }}
    >
      <Table
        bordered
        columns={columns}
        dataSource={data}
        pagination={false}
        size={size}
        className={`custom-table ${theme}`}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('No data')}
            />
          ),
        }}
      />
    </ConfigProvider>
  );
};
