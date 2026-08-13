import { DownOutlined } from '@ant-design/icons';
import { Collapse, ConfigProvider, Space, Table } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import { Divider, IconButton, Tooltip } from '@mui/material';
import { FiMapPin, FiRefreshCw, FiWind } from 'react-icons/fi';
import Colors, { border as borderColor, textLabel } from '@/configs/Colors';
import { StatusBadge } from '../../../components/StatusBadge';
import { Box } from '@mui/material';

export interface DroneSensorStatusType {
  name: string;
  enabled?: boolean;
  present?: boolean;
  health?: boolean;
  status: string;
  situation: string;
}

const DroneSensorStatus = ({
  droneSensorStatus,
  sensorStatus,
  onRefreshSensorStatus,
  loadingSensorStatus,
}: {
  droneSensorStatus: DroneSensorStatusType[];
  sensorStatus: any;
  onRefreshSensorStatus?: () => void;
  loadingSensorStatus: boolean;
}) => {

  console.log('droneSensorStatus_dadadad', droneSensorStatus);
  console.log('sensorStatus_dadadad55333232', sensorStatus);
  console.log('loadingSensorStatus_dadadad66', loadingSensorStatus);

  const { t } = useTranslation();
  const [theme] = useTheme();
  const [dataLeftTable, setDataLeftTable] = useState<DroneSensorStatusType[]>([
    {
      name: '_3D_GYRO',
      situation: 'Loading',
      status: 'ON',
    },
    {
      name: '_3D_ACCEL',
      situation: 'Loading',
      status: 'ON',
    },
    {
      name: 'GPS',
      situation: 'Loading',
      status: 'ON',
    },
    {
      name: 'BATTERY',
      situation: 'Loading',
      status: 'ON',
    },
  ]);
  const [dataRightTable, setDataRightTable] = useState<DroneSensorStatusType[]>(
    [
      {
        name: 'ATTITUDE_STABILIZATION',
        situation: 'Loading',
        status: 'ON',
      },
      {
        name: 'MAV_SYS_STATUS_AHRS',
        situation: 'Loading',
        status: 'ON',
      },
      {
        name: 'MAV_SYS_STATUS_PREARM_CHECK',
        situation: 'Loading',
        status: 'ON',
      },
      {
        name: 'MAV_SYS_STATUS_TERRAIN',
        situation: 'Loading',
        status: 'ON',
      },
    ],
  );

  useEffect(() => {
    if (droneSensorStatus.length > 0) {
      // Update left table data
      setDataLeftTable((prev) =>
        prev.map((item) => {
          const updatedSensor = droneSensorStatus.find(
            (sensor) => sensor.name === item.name,
          );
          return updatedSensor
            ? {
              ...item,
              status: updatedSensor.status,
              situation: updatedSensor.situation,
            }
            : item;
        }),
      );

      // Update right table data
      setDataRightTable((prev) =>
        prev.map((item) => {
          const updatedSensor = droneSensorStatus.find(
            (sensor) => sensor.name === item.name,
          );
          console.log('updatedSensor', updatedSensor);
          return updatedSensor
            ? {
              ...item,
              status: updatedSensor.status,
              situation: updatedSensor.situation,
            }
            : item;
        }),
      );
    } else {
      setDataLeftTable([
        {
          name: '_3D_GYRO',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: '_3D_ACCEL',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: 'GPS',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: 'BATTERY',
          situation: 'Loading',
          status: 'ON',
        },
      ]);
      setDataRightTable([
        {
          name: 'ATTITUDE_STABILIZATION',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: 'MAV_SYS_STATUS_AHRS',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: 'MAV_SYS_STATUS_PREARM_CHECK',
          situation: 'Loading',
          status: 'ON',
        },
        {
          name: 'MAV_SYS_STATUS_TERRAIN',
          situation: 'Loading',
          status: 'ON',
        },
      ]);
    }
  }, [droneSensorStatus]);

  const droneSensorColumns = useMemo(() => {
    return [
      {
        title: t('Inspection Item(s)'),
        dataIndex: 'inspection_items',
        key: 'inspection_items',
        render: (_: unknown, record: DroneSensorStatusType) => (
          <span>{record.name + '(' + record.status + ')'}</span>
        ),
      },
      {
        title: t('Status'),
        dataIndex: 'situation',
        key: 'situation',
        width: 130,
        render: (_: unknown, record: DroneSensorStatusType) => (
          <StatusBadge
            status={
              (record?.situation?.toLowerCase() as
                | 'normal'
                | 'loading'
                | 'error') || 'loading'
            }
            theme={theme}
          />
        ),
      },
    ];
  }, [droneSensorStatus, t, theme]); // eslint-disable-line react-hooks/exhaustive-deps

  const ContentCollapse = useMemo(() => {
    return (
      <ConfigProvider
        theme={{
          components: {
            Table: {
              headerBg: theme === 'dark' ? '#2D2E30' : '#ECECEF',
              borderColor: theme === 'dark' ? '#3C3D3E' : '#dddfe2',
            },
          },
          token: {
            /* here is your global tokens */
            colorBgContainer: theme === 'dark' ? '#1F1F20' : '#ffffff',
            motionDurationMid: '0s',
            motionDurationSlow: '0s',
            borderRadius: 0,
            fontWeightStrong: 400,
          },
        }}
      >
        <Box display="flex" gap="3rem" mt="1rem">
          <Box display="flex" gap="0.5rem">
            <span>{t('Flight Mode')}:</span>
            <span>{sensorStatus?.flightMode || ""}</span>
          </Box>
          <Box display="flex" gap="0.5rem">
            <span>{t('Status')}:</span>
            <span>
              {sensorStatus?.armed == null
                ? ""
                : sensorStatus.armed
                  ? "Arm"
                  : "Disarm"}
            </span>

          </Box>
        </Box>
        <Space
          align="center"
          size="middle"
          style={{
            width: '100%',
            justifyContent: 'space-between',
          }}
          styles={{
            item: {
              width: '100%',
            },
          }}
        >
          <Table<DroneSensorStatusType>
            columns={droneSensorColumns}
            dataSource={dataLeftTable}
            rowKey="name"
            pagination={false}
            size="small"
            bordered={true}
          />

          <Table<DroneSensorStatusType>
            columns={droneSensorColumns}
            dataSource={dataRightTable}
            rowKey="name"
            pagination={false}
            size="small"
            bordered={true}
          />
        </Space>
      </ConfigProvider>
    );
  }, [droneSensorColumns, dataLeftTable, dataRightTable, theme, sensorStatus, t]);

  return (
    <>
      <ConfigProvider
        theme={{
          components: {
            Collapse: {
              headerBg: theme === 'dark' ? '#1F1F20' : '#ffffff',
              contentBg: theme === 'dark' ? '#000000' : '#ffffff',
            },
          },
          token: {
            colorText: theme === 'dark' ? '#ffffff' : '#000000',
          },
        }}
      >
        <Collapse
          size="small"
          defaultActiveKey={['1']}
          expandIconPosition="end"
          bordered={false}
          style={{
            width: '100%',
            border: `1px solid ${theme === 'dark' ? '#1F1F20' : '#ffffff'}`,
          }}
          className={`${theme === 'dark' ? 'dark' : 'light'}`}
          expandIcon={({ isActive }) => (
            <Box display="flex" gap="2rem">
              {isActive ? <IconButton
                size="small"
                disabled={!loadingSensorStatus ? false : true}
                sx={{
                  mt: '0.5rem',
                  border: `1px solid ${borderColor[theme === 'dark' ? 'dark' : 'light']}`,
                  borderRadius: '0.5rem',
                  opacity: loadingSensorStatus ? 0.6 : 1,
                  '&:hover': {
                    color:
                      theme === 'dark'
                        ? 'var(--ga-primary-dark)'
                        : 'var(--ga-primary)',
                  },
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (onRefreshSensorStatus) {
                    onRefreshSensorStatus();
                  }
                }}
              >
                <FiRefreshCw
                  style={{
                    fontSize: '1.25rem',
                    color: sensorStatus?.flightMode
                      ? loadingSensorStatus
                        ? Colors.Primary
                        : theme === 'dark'
                          ? Colors.White
                          : Colors.Black
                      : Colors.Gray5,
                    animation:
                      loadingSensorStatus
                        ? 'spin 1s linear infinite'
                        : 'none',
                  }}
                />
              </IconButton> : ""}
              <DownOutlined rotate={isActive ? 0 : 180} />
            </Box>
          )}
          items={[
            {
              key: '1',
              label: t('Drone Information'),
              children: ContentCollapse,
              styles: {
                header: {
                  fontWeight: '600',
                  fontSize: '1.5rem',
                  padding: '0',
                },
                body: {
                  padding: '0',
                },
              },
            },
          ]}
        />
      </ConfigProvider>
    </>
  );
};

export default React.memo(DroneSensorStatus);
