import { notification } from 'antd';
import { t } from 'i18next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { GoPlus } from 'react-icons/go';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  useConfigSystem,
  useUserInfo,
} from 'rj-core';

import SwitchBtn from '@/components/Form/SwitchBtn';
import API, { endpoint } from '@/services/API';
import { CheckRoleAccount } from '@/utils/CheckRoleAccount';
import { getContrastTextColor, remToPx } from '@/utils/utils';

import ButtonStatus from '../components/ButtonStatus';
import { CancelOrder } from '../components/CancelOrder';
import { ChangeStatus } from '../components/ChangeStatus';
import { useDeliveryInquiryData } from '../hooks/useDeliveryInquiryData';
import { useWebSocketDeliveryInquiry } from '../hooks/useWebSocketDeliveryInquiry';
import useAPI from '../useAPI';
import { formatStatusDeliveryInquiry } from '../utils/StatusColorInquiry';
import convertInfoNotification from '../utils/convertInfoNotification';
import './ListDeliveryInquiry.scss';
import { getDashboardLocation } from '@/utils/requestLocationPermission';
import { NominatimResponse, OpenMeteoResponse } from '@/features/Dashboard/SurveillanceDashboard/components/WeatherInfoSurveillance';

const BAD_CODE_RANGES: number[] = [
  -45, 48, - 51, 53, 55, - 61, 63, 65, - 66, 67, - 71, 73, 75, - 77 - 80, 81, 82, - 85, 86, - 95, 96, 99
];

