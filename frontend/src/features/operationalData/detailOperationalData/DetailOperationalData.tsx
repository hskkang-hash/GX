import { Box } from '@mui/material';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsDownload } from 'react-icons/bs';
import { MdOutlineRemoveRedEye } from 'react-icons/md';
import { useLocation } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  Main,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import CustomFieldBtn from '@/components/Form/CustomFieldBtn';
import { Map } from '@/components/maps';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

import useAPI from '../useAPI/useAPI';
import './DetailOperationalData.scss';

const noteMap = [
  { color: '#f43f3d', name: 'Drone' },
  { color: '#4EA72E', name: 'Robot' },
];

const DetailOperationalData = () => {
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { pathname } = useLocation();
  const id = Number(pathname.split('/')[3]);
  const {
    getDetailOperationalData,
    donwloadFileOperationalData,
    donwloadFileOperationalDataAll,
  } = useAPI();

  const [dataDetail, setDataDetail] = useState<any>({});

  const fetchData = async () => {
    if (!id) return;
    const { success, data, message } = await getDetailOperationalData(id);
    if (success) {
      setDataDetail(data);
    }
    if (!success) {
      ToastTopHelper.error(message);
    }
  };
  useEffect(() => {
    fetchData();
  }, []);

  const handleDownLoadAllFile = async (id: number) => {
    const { success, message } = await donwloadFileOperationalDataAll({
      id: [id],
      delivery_operation_code: dataDetail.delivery_operation_code,
    });
    if (success) {
      // ToastTopHelper.success(message);
    } else {
      console.log('Failed to download file', message);
      ToastTopHelper.error(message);
    }
  };

  const handleDownLoadFileLog = async ({
    id,
    type,
  }: {
    id: number;
    type: 'downloadFileDrone' | 'downloadFileRobot';
  }) => {
    const { success, message } = await donwloadFileOperationalData({
      id,
      type,
      delivery_operation_code: dataDetail.delivery_operation_code,
    });
    if (success) {
      // ToastTopHelper.success(message);
    } else {
      console.log('Failed to download file', message);
      ToastTopHelper.error(message);
    }
  };

  const handleRouteTerminal = useCallback(
    (route: any = [], isRobot: boolean) => {
      if (route.length === 0 || !Array.isArray(route)) return [];
      return route?.map(([lat, lng]: any) => ({
        lat: lat,
        lng: lng,
        for_robot: isRobot,
        name: `${lat} ${lng}`,
      }));
    },
    [],
  );

  const routeTerminalDrone = useMemo(
    () => handleRouteTerminal(dataDetail?.route_terminals_drone || [], false),
    [dataDetail?.route_terminals_drone, handleRouteTerminal],
  );
  const routeTerminalRobot = useMemo(
    () => handleRouteTerminal(dataDetail?.route_terminals_robot || [], true),
    [dataDetail?.route_terminals_robot, handleRouteTerminal],
  );
  const routeTerminal = useMemo(
    () =>
      routeTerminalDrone
        ? routeTerminalDrone?.concat(routeTerminalRobot)
        : routeTerminalRobot,
    [routeTerminalDrone, routeTerminalRobot],
  );

  return (
    <>
      <CustomBreadcrumb
        items={[{ url: '/operational-data' }, { text: 'Detailed Information' }]}
        buttons={[
          <CustomBtn
            variant="contained"
            color="primary"
            label={t('Download')}
            onClick={() => handleDownLoadAllFile(dataDetail.id)}
          />,
        ]}
      />
      <Main>
        <Box
          sx={{
            position: 'relative',
            width: '100%',
            height: '550px',
            borderRadius: '10px',
          }}
        >
          <Map
            operatingMarkers={
              routeTerminal?.length > 0
                ? routeTerminal?.map((stop: any) => ({
                    lat: stop.lat,
                    lng: stop.lng,
                    name: stop.name,
                    for_robot: stop.for_robot,
                  }))
                : []
            }
            polylines={
              routeTerminal?.length > 1
                ? [
                    routeTerminal?.map((stop: any) => ({
                      lat: stop.lat,
                      lng: stop.lng,
                      for_robot: stop.for_robot,
                    })),
                  ]
                : []
            }
            style={{ height: 550, borderRadius: '10px' }}
          />
          <Box
            sx={{
              position: 'absolute',
              bottom: '56px',
              right: '16px',
              zIndex: 500,
            }}
          >
            <Box
              sx={{
                padding: '10px',
                borderRadius: '8px',
                backgroundColor:
                  theme == 'dark'
                    ? 'rgb(68, 68, 68)'
                    : 'rgba(255, 255, 255, 0.5)',
                // backdropFilter: 'blur(4px)',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                border:
                  theme == 'dark' ? '1px solid #44464' : '1px solid #DDDFE2',
                fontSize: '14px',
                gap: '12px',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {noteMap.map((item, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <Box
                    sx={{
                      width: '12px',
                      height: '12px',
                      backgroundColor: item.color,
                      borderRadius: '50%',
                    }}
                  ></Box>{' '}
                  <Box
                    sx={{
                      fontSize: '14px',
                      color: theme == 'dark' ? '#fff' : '#000',
                    }}
                  >
                    {' '}
                    {t(item.name)}{' '}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
        <Box>
          <Box
            sx={{
              fontSize: '1.25rem',
              fontWeight: '600',
              py: '16px',
            }}
          >
            {t('Operational Data')}
          </Box>
          <table className="table-operational-data">
            <tbody>
              <tr>
                <th>{t('Tracking Number')}</th>
                <td>{dataDetail.delivery_operation_code || '-'}</td>
                <th>{t('Receipt Number')}</th>
                <td>{dataDetail.receipt_id || '-'}</td>
                <th>{t('Delivery Date')}</th>
                <td>
                  {converRawDateToDateTimeFormat(dataDetail.delivered_at) ||
                    '-'}
                </td>
                <th>{t('Reception Date')}</th>
                <td>
                  {converRawDateToDateTimeFormat(
                    dataDetail.delivery_operation__created_on,
                  ) || '-'}
                </td>
                <th>{t('Operation Log Check')}</th>
                <td>
                  <div className="operation-log-check">
                    <CustomFieldBtn
                      label={t('Drone')}
                      icon={<BsDownload size={16} />}
                      onClick={() => {
                        handleDownLoadFileLog({
                          id: dataDetail.id,
                          type: 'downloadFileDrone',
                        });
                      }}
                    />
                    <CustomFieldBtn
                      label={t('Robot')}
                      icon={<BsDownload size={16} />}
                      onClick={() => {
                        handleDownLoadFileLog({
                          id: dataDetail.id,
                          type: 'downloadFileRobot',
                        });
                      }}
                    />
                  </div>
                </td>
              </tr>
              <tr>
                <th>{t('Route')}</th>
                <td className="route-td">{dataDetail.route || '-'}</td>
                <th>{t('Delivery Point')}</th>
                <td>{dataDetail.delivery_point || '-'}</td>
                <th>{t('Item Type')}</th>
                <td>{dataDetail.item_type || '-'}</td>
                <th>{t('Weight')}</th>
                <td>
                  {dataDetail?.item_weight?.includes('null')
                    ? '-'
                    : dataDetail.item_weight}
                </td>
                <th>{t('Video Check')}</th>
                <td>
                  <div className="operation-log-check">
                    <CustomFieldBtn
                      label={t('Drone')}
                      icon={<MdOutlineRemoveRedEye size={16} />}
                      onClick={() => {}}
                      action="view"
                      videoUrl={dataDetail?.drone_video_path}
                      isDisabled={dataDetail?.drone_video_path === 'N/A'}
                    />
                    <CustomFieldBtn
                      label={t('Robot')}
                      icon={<MdOutlineRemoveRedEye size={16} />}
                      onClick={() => {}}
                      action="view"
                      videoUrl={dataDetail?.robot_video_path}
                      isDisabled={dataDetail?.robot_video_path === 'N/A'}
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </Box>
      </Main>
    </>
  );
};

export default DetailOperationalData;
