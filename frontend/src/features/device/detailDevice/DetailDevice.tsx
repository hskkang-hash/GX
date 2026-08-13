import { Image } from 'antd';
import dayjs from 'dayjs';
import i18next from 'i18next';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  useTheme,
  ToastTopHelper,
  ROLE_PERMISSION,
  useUserInfo,
} from 'rj-core';

import DownLoad from '@/assets/images/DownLoad';
import FileTypeFile from '@/assets/images/FileTypeFile';
import FileTypeImage from '@/assets/images/FileTypeImage';
import { Tabs } from '@/components/Form/Tabs';
import Colors from '@/configs/Colors';
import { CustomRoutes } from '@/services/API';

import useAPI from '../useAPI/useAPI';
import './DetailDevice.scss';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const DetailDevice = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [theme, _] = useTheme();
  const { pathname } = useLocation();
  const id = Number(pathname.split('/')[3]);
  const { getDetailDevice } = useAPI();
  const { converRawDateToDateFormat } = useConvertDate();

  const [activeTab, setActiveTab] = useState<number | undefined>(0);
  const [dataDetail, setDataDetail] = useState<any>({});

  const fetchData = async () => {
    const { success, data, message } = await getDetailDevice({
      id: id,
      edit: false,
    });
    if (success) {
      setDataDetail(data);
    }
    if (!success) {
      // alert(message);
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [previewImage, setPreviewImage] = useState<string>('');
  const handlePreview = (file: any) => {
    if (!file.file_type.includes('image')) return null;
    setPreviewImage(file?.file_url);
    setPreviewOpen(true);
  };

  const data = [
    {
      mainTitle: t('Physical Specifications'),
      detailsSection: [
        {
          subTitle: t('Dimensions and weight'),
          list: [
            {
              label: t('Frame size'),
              value: dataDetail?.dimensions?.frame_size,
            },
            {
              label: t('Maximum Takeoff Weight (MTOW)'),
              value: dataDetail?.dimensions?.maximum_takeoff_weight,
            },
            {
              label: t('Payload Capacity'),
              value: dataDetail?.dimensions?.payload_capacity,
            },
            {
              label: t('Empty Weight'),
              value: dataDetail?.dimensions?.empty_weight,
            },
            {
              label: t('Frame Class'),
              value: dataDetail?.dimensions?.frame_class,
            },
            {
              label: t('Frame Type'),
              value: dataDetail?.dimensions?.frame_type,
            },
          ],
        },
        {
          subTitle: t('Propulsion System'),
          list: [
            {
              label: t('Number of Motors'),
              value: dataDetail?.propulsion_system?.number_of_motors,
            },
            {
              label: t('Motor Type'),
              value: dataDetail?.propulsion_system?.motor_type?.name,
            },
            {
              label: t('Motor Power'),
              value: dataDetail?.propulsion_system?.motor_power,
            },
            {
              label: t('Propeller Size'),
              value: dataDetail?.propulsion_system?.propeller_size,
            },
            {
              label: t('Battery Type'),
              value: dataDetail?.propulsion_system?.battery_type?.name,
            },
            {
              label: t('Battery Capacity'),
              value: dataDetail?.propulsion_system?.battery_capacity,
            },
            {
              label: t('Flight Time'),
              value: dataDetail?.propulsion_system?.flight_time,
            },
            {
              label: t('Charging Time'),
              value: dataDetail?.propulsion_system?.charging_time,
            },
            {
              label: t('Battery Type'),
              value: dataDetail?.propulsion_system?.battery_type__name,
            },
            {
              label: t('Motor Type'),
              value: dataDetail?.propulsion_system?.motor_type__name,
            },
          ],
        },
      ],
    },
    {
      mainTitle: t('Communication Systems'),
      detailsSection: [
        {
          subTitle: t('Radio Communication'),
          list: [
            {
              label: t('Frequency Band'),
              value: dataDetail?.radio_communication?.frequency,
            },
            {
              label: t('Range'),
              value: dataDetail?.radio_communication?.range,
            },
          ],
        },
        {
          subTitle: t('Telemetry'),
          list: [
            {
              label: t('Real-time flight data transmission'),
              value: dataDetail?.telemetry?.realtime_flight_data && t('Yes'),
            },
            {
              label: t('Video streaming (1080p)'),
              value: dataDetail?.telemetry?.video_streaming && t('Yes'),
            },
            {
              label: t('Battery status monitoring'),
              value:
                dataDetail?.telemetry?.battery_status_monitoring && t('Yes'),
            },
            {
              label: t('GPS position tracking'),
              value: dataDetail?.telemetry?.gps_position_tracking && t('Yes'),
            },
            {
              label: t('System health monitoring'),
              value:
                dataDetail?.telemetry?.system_health_monitoring && t('Yes'),
            },
          ],
        },
      ],
    },
    {
      mainTitle: t('Performance Specifications'),
      detailsSection: [
        {
          subTitle: t('Flight Performance'),
          list: [
            {
              label: t('Maximum Speed'),
              value: dataDetail?.flight_performance?.maximum_speed,
            },
            {
              label: t('Cruise Speed'),
              value: dataDetail?.flight_performance?.cruise_speed,
            },
            {
              label: t('Maximum Altitude'),
              value: dataDetail?.flight_performance?.maximum_altitude,
            },
            {
              label: t('Operating Altitude'),
              value: dataDetail?.flight_performance?.operating_altitude,
            },
            {
              label: t('Maximum Range'),
              value: dataDetail?.flight_performance?.maximum_range,
            },
            {
              label: t('Wind Resistance (Up to)'),
              value: dataDetail?.flight_performance?.wind_resistance,
            },
          ],
        },
        {
          subTitle: t('Navigation and Control'),
          list: [
            {
              label: t('GPS Accuracy'),
              value: dataDetail?.navigation_control?.gps_accuracy,
            },
            {
              label: t('IMU'),
              value: dataDetail?.navigation_control?.imu,
            },
            {
              label: t('Barometric Altimeter'),
              value:
                dataDetail?.navigation_control?.barometric_altimeter &&
                t('Yes'),
            },
          ],
        },
      ],
    },
    {
      mainTitle: t('Communication Protocols'),
      detailsSection: [
        {
          subTitle: t(''),
          list: Array.isArray(dataDetail?.device_protocols)
            ? dataDetail?.device_protocols?.map((item: any) => ({
              label: i18next.t(item.type),
              value: item.name,
            }))
            : [],
        },
      ],
    },
  ];
  const payloadAndSensorSystems = [
    {
      mainTitle: t('Payload Systems'),
      detailsSection: [
        {
          subTitle: t('Cargo Compartment'),
          list: [
            {
              label: t('Dimensions'),
              value: dataDetail?.cargo_compartments?.dimensions,
            },
            {
              label: t('Weight Capacity'),
              value: dataDetail?.cargo_compartments?.weight_capacity,
            },
            {
              label: t('Temperature Control'),
              value:
                dataDetail?.cargo_compartments?.temperature_control && t('Yes'),
            },
            {
              label: t('Secure locking mechanism'),
              value: dataDetail?.cargo_compartments?.secure_locking && t('Yes'),
            },
            {
              label: t('Quick-release system'),
              value: dataDetail?.cargo_compartments?.quick_release && t('Yes'),
            },
          ],
        },
      ],
    },
    {
      mainTitle: t('Surveillance Systems'),
      detailsSection: dataDetail?.surveillance_systems?.map(
        (item: any, index: number) => ({
          subTitle: `${t('Camera')} ${index + 1}`,
          list: [
            {
              label: t('Type'),
              value: item.name,
            },
            {
              label: t('Resolution'),
              value: item.resolution,
            },
            {
              label: t('Frame Rate (FPS)'),
              value: item.frame_rate,
            },
            {
              label: t('Field of View (FOV)'),
              value: item.field_of_view,
            },
            {
              label: t('Weight'),
              value: item.weight,
            },
            {
              label: t('Image Stabilization'),
              value: item.image_stabilization__name,
            },
            {
              label: t('Note'),
              value: item.note,
            },
          ],
        }),
      ),
    },
    {
      mainTitle: t('Packaging Specifications'),
      detailsSection: dataDetail?.packaging_specification?.map(
        (item: any, index: number) => ({
          subTitle: `${t('Option')} ${index + 1}`,
          list: item?.specifications?.map((item: any) => ({
            label: item?.name + ' (' + item?.code + ') ',
            value: {
              dimensions: item?.dimensions,
              max_weight: item?.max_weight,
            },
          })),
        }),
      ),
    },
    {
      mainTitle: t('Sensor Suite'),
      detailsSection: [
        {
          subTitle: t(''),
          list: [
            {
              label: t('GNSS'),
              value: dataDetail?.sensor_suite?.gnss
                .map((item: any) => item.name)
                .join(', '),
            },
            {
              label: t('Optical Flow Sensor'),
              value: dataDetail?.sensor_suite?.optical_flow_sensor && t('Yes'),
            },
            {
              label: t('Ultrasonic Sensors'),
              value: dataDetail?.sensor_suite?.ultrasonic_sensors && t('Yes'),
            },
            {
              label: t('LIDAR for obstacle detection'),
              value: dataDetail?.sensor_suite?.lidar && t('Yes'),
            },
            {
              label: t('AIS (Automatic Identification System)'),
              value: dataDetail?.sensor_suite?.ais && t('Yes'),
            },
            {
              label: t('ADS-B receiver'),
              value: dataDetail?.sensor_suite?.ads_b_receiver && t('Yes'),
            },
            {
              label: t('RF signal detector'),
              value: dataDetail?.sensor_suite?.rf_signal_detector && t('Yes'),
            },
            {
              label: t('Chemical sensor array'),
              value:
                dataDetail?.sensor_suite?.chemical_sensor_array && t('Yes'),
            },
            {
              label: t('Radiation detector'),
              value: dataDetail?.sensor_suite?.radiation_detector && t('Yes'),
            },
            {
              label: t('Weather sensors'),
              value: dataDetail?.sensor_suite?.weather_sensors && t('Yes'),
            },
          ],
        },
      ],
    },
  ];
  const regulatoryAndOperational = [
    {
      mainTitle: t('Manufacturers'),
      detailsSection: [
        {
          subTitle: t('Drone Manufacturing Information'),
          list: [
            {
              label: t('Manufacturer'),
              value: dataDetail?.manufacturer_information?.manufacturer,
            },
            {
              label: t('Country of Origin'),
              value:
                dataDetail?.manufacturer_information?.country_of_origin__name,
            },
            {
              label: t('Model / Product Code'),
              value: dataDetail?.manufacturer_information?.model_number,
            },
            {
              label: t('Serial Number'),
              value: dataDetail?.manufacturer_information?.serial_number,
            },
            {
              label: t('Production Date'),
              value:
                converRawDateToDateFormat(dataDetail?.manufacturer_information?.production_date) || null,
            },
            {
              label: t('Registration Number'),
              value:
                dataDetail?.manufacturer_information?.registration_number || null,
            },
            {
              label: t('Note'),
              value: dataDetail?.manufacturer_information?.device?.note,
            },
          ],
        },
        {
          subTitle: t('Drone Insurance Information'),
          list: [
            {
              label: t('Insurance Status'),
              value:
                dataDetail?.manufacturer_information?.insurance_status &&
                t('Yes'),
            },
            {
              label: t('Insurance Type'),
              value: dataDetail?.manufacturer_information?.insurance_type,
            },
            {
              label: t('Insurance Provider'),
              value: dataDetail?.manufacturer_information?.insurance_provider,
            },
            {
              label: t('Policy Number'),
              value: dataDetail?.manufacturer_information?.policy_number,
            },
            {
              label: t('Validity Period'),
              value:
                dataDetail?.manufacturer_information?.validity_period_from &&
                  dataDetail?.manufacturer_information?.validity_period_to
                  ? converRawDateToDateFormat(dataDetail?.manufacturer_information?.validity_period_from) +
                  ' - ' +
                  converRawDateToDateFormat(dataDetail?.manufacturer_information?.validity_period_to)
                  : null,
            },
            {
              label: t('Current Status'),
              value:
                dataDetail?.manufacturer_information?.current_status?.[0]?.toUpperCase() +
                dataDetail?.manufacturer_information?.current_status
                  ?.slice(1)
                  ?.toLowerCase(),
            },
          ],
        },
      ],
    },
    {
      mainTitle: t('Environmental Specifications'),
      detailsSection: [
        {
          subTitle: t('Operating Conditions'),
          list: [
            {
              label: t('Temperature Range'),
              value: dataDetail?.environmental_specification?.temperature_range,
            },
            {
              label: t('Humidity'),
              value: dataDetail?.environmental_specification?.humidity,
            },
            {
              label: t('Precipitation'),
              value: dataDetail?.environmental_specification?.precipitation,
            },
            {
              label: t('Wind Speed'),
              value: dataDetail?.environmental_specification?.wind_speed,
            },
          ],
        },
        {
          subTitle: t('Noise Levels'),
          list: [
            {
              label: t('Takeoff'),
              value: dataDetail?.environmental_specification?.noise_takeoff,
            },
            {
              label: t('Cruise'),
              value: dataDetail?.environmental_specification?.noise_cruise,
            },
            {
              label: t('Landing'),
              value: dataDetail?.environmental_specification?.noise_landing,
            },
          ],
        },
      ],
    },

    {
      mainTitle: t('Safety Features'),
      detailsSection: [
        {
          subTitle: t('Redundancy Systems'),
          list: [
            {
              label: t('Dual IMU'),
              value: dataDetail?.safety_feature?.dual_imu && t('Yes'),
            },
            {
              label: t('Dual GPS'),
              value: dataDetail?.safety_feature?.dual_gps && t('Yes'),
            },
            {
              label: t('Dual battery system'),
              value: dataDetail?.safety_feature?.dual_battery && t('Yes'),
            },
            {
              label: t('Emergency parachute system'),
              value:
                dataDetail?.safety_feature?.emergency_parachute && t('Yes'),
            },
            {
              label: t('Return-to-home (RTH) capability'),
              value: dataDetail?.safety_feature?.return_to_home && t('Yes'),
            },
          ],
        },
        {
          subTitle: t('Collision Avoidance'),
          list: [
            {
              label: t('360° obstacle detection'),
              value:
                dataDetail?.safety_feature?.obstacle_detection_360 && t('Yes'),
            },
            {
              label: t('Forward-facing stereo cameras'),
              value: dataDetail?.safety_feature?.stereo_cameras && t('Yes'),
            },
            {
              label: t('LIDAR-based obstacle mapping'),
              value: dataDetail?.safety_feature?.lidar_mapping && t('Yes'),
            },
            {
              label: t('Automatic emergency braking'),
              value: dataDetail?.safety_feature?.emergency_braking && t('Yes'),
            },
          ],
        },
      ],
    },
  ];
  const content = (type: string) => {
    return (
      <div className={`detail-device ${theme}`}>
        {(type === 'technical-specifications'
          ? data
          : type === 'payload-and-sensor-systems'
            ? payloadAndSensorSystems
            : type === 'regulatory-and-operational-information'
              ? regulatoryAndOperational
              : []
        )
          .filter((item) =>
            item.detailsSection?.some((section) =>
              section.list?.some((listItem) => listItem.value),
            ),
          )
          .map((item, index) => (
            <div
              className={`detail-device__section ${theme}`}
              key={index}
            >
              <div className={`detail-device__section-title ${theme}`}>
                {item.mainTitle}
              </div>

              {item.detailsSection
                .filter((section) =>
                  section.list?.some((listItem) => listItem.value),
                )
                .map((section, idx) => (
                  <div
                    className={`detail-device__section-item ${theme}`}
                    key={idx}
                  >
                    {section.subTitle && (
                      <div className="detail-device__subsection-title">
                        {section.subTitle}
                      </div>
                    )}

                    <ul className="detail-device__list">
                      {section.list.map((listItem, i) => {
                        if (!listItem.value) return null;

                        return (
                          <li
                            className={`detail-device__list-item ${theme}`}
                            key={i}
                          >
                            <span className="detail-device__label">
                              {listItem.label}
                            </span>

                            {typeof listItem.value === 'object' ? (
                              // Đối với giá trị là object
                              listItem.value.dimensions ? (
                                <span className="detail-device__value d-flex flex-column align-items-end">
                                  <span>{listItem.value.dimensions}</span>
                                  <span>{listItem.value.max_weight}</span>
                                </span>
                              ) : (
                                // Xử lý object khác không có dimensions
                                <span className="detail-device__value">
                                  {JSON.stringify(listItem.value)}
                                </span>
                              )
                            ) : (
                              // Đối với giá trị không phải object
                              <span className="detail-device__value">
                                {String(listItem.value)}
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
            </div>
          ))}
      </div>
    );
  };

  const userInfo = useUserInfo();
  const isGroupEtri =
    (userInfo as any)?.profile__group__code === 'group_etri' ? true : false;

  const listTabs = [
    {
      label: t('Technical Specifications'),
      content: content('technical-specifications'),
    },
    {
      label: t('Payload and Sensor Systems'),
      content: content('payload-and-sensor-systems'),
    },
    ...(!isGroupEtri
      ? [
        {
          label: t('Regulatory and Operational Information'),
          content: content('regulatory-and-operational-information'),
        },
      ]
      : []),
    {
      label: t('Attachments'),
      content: dataDetail?.file_attachments?.length > 0 && (
        <FormBlock>
          <div className={`attachment-device ${theme}`}>
            {dataDetail?.file_attachments?.map((item: any, index: any) => (
              <div
                onClick={() => handlePreview(item)}
                key={index}
                className={`file-upload__file-item  ${theme}`}
              >
                <>
                  <span>
                    {item?.file_type.includes('image') ? (
                      <FileTypeImage
                        color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
                      />
                    ) : (
                      <FileTypeFile
                        color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
                      />
                    )}
                  </span>
                  <span className="file-upload__file-name">
                    {item?.file_name}
                  </span>
                </>
                <a
                  href={
                    // item?.file_url.includes("media")
                    // ? import.meta.env.VITE_API_URL + item?.file_url.replace(/^\/+/, "") :
                    // import.meta.env.VITE_API_URL + item?.file_url
                    import.meta.env.VITE_API_URL + item?.file_url
                  }
                  download={
                    // item?.file_url.includes("media")
                    // ? import.meta.env.VITE_API_URL + item?.file_url.replace(/^\/+/, "") :
                    // import.meta.env.VITE_API_URL + item?.file_url
                    import.meta.env.VITE_API_URL + item?.file_url
                  }
                >
                  {' '}
                  <DownLoad
                    color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
                  />
                </a>
              </div>
            ))}
          </div>
          {previewImage && (
            <Image
              wrapperStyle={{ display: 'none' }}
              preview={{
                visible: previewOpen,
                onVisibleChange: (visible) => setPreviewOpen(visible),
                afterOpenChange: (visible) => !visible && setPreviewImage(''),
              }}
              src={previewImage}
            />
          )}
        </FormBlock>
      ),
    },
  ];

  return (
    <>
      <CustomBreadcrumb
        items={[{ url: '/device' }, { text: 'Detailed Information' }]}
        buttons={[
          <CustomBtn
            variant="outline"
            color="primary"
            actionType={ROLE_PERMISSION.UPDATE}
            label={t('Edit')}
            onClick={() =>
              navigate(
                CustomRoutes.device.subRoutes.editDevice.path.replace(
                  ':id',
                  id.toString(),
                ),
              )
            }
          />,
        ]}
      />
      <Main>
        <Tabs
          items={listTabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </Main>
    </>
  );
};

export default DetailDevice;
