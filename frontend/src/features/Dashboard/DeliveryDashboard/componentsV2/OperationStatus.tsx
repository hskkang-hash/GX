import { Box, Tooltip } from '@mui/material';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IoLocationSharp } from 'react-icons/io5';
import { useTheme } from 'rj-core';

import HubHideIcon from '@/assets/images/HouseIconDashboard.svg';
import HubActiveIcon from '@/assets/images/HouseIconDashboardActive.svg';
import Drone1Icon from '@/assets/images/dashboard/drone-25kg.svg';
import RobotIcon from '@/assets/images/dashboard/robot.svg';
import NoDataIcon from '@/assets/images/no_data.svg';
import Colors from '@/configs/Colors';

import { Panel } from '../../types/IDashboard';
import PopoverDevice from './PopoverDevice';
import './operationalStatus.scss';

// import './operationalStatus.sass';

interface OperationStatusData {
  devices: {
    [weight: string]: {
      drones: Array<{
        type: string;
        color: string | null;
        device: string;
        status: string;
        location: {
          latitude: number;
          longitude: number;
        };
      }>;
      robots: Array<{
        type: string;
        color: string | null;
        device: string;
        status: string;
        location: {
          latitude: number;
          longitude: number;
        };
      }>;
    };
  };
  docking_station: {
    active: boolean;
    name: string;
    latitude: string;
    longitude: string;
  };
  linked_terminals: Array<{
    name: string;
    active: boolean;
  }>;
}

interface Props {
  panel?: Panel;
}

const listStatus = [
  {
    color: '#69DC8A',
    name: 'Active',
    value: 'available',
  },
  {
    color: '#EB7509',
    name: 'On Mission',
    value: 'on_mission',
  },
  {
    color: '#FFDE21',
    name: 'Warning',
    value: 'warning',
  },
  {
    color: '#F64E60',
    name: 'Inactive',
    value: 'inactive',
  },
];

const getColor = (status: string) => {
  return listStatus.find((item) => item.value === status)?.color;
};

