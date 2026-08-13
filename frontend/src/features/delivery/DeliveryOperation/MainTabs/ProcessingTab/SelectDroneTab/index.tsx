import {
  Box,
  Typography,
  Skeleton,
  Radio,
  debounce,
  CircularProgress,
} from '@mui/material';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  CustomBtn,
  CustomizableTable,
  useCalculateHeight,
  useTheme,
  ToastTopHelper,
} from 'rj-core';

import MapKakao from '@/components/maps/MapKakao';
import { colorOpacity } from '@/configs/Colors';
import API, { endpoint } from '@/services/API';
import { remToPx } from '@/utils/utils';

import { Map } from '../../../../../../components/maps';
import { formatStatusDeliveryInquiry } from '../../../../deliveryInquiry/utils/StatusColorInquiry';
import { useOperationOrder } from '../../../hooks/useOperationOrder';
import OrderDetailModal from '../components/OrderDetailModal';

interface TableData {
  data: any[];
  totalItem: number;
  totalPage: number;
}

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, unknown>;
}

export default function SelectDroneTab() {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const {
    fetchOperationOrder,
    fetchPackageOfOrder,
    fetchConfirmDrone,
    fetchDronesByPackageId,
  } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);

  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [dronePage, setDronePage] = useState(1);
  const [drones, setDrones] = useState<any[]>([]);
  const [jsonData, setJsonData] = useState<any[]>([]);
  const [pageSize, setPageSize] = useState<number>();
  const [hasMoreDrones, setHasMoreDrones] = useState(true);
  const [listPackage, setListPackage] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null);
  const [isLoadingMoreDrones, setIsLoadingMoreDrones] = useState(false);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [refreshListDrone, setRefreshListDrone] = useState<boolean>(false);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [hasTriedLoadMoreDrones, setHasTriedLoadMoreDrones] = useState(false);
  const [selectedPackageIdx, setSelectedPackageIdx] = useState<string | null>(
    null,
  );
  const [selectedDroneIds, setSelectedDroneIds] = useState<
    Record<string, string>
  >({});
  const [selectedRowForDetail, setSelectedRowForDetail] = useState<any | null>(
    null,
  );
  const [droneLocation, setDroneLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 400],
  });

  const COLUMNS = [
    { Header: 'Order ID', accessor: 'order_id' },
    { Header: 'Order Time', accessor: 'order_time' },
    { Header: 'Sender', accessor: 'sender' },
    { Header: 'Recipient', accessor: 'recipient' },
    { Header: 'Creator', accessor: 'creator' },
    { Header: 'Number of Package', accessor: 'number_of_package' },
    {
      Header: 'Mapped Status',
      accessor: 'mapped_status',
      enableColumnFilter: false,
      cell: (info) => {
        const { t } = useTranslation();
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
            {mappedListStatus.map(
              (item: {
                name: string;
                code: string;
                background_color: string;
                text_color: string;
                border_color: string;
              }) =>
                formatStatusDeliveryInquiry({
                  t,
                  status_name: item.name,
                  status_code: item.code,
                  backgroundColor: item.background_color,
                  color: item.text_color,
                  border: item.border_color,
                }),
            )}
          </div>
        );
      },
    },
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: any) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            fetchOrderDetail(row?.row?.original.order__id);
            setIsDetailModalOpen(true);
          }}
        >
          <BsEye size={16} />
        </div>
      ),
      customStyle: { maxWidth: 20, textAlign: 'center' },
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
    },
  ] as const;

  // View order detail
  const handleViewOrderDetail = async (row: any) => {
    setSelectedPackageIdx(null);
    setDrones([]);

    setSelectedOrderId(Number(row.id));
    setSelectedOrder(row);
    if (row.order_id) {
      try {
        setListPackage([]);
        setDrones([]);
        setDronePage(1);
        setHasMoreDrones(true);
        setHasTriedLoadMoreDrones(false);
        const { data } = await fetchPackageOfOrder({
          page: 1,
          operation_id: Number(row.id),
        });
        const formatListPackage = data.map((item: any) => ({
          id: item?.id,
        }));

        if (formatListPackage.length > 0) {
          setListPackage(formatListPackage);
          setSelectedPackageIdx(formatListPackage[0]?.id);
          setSelectedDroneIds({});
        } else {
          setListPackage([]);
          setSelectedPackageIdx(null);
          setSelectedDroneIds({});
          setDrones([]);
        }
      } catch (error) {
        console.log('error handleViewOrderDetail', error);
      }
    }
  };

  // Confirm drone
  const handleConfirmDrone = async () => {
    try {
      const { success, message } = await fetchConfirmDrone(jsonData);
      if (success) {
        ToastTopHelper.success('Delivery drone selection successful.');
        setSelectedOrderId(null);
        setSelectedOrder(null);
        setListPackage([]);
        setSelectedPackageIdx(null);
        setSelectedDroneIds({});
        setDrones([]);
        setJsonData([]);
        setDroneLocation(null);
        setRefreshListDrone(true);
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      console.log('error handleConfirmDrone', error);
      ToastTopHelper.error('Failed to confirm drone');
    }
  };

  // Get order detail
  const fetchOrderDetail = async (orderId: string) => {
    const { success, data } = await API.get(
      endpoint.detailOrder(Number(orderId)),
    );
    if (success) {
      setSelectedRowForDetail(data);
    }
  };

  // Select drone and package for submit
  const handleDroneSelection = (droneId: string, packageId: string | null) => {
    if (!packageId) return;
    setSelectedDroneIds((prev) => ({
      ...prev,
      [packageId]: droneId,
    }));
  };

  // Load more drones
  const loadMoreDrones = async (packageId: string) => {
    if (isLoadingMoreDrones || !hasMoreDrones) return;
    setIsLoadingMoreDrones(true);
    try {
      const { data, hasMore } = await fetchDronesByPackageId({
        page: dronePage,
        operation_item_id: Number(packageId),
      });

      const formatDrones = data.map((item: any) => ({
        doneId: item?.id,
        id: item?.serial_number,
        model: item?.model_name || '',
        battery:
          item?.battery_capacity?.value + ' ' + item?.battery_capacity?.unit ||
          '',
        maxLoad:
          item?.weight_capacity?.value + ' ' + item?.weight_capacity?.unit ||
          '',
        droneLocation: item?.last_location
          ? {
              lat: item.last_location.latitude,
              lng: item.last_location.longitude,
            }
          : null,
      }));

      if (dronePage === 1) {
        setDrones(formatDrones);
      } else {
        setDrones((prev) => [...prev, ...formatDrones]);
      }

      if (formatDrones.length > 0 && !selectedDroneIds[packageId]) {
        handleDroneSelection(formatDrones[0].doneId, packageId);
        setDroneLocation(formatDrones[0].droneLocation);
      }

      setHasMoreDrones(hasMore);
      if (hasMore) {
        setDronePage((prev) => prev + 1);
      }
    } catch (error) {
      console.log('error loadMoreDrones', error);
      ToastTopHelper.error('Failed to get drones by package id');
    } finally {
      setIsLoadingMoreDrones(false);
    }
  };

  // Get drones by package id
  useEffect(() => {
    if (selectedPackageIdx) {
      setDronePage(1);
      setHasMoreDrones(true);
      setIsLoadingMoreDrones(false);
      loadMoreDrones(selectedPackageIdx);
    }
  }, [selectedPackageIdx, selectedOrder]);

  // Get list orders
  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: ['select_drone_processing'],
    };
    const response = await fetchOperationOrder({
      pageSize,
      currentPage,
      objSearch: objSearchFetch,
    });
    if (response) {
      setData({
        data: response.data,
        totalPage: response.totalPage,
        totalItem: response.totalItem,
      });
      if (!selectedOrderId && response && response.data.length > 0) {
        handleViewOrderDetail(response.data[0]);
      }
    }
  };

  // Get list orders
  useEffect(() => {
    if (pageSize) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (refreshListDrone && pageSize) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setRefreshListDrone(false);
    }
  }, [refreshListDrone, pageSize, currentPage, objSearch]);

  // Get json data
  useEffect(() => {
    if (Object.keys(selectedDroneIds).length > 0) {
      const formattedData = Object.entries(selectedDroneIds).map(
        ([packageId, droneId]) => ({
          drone_id: Number(droneId),
          package_id: Number(packageId),
        }),
      );
      setJsonData(formattedData);
    } else {
      setJsonData([]);
    }
  }, [selectedDroneIds]);

  const handleScroll = useCallback(
    debounce((event: any) => {
      const { scrollTop, scrollHeight, clientHeight } = event.target;
      if (
        scrollHeight - scrollTop <= clientHeight + 10 &&
        hasMoreDrones &&
        !isLoadingMoreDrones &&
        selectedPackageIdx
      ) {
        loadMoreDrones(selectedPackageIdx);
      }
    }, 200),
    [hasMoreDrones, isLoadingMoreDrones, selectedPackageIdx],
  );

  return (
    <Box>
      {selectedOrderId ? (
        <Box
          display="flex"
          gap={2}
        >
          {/* Map */}
          <Box flex={1}>
            <Map
              center={droneLocation || undefined}
              operatingMarkers={droneLocation ? [droneLocation] : []}
              polylines={droneLocation ? [[droneLocation]] : []}
              style={{ height: 400 }}
            />
          </Box>
          {/* Select Drone section */}
          <Box
            flex={1}
            bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
            borderRadius={3}
            p={'1rem'}
            height={400}
          >
            {/* Confirm button */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={2}
            >
              <Typography
                variant="h6"
                fontWeight={600}
                fontSize={'1.25rem'}
              >
                {t('Select Drone')}
              </Typography>
              <Box
                display="flex"
                gap={2}
                alignItems="center"
              >
                <CustomBtn
                  variant="contained"
                  color="primary"
                  size="medium"
                  label={t('Confirm')}
                  style={{ minWidth: 100, borderRadius: 8 }}
                  onClick={handleConfirmDrone}
                  disabled={Object.keys(selectedDroneIds).length === 0}
                />
              </Box>
            </Box>
            <Box
              display="flex"
              gap={1}
              sx={{
                height: 'calc(400px - 2rem - 1rem - 2rem)',
              }}
            >
              {/* Package Tabs - vertical */}
              <Box
                display="flex"
                flexDirection="column"
                gap={2}
                sx={{
                  height: 'calc(400px - 2rem - 1rem - 3rem)',
                  overflow: 'auto',
                }}
              >
                {listPackage.length === 0 && (
                  <Box
                    display="flex"
                    justifyContent="center"
                    alignItems="center"
                    height="100%"
                  >
                    <Typography color="#757575">No package found</Typography>
                  </Box>
                )}
                {listPackage.length > 0 &&
                  listPackage.map((pkg, idx) => (
                    <Box
                      onClick={() => setSelectedPackageIdx(pkg.id)}
                      key={pkg.id}
                      p="0.5rem 1rem"
                      borderRadius="0.5rem"
                      bgcolor={
                        selectedPackageIdx === pkg.id
                          ? theme === 'dark'
                            ? '#293438'
                            : '#EEF9FF'
                          : theme === 'dark'
                            ? '#2D2E30'
                            : '#F6F7F8'
                      }
                      color={
                        selectedPackageIdx === pkg.id
                          ? theme === 'dark'
                            ? 'var(--ga-primary-dark)'
                            : 'var(--ga-primary)'
                          : '#9C9D9D'
                      }
                      fontWeight={selectedPackageIdx === pkg.id ? 700 : 500}
                      fontSize={'1rem'}
                      sx={{
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        opacity: selectedPackageIdx === pkg.id ? 1 : 0.7,
                      }}
                    >
                      {t('Package')} {idx + 1}
                    </Box>
                  ))}
              </Box>
              {/* Drone List */}
              <Box
                flex={1}
                borderRadius={'0.5rem'}
                bgcolor={theme === 'dark' ? '#2D2E30' : '#F6F7F8'}
                p="1rem"
                sx={{
                  height: 'calc(400px - 2rem - 1rem - 3rem)',
                }}
              >
                <Box
                  overflow="auto"
                  height={350 - 32 - 27 - 16}
                  maxHeight={500}
                  onScroll={handleScroll}
                  sx={{
                    overflow: 'auto',
                  }}
                >
                  {drones.length === 0 &&
                    selectedPackageIdx &&
                    !isLoadingMoreDrones && (
                      <Box
                        display="flex"
                        justifyContent="center"
                        alignItems="start"
                        height="100%"
                      >
                        <Typography color="#757575">
                          Sorry! We couldn’t find a suitable drone for the
                          selected package. Please try again later.
                        </Typography>
                      </Box>
                    )}
                  {drones.length > 0 &&
                    drones.map((drone) => {
                      return (
                        <Box
                          key={drone.id}
                          display="flex"
                          flexDirection="column"
                          alignItems="flex-start"
                          border="1.5px solid"
                          borderColor={theme === 'dark' ? '#444646' : '#DDDFE2'}
                          bgcolor={theme === 'dark' ? '#1F1F20' : '#fff'}
                          borderRadius={3}
                          mb={'1rem'}
                          p={'1rem'}
                          sx={{
                            cursor: 'pointer',
                            transition: 'border-color 0.2s, box-shadow 0.2s',
                          }}
                          onClick={() => {
                            handleDroneSelection(
                              drone.doneId,
                              selectedPackageIdx,
                            );
                            setDroneLocation(drone.droneLocation);
                          }}
                        >
                          <Box
                            display="flex"
                            alignItems="center"
                          >
                            <Radio
                              checked={
                                selectedPackageIdx
                                  ? selectedDroneIds[selectedPackageIdx] ===
                                    drone.doneId
                                  : false
                              }
                              onChange={() =>
                                selectedPackageIdx &&
                                handleDroneSelection(
                                  drone.doneId,
                                  selectedPackageIdx,
                                )
                              }
                              sx={{
                                color: '#2196F3',
                                padding: 0,
                                mr: 1,
                                '&.Mui-checked': { color: '#2196F3' },
                              }}
                            />
                            <Typography
                              fontWeight={400}
                              fontSize={'1rem'}
                            >
                              {drone.id}
                            </Typography>
                          </Box>
                          {selectedPackageIdx &&
                            selectedDroneIds[selectedPackageIdx] ===
                              drone.doneId && (
                              <Box
                                mt={1}
                                borderTop="1px solid"
                                borderColor={
                                  theme === 'dark' ? '#444646' : '#DDDFE2'
                                }
                                pt={1}
                                display="grid"
                                gridTemplateColumns="140px 1fr"
                                rowGap={0.5}
                                columnGap={2}
                                fontSize={'1rem'}
                                width={'100%'}
                              >
                                <Box color="#757575">{t('Model')}</Box>
                                <Box>{drone.model}</Box>
                                <Box color="#757575">{t('Battery')}</Box>
                                <Box>{drone.battery}</Box>
                                <Box color="#757575">{t('Maximum Load')}</Box>
                                <Box>{drone.maxLoad}</Box>
                              </Box>
                            )}
                        </Box>
                      );
                    })}
                  {isLoadingMoreDrones && (
                    <Box
                      display="flex"
                      justifyContent="center"
                      p={2}
                    >
                      <CircularProgress size={20} />
                    </Box>
                  )}
                  {!hasMoreDrones &&
                    drones.length > 0 &&
                    hasTriedLoadMoreDrones && (
                      <Box
                        display="flex"
                        justifyContent="center"
                        p={2}
                      >
                        <Typography
                          variant="body2"
                          color={theme === 'dark' ? '#fff' : '#000'}
                        >
                          {t('No more drones to load')}
                        </Typography>
                      </Box>
                    )}
                </Box>
              </Box>
            </Box>
          </Box>
        </Box>
      ) : (
        <Box
          display="flex"
          gap={2}
          mb={2}
        >
          {/* Map Skeleton */}
          <Box flex={1}>
            <Skeleton
              variant="rectangular"
              height={400}
              sx={{
                borderRadius: 2,
                bgcolor: theme === 'dark' ? '#1F1F20' : 'rgba(0, 0, 0, 0.08)',
              }}
              animation="wave"
            />
          </Box>
          {/* Route Selection Skeleton */}
          <Box
            flex={1}
            bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
            borderRadius={2}
            p={2}
            boxShadow={1}
          >
            <Skeleton
              variant="text"
              width="40%"
              height={32}
              sx={{ mb: 2 }}
              animation="wave"
            />
            <Skeleton
              variant="rectangular"
              height={60}
              sx={{ mb: 2, borderRadius: 2 }}
              animation="wave"
            />
            <Skeleton
              variant="rectangular"
              height={60}
              sx={{ mb: 2, borderRadius: 2 }}
              animation="wave"
            />
            <Skeleton
              variant="rectangular"
              height={60}
              sx={{ mb: 2, borderRadius: 2 }}
            />
            <Skeleton
              variant="rectangular"
              height={60}
              sx={{ borderRadius: 2 }}
              animation="wave"
            />
          </Box>
        </Box>
      )}
      <CustomizableTable
        columns={COLUMNS}
        data={data}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        stickyHeader
        availableHeight={spaceTableHeight}
        onClickRow={handleViewOrderDetail}
        hightlidhtRow={data.data?.find((item) => item.id === selectedOrder?.id)}
      />
      <OrderDetailModal
        show={isDetailModalOpen}
        onHide={() => setIsDetailModalOpen(false)}
        detailData={selectedRowForDetail}
      />
    </Box>
  );
}
