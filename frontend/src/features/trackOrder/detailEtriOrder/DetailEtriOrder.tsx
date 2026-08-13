import { useEffect, useState, useMemo } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  Main,
  ToastTopHelper,
  useLoadingContext,
  useTheme,
} from 'rj-core';

import MapPoint from '@/components/maps/MapPoint';
import Colors from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import useBoolean from '@/hooks/useBoolean';
import { CustomRoutes } from '@/services/API';
import MapDistanceCalculator from '@/utils/MapDistanceCalculator';
import { formatStatusEtri } from '@/utils/formatColumns';

import useAPI from '../useAPI/useAPI';
import './DetailEtriOrder.scss';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

interface OrderItem {
  item_type__name: string;
  dimension_w: { value: number; unit: string };
  dimension_l: { value: number; unit: string };
  dimension_h: { value: number; unit: string };
  package_details: string;
  note: string;
}

interface OrderMapData {
  DRONE_PATH?: [number, number][];
  ROBOT_PATH?: [number, number][];
}

interface LocationState {
  orderMap?: OrderMapData;
}

const DetailEtriOrder = () => {
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [theme] = useTheme();

  const { getDetailOrder, sendingReceptionInfo } = useAPI();
  const { pathname, state } = useLocation() as {
    pathname: string;
    state: LocationState;
  };

  const [showModal, openModal, setHideModal] = useBoolean();
  const orderMapFromState = state?.orderMap;
  const id = Number(pathname.split('/')[2]);
  const operation_id = Number(pathname.split('/')[3]);

  const [detailOrder, setDetailOrder] = useState<any>({});

  // Extract path data from detailOrder.another_info.etri.receive_data
  // Fallback to orderMap from state if receive_data is not available
  const orderMap = useMemo(() => {
    const receiveData = detailOrder?.another_info?.etri?.receive_data;
    if (receiveData?.DRONE_PATH || receiveData?.ROBOT_PATH) {
      return {
        DRONE_PATH: receiveData.DRONE_PATH || [],
        ROBOT_PATH: receiveData.ROBOT_PATH || [],
        DOCKING_POINT: receiveData.DOCKING_POINT || [],
      };
    }
    return orderMapFromState;
  }, [detailOrder?.another_info?.etri?.receive_data, orderMapFromState]);

  console.log({ orderMap });
  console.log('detailOrder', detailOrder);

  const { showLoading, hideLoading } = useLoadingContext();
  const fetchDataDetailOrder = async () => {
    showLoading();
    const { success, data, message } = await getDetailOrder({
      id: id,
      edit: false,
    });

    console.log('data', data);
    setDetailOrder(data);
    if (!success) {
      ToastTopHelper.error(message);
    }
    hideLoading();
  };
  useEffect(() => {
    fetchDataDetailOrder();
  }, []);

  const handleSendReceptionInformation = async () => {
    const { success, message, data } = await sendingReceptionInfo({
      operation_id: operation_id,
    });
    console.log('data', data);
    console.log('success', success);
    if (success) {
      fetchDataDetailOrder();
    }
    if (!success) {
      ToastTopHelper.error(message);
    }
  };
  const { getAddressByLatLongSafe } = useCommonAPI();

  const dronePathStart = orderMap?.DRONE_PATH?.[0];
  const dronePathEnd = orderMap?.DRONE_PATH?.[orderMap?.DRONE_PATH?.length - 1];
  const robotPathStart = orderMap?.ROBOT_PATH?.[0];
  const robotPathEnd = orderMap?.ROBOT_PATH?.[orderMap?.ROBOT_PATH?.length - 1];

  console.log('dronePathStart', dronePathStart);
  console.log('dronePathEnd', dronePathEnd);
  console.log('robotPathStart', robotPathStart);
  console.log('robotPathEnd', robotPathEnd);

  const [droneStartAddress, setDroneStartAddress] = useState<string>('');
  const [droneEndAddress, setDroneEndAddress] = useState<string>('');
  const [robotStartAddress, setRobotStartAddress] = useState<string>('');
  const [robotEndAddress, setRobotEndAddress] = useState<string>('');
  // const [droneDistance, setDroneDistance] = useState<number>(0);
  // const [robotDistance, setRobotDistance] = useState<number>(0);

  console.log('droneStartAddress', droneStartAddress);
  console.log('droneEndAddress', droneEndAddress);
  console.log('robotStartAddress', robotStartAddress);
  console.log('robotEndAddress', robotEndAddress);
  // console.log("droneDistance", droneDistance)
  // console.log("robotDistance", robotDistance)

  const fetchRegionByLatLong = async (
    lat: number,
    long: number,
    type: string,
  ) => {
    if (!lat || !long) return;
    const { data, status } = await getAddressByLatLongSafe(lat, long);

    if (type === 'drone_start') {
      setDroneStartAddress(data?.address_name || '');
    }
    if (type === 'drone_end') {
      setDroneEndAddress(data?.address_name || '');
    }
    if (type === 'robot_start') {
      setRobotStartAddress(data?.address_name || '');
    }
    if (type === 'robot_end') {
      setRobotEndAddress(data?.address_name || '');
    }

    if (!status) {
      return;
    }
  };

  useEffect(() => {
    if (dronePathStart) {
      fetchRegionByLatLong(dronePathStart[0], dronePathStart[1], 'drone_start');
    }
    if (dronePathEnd) {
      fetchRegionByLatLong(dronePathEnd[0], dronePathEnd[1], 'drone_end');
    }
    if (robotPathStart) {
      fetchRegionByLatLong(robotPathStart[0], robotPathStart[1], 'robot_start');
    }
    if (robotPathEnd) {
      fetchRegionByLatLong(robotPathEnd[0], robotPathEnd[1], 'robot_end');
    }
  }, [dronePathStart, dronePathEnd, robotPathStart, robotPathEnd]);

  // const getDistanceFromLatLonInKm = (
  //   lat1: number,
  //   lon1: number,
  //   lat2: number,
  //   lon2: number
  // ): number => {
  //   const toRad = (value: number) => (value * Math.PI) / 180;

  //   const R = 6371; // Bán kính Trái Đất theo km
  //   const dLat = toRad(lat2 - lat1);
  //   const dLon = toRad(lon2 - lon1);
  //   const a =
  //     Math.sin(dLat / 2) * Math.sin(dLat / 2) +
  //     Math.cos(toRad(lat1)) *
  //     Math.cos(toRad(lat2)) *
  //     Math.sin(dLon / 2) *
  //     Math.sin(dLon / 2);
  //   const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  //   const distance = R * c;

  //   return distance;
  // };

  // useEffect(() => {
  //   if (dronePathStart && dronePathEnd) {
  //     const distance = (getDistanceFromLatLonInKm(dronePathStart[0], dronePathStart[1], dronePathEnd[0], dronePathEnd[1])).toFixed(2);
  //     console.log("distance", distance)
  //     setDroneDistance(Number(distance))
  //   }
  //   if (robotPathStart && robotPathEnd) {
  //     const distance = (getDistanceFromLatLonInKm(robotPathStart[0], robotPathStart[1], robotPathEnd[0], robotPathEnd[1])).toFixed(2);
  //     console.log("distance", distance)
  //     setRobotDistance(Number(distance))
  //   }
  // }, [dronePathStart, dronePathEnd])

  const droneDistanceRoute =
    orderMap?.DRONE_PATH?.length && orderMap?.DRONE_PATH?.length > 0
      ? orderMap?.DRONE_PATH?.map((item: any) => {
        return {
          lat: item[0],
          lng: item[1],
        };
      })
      : '-';
  const robotDistanceRoute =
    orderMap?.ROBOT_PATH?.length && orderMap?.ROBOT_PATH?.length > 0
      ? orderMap?.ROBOT_PATH?.map((item: any) => {
        return {
          lat: item[0],
          lng: item[1],
        };
      })
      : '-';

  const methods = useForm({
    defaultValues: {
      reason: t('담당자 취소'),
    },
  });

  const { control, setValue, reset, watch } = methods;

  const { cancelOrder } = useAPI();

  const handleCancelOrder = async (reason: any) => {
    if (!reason || !id) {
      return null;
    }
    const { success, message } = await cancelOrder(id, reason);
    if (success) {
      ToastTopHelper.success(message);
      navigate(CustomRoutes.trackOrder.path);
    }
    if (!success) {
      ToastTopHelper.error(message);
    }
  };

  const [droneDistance, setDroneDistance] = useState(0);
  const [robotDistance, setRobotDistance] = useState(0);

  const totalDistanceAll = droneDistance + robotDistance;
  console.log('totalDistanceAll', totalDistanceAll);

  return (
    <>
      <CustomBreadcrumb
        items={[
          { url: '/etri-tracking' },
          { text: t('etri.Delivery Details') },
        ]}
        buttons={[
          <CustomBtn
            variant="contain"
            className="btn-send-reception"
            label={t('etri.Sending reception information')}
            onClick={() => handleSendReceptionInformation()}
            disabled={detailOrder?.mapped_status?.code !== 'unverified_order'}
          />,
          <CustomBtn
            variant="contained"
            className="btn-cancel-order"
            label={t('etri.Cancel Order')}
            style={{ paddingLeft: '16px', paddingRight: '16px' }}
            disabled={detailOrder?.mapped_status?.code !== 'unverified_order'}
            onClick={openModal}
          />,
        ]}
      />
      <Main>
        {detailOrder?.items ? (
          <div>
            {detailOrder?.items?.map((item: OrderItem, index: number) => (
              <>
                <section className="section-table">
                  <div className="title-table">
                    {t('etri.Reception Information')}
                  </div>
                  <div className="delivery-table-container">
                    <table className="delivery-table">
                      <tbody>
                        <tr>
                          <th className="should-wrap">
                            {t('etri.Reception Number')}
                          </th>
                          <td colSpan={2}>
                            {detailOrder?.another_info?.etri?.receipt_id || '-'}
                          </td>
                          <th> {t('etri.Reception Date')}</th>
                          <td colSpan={2}>
                            {detailOrder?.recipient_address__created_on || '-'}
                          </td>
                          <th> {t('etri.Item Type')}</th>
                          <td>{item?.item_type__name || '-'}</td>
                          <th> {t('etri.Item Weight (kg)')}</th>
                          <td>{item?.weight?.value || '-'}</td>
                        </tr>
                        <tr>
                          <th> {t('etri.Sender')}</th>
                          <td>{detailOrder?.sender_name || '-'}</td>
                          <td>{detailOrder?.sender_phone || '-'}</td>
                          <th> {t('etri.Receiver')}</th>
                          <td>{detailOrder?.recipient_name || '-'}</td>
                          <td>{detailOrder?.recipient_phone || '-'}</td>
                          <th className="should-wrap">
                            {' '}
                            {t('etri.Item Dimensions (cm)')}
                          </th>
                          <td>
                            {item?.dimension_w?.value +
                              item?.dimension_w?.unit +
                              ' x ' +
                              item?.dimension_l?.value +
                              item?.dimension_l?.unit +
                              ' x ' +
                              item?.dimension_h?.value +
                              item?.dimension_h?.unit || '-'}
                          </td>
                          <th style={{ textWrap: 'nowrap' }}>
                            {' '}
                            {t('etri.Note')}
                          </th>
                          <td>{detailOrder?.recipient_note || '-'}</td>
                        </tr>
                        <tr>
                          <th> {t("etri.Sender's Address")}</th>
                          <td colSpan={5}>
                            {detailOrder?.sender_address__full_address || '-'}
                          </td>
                          <th> {t("etri.Receiver's Address")}</th>
                          <td colSpan={3}>
                            {detailOrder?.recipient_address__full_address ||
                              '-'}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>
                <br />
              </>
            ))}
            {detailOrder?.mapped_status?.code !== 'unverified_order' && (
              <section className="section-table">
                <div className="title-table">
                  {t('etri.Shipping Information')}
                </div>
                <div className="delivery-table-container">
                  <table className="delivery-table">
                    <tbody>
                      <tr>
                        <th rowSpan={2}>{t('etri.Tracking Number')}</th>
                        <td
                          style={{ width: '26rem' }}
                          rowSpan={2}
                        >
                          {detailOrder?.another_info?.etri?.tracking_number ||
                            '-'}
                        </td>
                        <th style={{ width: '13rem' }}>
                          {t('etri.Reception Date')}
                        </th>
                        <td style={{ width: '22rem' }}>
                          {converRawDateToDateTimeFormat(detailOrder?.verified_time) || '-'}
                        </td>
                        <th>{t('etri.Status')}</th>
                        <td
                          className="should-wrap"
                          style={{ minWidth: '12rem', textAlign: 'center' }}
                        >
                          {formatStatusEtri(
                            detailOrder?.mapped_status?.name,
                            t,
                          )}
                        </td>
                        <th rowSpan={2}> {t('etri.Distance (Km)')}</th>
                        <td rowSpan={2}>
                          {totalDistanceAll !== 0
                            ? totalDistanceAll.toFixed(2) + 'km'
                            : '-'}
                        </td>
                      </tr>
                      <tr>
                        <th style={{ borderLeft: '1px solid #888888' }}>
                          {t('etri.Delivery/Cancel Date')}
                        </th>
                        <td style={{ width: '22rem' }}>
                          {detailOrder?.delivered_time
                            ? converRawDateToDateTimeFormat(detailOrder?.delivered_time)
                            : detailOrder?.cancel_time
                              ? converRawDateToDateTimeFormat(detailOrder?.cancel_time)
                              : '-'}
                        </td>
                        <th className="should-wrap">
                          {t('etri.Cancellation Reason')}
                        </th>
                        <td>{detailOrder?.cancel_reason || '-'}</td>
                      </tr>
                      <tr>
                        <th className="should-wrap">
                          {t('etri.Departure Location')}
                        </th>
                        <td colSpan={3}>
                          {detailOrder?.pickup_location || '-'}
                        </td>
                        <th>{t('etri.Arrival Location')}</th>
                        <td
                          colSpan={3}
                        //  style={{ minWidth: "360px" }}
                        >
                          {detailOrder?.recipient_address__full_address || '-'}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            )}
            <br />

            {detailOrder?.mapped_status?.code === 'completed_order' && (
              <>
                {/* Shipped only use this section */}
                <section className="section-table">
                  <div className="title-table">
                    {t('etri.Route Information')}
                  </div>
                  <div className="delivery-table-container">
                    <table className="delivery-table">
                      <tbody>
                        <tr>
                          <th style={{ width: '18rem' }}>
                            {t('etri.Drone name')}
                          </th>
                          <td style={{ width: '36rem' }}>
                            {' '}
                            {t('Drone')} {Math.floor(Math.random() * 100) + 1}
                          </td>
                          <th style={{ width: '18rem' }}>
                            {t('etri.Drone router')}
                          </th>
                          <td style={{ width: '36rem' }}> Drone Route 1</td>
                          <th style={{ width: '15rem' }}>
                            {t('etri.Starting location')}
                          </th>
                          <td style={{ width: '30rem' }}>
                            {droneStartAddress || '-'}
                          </td>
                          <th>{t('etri.Destination')}</th>
                          <td style={{ width: '20rem' }}>
                            {droneEndAddress || '-'}
                          </td>
                          <th style={{ width: '15rem' }}>
                            {' '}
                            {t('etri.Distance1')}
                          </th>
                          <td style={{ width: '7rem' }}>
                            {typeof droneDistanceRoute === 'object' ? (
                              <>
                                <MapDistanceCalculator
                                  positions={droneDistanceRoute}
                                  onDistanceCalculated={setDroneDistance}
                                />
                                {droneDistance.toFixed(2) + 'km'}
                              </>
                            ) : (
                              '-'
                            )}
                          </td>
                        </tr>
                        <tr>
                          <th>{t('etri.Robot name')}</th>
                          <td>
                            {t('Robot')} {Math.floor(Math.random() * 100) + 1}
                          </td>
                          <th>{t('etri.Robot router')}</th>
                          <td>Robot Route 1</td>
                          <th>{t('etri.Starting location')}</th>
                          <td>{robotStartAddress || '-'}</td>
                          <th>{t('etri.Destination')}</th>
                          <td>{robotEndAddress || '-'}</td>
                          <th> {t('etri.Distance2')}</th>
                          <td>
                            {typeof robotDistanceRoute === 'object' ? (
                              <>
                                {' '}
                                <MapDistanceCalculator
                                  positions={robotDistanceRoute}
                                  onDistanceCalculated={setRobotDistance}
                                />
                                {robotDistance.toFixed(2) + 'km'}{' '}
                              </>
                            ) : (
                              '-'
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>
                <br />
                {/* Map Section */}
                {orderMap && (
                  <section className="section-table">
                    <div className="title-table">
                      {t('etri.Map Information')}
                    </div>
                    <div>
                      {orderMap && (
                        <MapPoint
                          polylines={[
                            {
                              path:
                                orderMap?.DRONE_PATH?.map(
                                  ([lat, lng]: [number, number]) => ({
                                    lat,
                                    lng,
                                  }),
                                ) || [],
                              strokeColor: '#2196F3',
                              strokeOpacity: 0.8,
                              strokeStyle: 'solid',
                              strokeWeight: 4,
                              type: 'DRONE',
                            },
                            {
                              path:
                                orderMap?.ROBOT_PATH?.map(
                                  ([lat, lng]: [number, number]) => ({
                                    lat,
                                    lng,
                                  }),
                                ) || [],
                              strokeColor: '#e74c3c',
                              strokeOpacity: 0.8,
                              strokeStyle: 'solid',
                              strokeWeight: 4,
                              type: 'ROBOT',
                            },
                          ]}
                          terminalAddress={{
                            droneStartAddress: {
                              lat: orderMap.DRONE_PATH?.[0]?.[0] || 0,
                              lng: orderMap.DRONE_PATH?.[0]?.[1] || 0,
                              name: droneStartAddress,
                            },
                            robotStartAddress: {
                              lat: orderMap.ROBOT_PATH?.[0]?.[0] || 0,
                              lng: orderMap.ROBOT_PATH?.[0]?.[1] || 0,
                              name: robotStartAddress,
                            },
                            droneEndAddress: {
                              lat:
                                orderMap.DRONE_PATH?.[
                                (orderMap.DRONE_PATH?.length || 1) - 1
                                ]?.[0] || 0,
                              lng:
                                orderMap.DRONE_PATH?.[
                                (orderMap.DRONE_PATH?.length || 1) - 1
                                ]?.[1] || 0,
                              name: droneEndAddress,
                            },
                            robotEndAddress: {
                              lat:
                                orderMap.ROBOT_PATH?.[
                                (orderMap.ROBOT_PATH?.length || 1) - 1
                                ]?.[0] || 0,
                              lng:
                                orderMap.ROBOT_PATH?.[
                                (orderMap.ROBOT_PATH?.length || 1) - 1
                                ]?.[1] || 0,
                              name: robotEndAddress,
                            },
                          }}
                          style={{ height: 650 }}
                        />
                      )}
                    </div>
                  </section>
                )}
              </>
            )}
          </div>
        ) : null}

        <FormProvider {...methods}>
          <form>
            <CustomModal
              title={t('Cancel Order')}
              show={showModal}
              onHide={() => {
                setValue('reason', '');
                setHideModal();
              }}
            >
              <div style={{ width: '45rem' }}>
                <div
                  style={{
                    fontSize: '14px',
                    paddingBottom: '20px',
                    color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                  }}
                  className=""
                >
                  {t(
                    "We'd love to know why you're cancelling—please share your reason.",
                  )}
                </div>
                <CustomInputHookForm
                  name="reason"
                  placeholder={t('Reason-Etri')}
                  control={control}
                />
              </div>
              <ActionBtn
                styles={{ maxWidth: '100%' }}
                leftButtons={[
                  <CustomBtn
                    type="button"
                    variant="contained"
                    color="primary"
                    size="lg"
                    disabled={watch('reason') === ''}
                    label={t('Confirm')}
                    onClick={() => {
                      handleCancelOrder(watch('reason'));
                    }}
                  />,
                ]}
                rightButtons={[
                  <CustomBtn
                    type="button"
                    variant="outline"
                    color="secondary"
                    size="lg"
                    onClick={() => {
                      setHideModal();
                      reset();
                    }}
                    label={t('Cancel')}
                  />,
                ]}
              />
            </CustomModal>
          </form>
        </FormProvider>
      </Main>
    </>
  );
};

export default DetailEtriOrder;