const OperationStatus: React.FC<Props> = ({ panel }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [selectedDevice, setSelectedDevice] = useState<any>(null);
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null);
  const deviceId = selectedDevice?.id;

  const handleClick = (event: React.MouseEvent<HTMLElement>, device: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedDevice(device);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);
  // const id = open ? 'simple-popover' : undefined;
  if (!panel) return null;
  const data = panel.panel_data.data as unknown as OperationStatusData[];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        gap: '1.5rem',
      }}
    >
      {/* Header */}
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {listStatus.map((item) => (
            <Box
              key={item.name}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  backgroundColor: item.color,
                  borderRadius: '50%',
                }}
              ></Box>
              <Box style={{ fontSize: `calc( (12 / 1920) * 100vw)` }}>
                {t(item.name)}
              </Box>
            </Box>
          ))}
        </Box>
      </div>
      {/* List data */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          overflowY: 'auto',
          maxHeight: '50vh',
          width: '100%',
          overflowX: 'auto',
        }}
        className="scrollbar-custom"
      >
        {data?.map((item, index) => {
          const listDevice = Object.entries(item?.devices).map(
            ([weight, deviceData], idx) => {
              const hasDrones = deviceData?.drones?.length > 0;
              const hasRobots = deviceData?.robots?.length > 0;
              return hasDrones || hasRobots;
            },
          );
          const checkListDevice = listDevice.some((v) => v === true);
          if (item?.linked_terminals.length == 0 && !checkListDevice) {
            return;
          }
          return (
            <Box
              key={index}
              style={{
                background:
                  theme === 'light' ? '#F6F7F8' : 'var(--ga-dark-bg-accordion)',
                padding: '0 12px 0px ',
                borderRadius: '12px',
                flex: 1,
                boxSizing: 'content-box',
              }}
            >
              <Box
                className="scrollbar-custom"
                style={{
                  display: 'flex',
                  gap: '1.5rem',
                  padding: '12px',
                  overflowX: 'auto',
                  height: '179px',
                  whiteSpace: 'nowrap',
                }}
              >
                <div style={{ display: 'flex', gap: '1.5rem' }}>
                  {/* ------- DOCKING STATION NAME ------- */}
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.5rem',
                      width: '90px',
                      alignItems: 'center',
                      padding: '15.5px 0',
                      flexShrink: 0,
                      alignSelf: 'center',
                    }}
                  >
                    <img
                      style={{
                        width: '50px',
                        height: '50px',
                        objectFit: 'contain',
                      }}
                      src={
                        item?.docking_station?.active
                          ? HubActiveIcon
                          : HubHideIcon
                      }
                      alt="Delivery Hub"
                    />
                    <Tooltip
                      title={item?.docking_station?.name}
                      arrow
                      placement="right"
                    >
                      <span
                        style={{
                          paddingTop: '12px',
                          fontSize: `calc( (14 / 1920) * 100vw)`,
                          fontWeight: '600',
                          textAlign: 'center',
                          maxWidth: '100px',
                          // textOverflow: 'ellipsis',
                          // overflow: 'hidden',
                          whiteSpace: 'wrap',
                          textWrap: 'wrap',
                          color: item?.docking_station?.active
                            ? '#69DC8A'
                            : Colors.Gray5,
                        }}
                      >
                        {item?.docking_station?.name}
                      </span>
                    </Tooltip>
                  </div>

                  {/* ------- LIST TERMINALS ------- */}
                  <div
                    style={{
                      padding: '12px 8px 12px 12px',
                      background:
                        theme === 'light'
                          ? 'white'
                          : 'var(--ga-btn-outline-dark-bg)',
                      borderRadius: '8px',
                      minWidth: '241px',
                      maxWidth: '241px',
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                  >
                    {item?.linked_terminals?.length > 0 ? (
                      <ul
                        className="scrollbar-custom"
                        style={{
                          overflowY: 'auto',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '1rem',
                          margin: 0,
                          padding: 0,
                          alignItems: 'flex-start',
                          justifyContent: 'flex-start',
                        }}
                      >
                        {item?.linked_terminals?.map((terminal) => (
                          <li
                            key={terminal.name}
                            style={{
                              listStyle: 'none',
                              display: 'flex',
                              width: '100%',
                              textOverflow: 'ellipsis',
                              flex: 1,
                            }}
                          >
                            <IoLocationSharp
                              size={16}
                              style={{
                                color:
                                  item?.docking_station?.active &&
                                    terminal.active
                                    ? '#69DC8A'
                                    : '#9C9D9D',
                              }}
                            />
                            <Tooltip
                              title={terminal.name}
                              arrow
                              placement="right"
                            >
                              <span
                                style={{
                                  fontSize: `calc( (12 / 1920) * 100vw)`,
                                  marginLeft: '0.6rem',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  flex: 1,
                                }}
                              >
                                {terminal.name}
                              </span>
                            </Tooltip>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          height: '100%',
                        }}
                      >
                        <img
                          style={{
                            width: '40px',
                            height: '40px',
                            objectFit: 'contain',
                          }}
                          src={NoDataIcon}
                          alt="No Data"
                        />
                      </div>
                    )}
                  </div>
                </div>
                {/* ------- LIST DEVICES ------- */}
                {Object.entries(item.devices).map(
                  ([weight, deviceData], idx) => {
                    const hasDrones = deviceData?.drones?.length > 0;
                    const hasRobots = deviceData?.robots?.length > 0;

                    if (!hasDrones && !hasRobots) {
                      return null;
                    }

                    return (
                      <div
                        key={idx}
                        style={{ display: 'flex', gap: '1rem' }}
                      >
                        {/* DRONE BLOCK */}
                        {hasDrones && (
                          <div
                            style={{
                              padding: '8px 8px 8px 0',
                              background:
                                theme === 'light'
                                  ? 'white'
                                  : 'var(--ga-btn-outline-dark-bg)',
                              borderRadius: '8px',
                              minWidth: '160px',
                            }}
                          >
                            <div
                              style={{
                                padding: '0 12px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.5rem',
                                width: '160px',
                                flexShrink: 0,
                                overflow: 'hidden',
                                height: '100%',
                                overflowY: 'auto',
                              }}
                              className="scrollbar-custom"
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  alignItems: 'center',
                                  width: 'fit-content',
                                }}
                              >
                                <img
                                  src={Drone1Icon}
                                  height={36}
                                  width={36}
                                  alt="Drone"
                                />
                                <span
                                  style={{
                                    fontWeight: '600',
                                    fontSize: '12px',
                                  }}
                                >
                                  {weight}
                                </span>
                              </div>
                              <ul
                                style={{
                                  margin: 0,
                                  padding: 0,
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}
                              >
                                {deviceData.drones?.map((drone, i) => (
                                  <Box
                                    key={i}
                                    style={{ position: 'relative' }}
                                  >
                                    <li
                                      key={i}
                                      onClick={(
                                        e: React.MouseEvent<HTMLLIElement>,
                                      ) => {
                                        e.stopPropagation();
                                        handleClick(e, drone);
                                      }}
                                      style={{
                                        listStyle: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '6px',
                                        border: `1px solid ${drone.color || '#000'}`,
                                        borderRadius: '8px',
                                        overflow: 'hidden',
                                        whiteSpace: 'nowrap',
                                        width: '100%',
                                        // position: 'relative',
                                      }}
                                    >
                                      <Box
                                        sx={{
                                          width: 10,
                                          height: 10,
                                          backgroundColor: getColor(
                                            drone.status,
                                          ),
                                          flexShrink: 0,
                                          borderRadius: '50%',
                                        }}
                                      ></Box>
                                      <Tooltip
                                        title={drone.device}
                                        arrow
                                        placement="right"
                                      >
                                        <span
                                          style={{
                                            marginLeft: '0.6rem',
                                            fontSize: '12px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                            width: '100%',
                                          }}
                                        >
                                          {drone.device}
                                        </span>
                                      </Tooltip>
                                    </li>
                                  </Box>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}

                        {/* ROBOT BLOCK */}
                        {hasRobots && (
                          <div
                            style={{
                              padding: '8px 8px 8px 0',
                              background:
                                theme === 'light'
                                  ? 'white'
                                  : 'var(--ga-btn-outline-dark-bg)',
                              borderRadius: '8px',
                              minWidth: '160px',
                            }}
                          >
                            <div
                              style={{
                                padding: '0 12px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.5rem',
                                width: '160px',
                                flexShrink: 0,
                                overflow: 'hidden',
                                height: '100%',
                                overflowY: 'auto',
                              }}
                              className="scrollbar-custom"
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  alignItems: 'center',
                                  width: 'fit-content',
                                }}
                              >
                                <img
                                  src={RobotIcon}
                                  height={36}
                                  width={36}
                                  alt="Robot"
                                />
                                <span
                                  style={{
                                    fontWeight: '600',
                                    fontSize: '12px',
                                  }}
                                >
                                  {weight}
                                </span>
                              </div>
                              <ul
                                style={{
                                  margin: 0,
                                  padding: 0,
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}
                              >
                                {deviceData.robots?.map((robot, i) => (
                                  <Box
                                    key={i}
                                    style={{ position: 'relative' }}
                                  >
                                    <li
                                      key={i}
                                      onClick={(
                                        e: React.MouseEvent<HTMLLIElement>,
                                      ) => {
                                        e.stopPropagation();
                                        handleClick(e, robot);
                                      }}
                                      style={{
                                        listStyle: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '6px',
                                        border: `1px solid ${robot.color || '#000'}`,
                                        borderRadius: '8px',
                                        overflow: 'hidden',
                                        whiteSpace: 'nowrap',
                                        width: '100%',
                                      }}
                                    >
                                      <Box
                                        sx={{
                                          width: 12,
                                          height: 12,
                                          backgroundColor: getColor(
                                            robot.status,
                                          ),
                                          flexShrink: 0,
                                          borderRadius: '50%',
                                        }}
                                      ></Box>
                                      <Tooltip
                                        title={robot.device}
                                        arrow
                                        placement="right"
                                      >
                                        <span
                                          style={{
                                            marginLeft: '0.6rem',
                                            fontSize: '12px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                            width: '100%',
                                          }}
                                        >
                                          {robot.device}
                                        </span>
                                      </Tooltip>
                                    </li>
                                  </Box>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  },
                )}
              </Box>
            </Box>
          );
        })}
      </Box>
      <PopoverDevice
        open={open}
        anchorEl={anchorEl}
        handleClose={handleClose}
        theme={theme}
        deviceId={deviceId}
      />
    </div>
  );
};

export default OperationStatus;