const ListDeliveryInquiry = () => {
  const [api, contextHolder] = notification.useNotification();
  const navigate = useNavigate();
  const location = useLocation();
  const headerPageRef = useRef(null);
  const { cancelOrder, changeOrderStatus } = useAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');

  const {
    data,
    currentPage,
    pageSize,
    objSearch,
    setCurrentPage,
    setPageSize,
    setObjSearch,
    fetchData,
  } = useDeliveryInquiryData();

  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [showModal, setShowModal] = useState({
    delivery_id: null,
    show: {
      cancelOrder: false,
      changeStatus: false,
    },
  });

  const { isConnected, message } = useWebSocketDeliveryInquiry({
    socketUrl: `${import.meta.env.VITE_STREAMING_WS}/ws/orders/notifications/`,
  });

  const handleViewDetailDevice = useCallback(
    (selectedRow: { id: number }) => {
      navigate(`/delivery-inquiry/${selectedRow.id}`, {
        state: {
          id: selectedRow.id,
          previousUrl: location.pathname + location.search,
        },
      });
    },
    [navigate, location.pathname, location.search],
  );

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const HistoryBehaviorColumns = useMemo(
    () => [
      {
        Header: 'Order ID',
        accessor: 'order_code',
      },
      {
        Header: 'Order Time',
        accessor: 'created_on',
        filterVariant: 'datetime',
      },
      {
        Header: 'Sender',
        accessor: 'sender_name',
      },
      {
        Header: 'Recipient',
        accessor: 'recipient_name',
      },
      {
        Header: 'Status',
        accessor: 'status__name',
        enableColumnFilter: false,
        cell: (info: any) => {
          const currentStatusSystem = info.row.original?.mapped_status_code;
          const currentStatusName = info.row.original?.mapped_status;
          const currentTextColor = getContrastTextColor(
            info.row.original?.mapped_status_background_color,
          );
          const currentBackgroundColor =
            info.row.original?.mapped_status_background_color;
          const currentBorderColor =
            info.row.original?.mapped_status_border_color;
          const mappedListStatus = info.row.original?.mapped_status_list;

          return (
            <div
              style={{
                display: 'flex',
                gap: 8,
                width: 'fit-content',
                flexFlow: 'wrap',
              }}
            >
              {mappedListStatus?.length > 0
                ? mappedListStatus.map(
                  (item: {
                    name: string;
                    background_color: string;
                    text_color: string;
                    border_color: string;
                  }) =>
                    formatStatusDeliveryInquiry({
                      t,
                      status_name: item.name,
                      status_code: currentStatusSystem,
                      backgroundColor: item.background_color,
                      color: item.text_color,
                      border: item.border_color,
                      onClickAwaitingDelivery: () => {
                        setShowModal({
                          show: { changeStatus: true, cancelOrder: false },
                          delivery_id: info.row.original.id,
                        });
                      },
                      onClickCancelled: () => {
                        setShowModal({
                          show: { changeStatus: false, cancelOrder: true },
                          delivery_id: info.row.original.id,
                        });
                      },
                    }),
                )
                : currentStatusName &&
                currentStatusSystem &&
                currentBackgroundColor &&
                currentTextColor &&
                currentBorderColor &&
                formatStatusDeliveryInquiry({
                  t,
                  status_name: currentStatusName,
                  status_code: currentStatusSystem,
                  backgroundColor: currentBackgroundColor,
                  color: currentTextColor,
                  border: currentBorderColor,
                  onClickAwaitingDelivery: () => {
                    setShowModal({
                      show: { changeStatus: true, cancelOrder: false },
                      delivery_id: info.row.original.id,
                    });
                  },
                  onClickCancelled: () => {
                    setShowModal({
                      show: { changeStatus: false, cancelOrder: true },
                      delivery_id: info.row.original.id,
                    });
                  },
                })}
            </div>
          );
        },
      },
    ],
    [t, ButtonStatus], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const openNotification = ({
    title,
    description,
    color,
    backgroundColor,
  }: {
    title: string;
    description: {
      time: string | number;
      transport_route: string;
      order_code: string | number;
      recipient_name: string | number;
    };
    color: string;
    backgroundColor: string;
  }) => {
    api.open({
      message: (
        <h5
          style={{
            marginBottom: '0.25rem',
            color,
          }}
        >
          {title}
        </h5>
      ),
      description: (
        <div>
          <p
            style={{
              marginBottom: 0,
              fontWeight: 600,
            }}
          >
            {t('The status has been changed.') + ` (${description.time})`}
          </p>
          <p
            style={{
              marginBottom: 0,
            }}
          >
            {description.transport_route}
          </p>
          <p
            style={{
              marginBottom: 0,
            }}
          >
            <span style={{ fontWeight: 600 }}>{t('Order ID: ')}</span>{' '}
            {description.order_code}
          </p>
          <p
            style={{
              marginBottom: 0,
            }}
          >
            <span style={{ fontWeight: 600 }}>{t('Recipient: ')}</span>{' '}
            {description.recipient_name}
          </p>
        </div>
      ),
      duration: 0,
      className: 'info-notification',
      style: {
        width: 320,
        backgroundColor,
        padding: '1.5rem',
        borderRadius: '0.8rem',
      },
    });
  };

  useEffect(() => {
    if (isConnected && message) {
      const { title, description, color, backgroundColor } =
        convertInfoNotification(t, message);
      openNotification({
        title,
        description,
        color,
        backgroundColor,
      });
    }
  }, [isConnected, message]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCancelOrder = useCallback(
    async (id: number, reason: string) => {
      setLoading(true);
      const { success, message } = await cancelOrder(id, reason);
      if (success) {
        ToastTopHelper.success(message);
        setShowModal({
          show: { changeStatus: false, cancelOrder: false },
          delivery_id: null,
        });
        fetchData();
      } else {
        ToastTopHelper.error(message);
      }
      setLoading(false);
    },
    [cancelOrder, fetchData],
  );

  const [loading, setLoading] = useState<boolean>(false);
  const handleChangeStatus = useCallback(
    async (id: number) => {
      setLoading(true);
      const { success, message } = await changeOrderStatus(id);
      if (success) {
        ToastTopHelper.success(message);
        fetchData();
        setShowModal({
          show: { changeStatus: false, cancelOrder: false },
          delivery_id: null,
        });
      } else {
        ToastTopHelper.error(message);
      }
      setLoading(false);
    },
    [changeOrderStatus, fetchData],
  );

  const handleToggleOrderWeather = useCallback(async () => {
    try {
      const response = await API.put(endpoint.toggleOrderWeather);
      if (response.success) {
        ToastTopHelper.success(response.message);
        fetchData();
      } else {
        ToastTopHelper.error(response.message);
      }
      console.log('response', response);
    } catch (error) {
      console.log('error', error);
    }
  }, [fetchData]);

  const [isBadWeatherResult, setIsBadWeatherResult] = useState<boolean>(false);
  const fetchWeatherData = async (latitude: number, longitude: number) => {
    try {
      setLoading(true);
      const weatherResponse = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true`,
      );
      if (!weatherResponse.ok) {
        throw new Error('Failed to fetch weather data');
      }
      const weatherApiData: OpenMeteoResponse = await weatherResponse.json();
      const isBadWeatherResult = BAD_CODE_RANGES.includes(weatherApiData?.current_weather?.weathercode);
      setIsBadWeatherResult(isBadWeatherResult);
    } catch (error) {
      console.error('Error fetching weather data:', error);
    } finally {
      setLoading(false);
    }
  };
  const requestLocationAndFetchWeather = async () => {
    try {
      const location = await getDashboardLocation();
      if (location && location.latitude && location.longitude) {
        await fetchWeatherData(location.latitude, location.longitude);
      }
    } catch (error) {
      console.log('Location permission not granted or error occurred:', error);
    }
  };

  useEffect(() => {
    requestLocationAndFetchWeather();
  }, []);



  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      {contextHolder}
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Order')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            disabled={!data?.allow_order_in_bad_weather && isBadWeatherResult}
            onClick={() => {
              isRoleSuperuser
                ? ToastTopHelper.warning(
                  t(
                    'System accounts cannot create orders. Please log in with a member account to use this feature.',
                  ),
                )
                : navigate('/delivery-inquiry/add-new-order');
            }}
          />,
        ]}
      />
      <Main>
        <div className="list-device__table-container">
          <CustomizableTable
            stickyHeader
            notShowSelectRow
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDevice}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              setOpenOffcanvas(boolean);
            }}
            buttonGroups={[
              {
                position: 'top',
                align: 'left',
                buttons: [
                  <>
                    {t('Weather')}
                    <SwitchBtn
                      actionType={ROLE_PERMISSION.UPDATE}
                      statusValue={data?.allow_order_in_bad_weather}
                      onChange={() => {
                        handleToggleOrderWeather();
                      }}
                      loading={false}
                    />
                  </>,
                ],
              },
            ]}
          />
        </div>
      </Main>
      <CancelOrder
        loading={loading}
        showModal={showModal.show.cancelOrder}
        setHideModal={() => {
          setShowModal({
            show: { changeStatus: false, cancelOrder: false },
            delivery_id: null,
          });
        }}
        handleCancelOrder={(reason: string) => {
          if (showModal.delivery_id) {
            handleCancelOrder(showModal.delivery_id, reason);
          } else {
            ToastTopHelper.error(t('Cannot Get Order ID'));
          }
        }}
      />
      <ChangeStatus
        loading={loading}
        showModal={showModal.show.changeStatus}
        setHideModal={() => {
          setShowModal({
            show: { changeStatus: false, cancelOrder: false },
            delivery_id: null,
          });
        }}
        handleChangeStatus={() => {
          if (showModal.delivery_id) {
            handleChangeStatus(showModal.delivery_id);
          } else {
            ToastTopHelper.error(t('Cannot Get Order ID'));
          }
        }}
      />
    </Container>
  );
};
export default ListDeliveryInquiry;
