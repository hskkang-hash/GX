import {
  Box,
  Typography,
  Skeleton,
  Radio,
  CircularProgress,
} from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  CustomBtn,
  CustomizableTable,
  useCalculateHeight,
  useTheme,
  ToastTopHelper,
} from 'rj-core';

import '@/components/Form/CustomRadio.scss';
import MapKakao from '@/components/maps/MapKakao';
import Colors, { colorOpacity } from '@/configs/Colors';
import useAPI from '@/features/routes/useAPI/useAPI';
import API, { endpoint } from '@/services/API';
import { remToPx } from '@/utils/utils';

import { Map } from '../../../../../../components/maps';
import { formatStatusDeliveryInquiry } from '../../../../deliveryInquiry/utils/StatusColorInquiry';
import { useOperationOrder } from '../../../hooks/useOperationOrder';
import OrderDetailModal from '../components/OrderDetailModal';

// Types
interface OrderRow {
  id: number;
  order_id: string;
  current_status__code: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
  origin: string;
  destination: string;
  estimated_distance?: string;
  estimated_duration?: string;
  route_options?: {
    id: number;
    name: string;
    distance: string;
    duration: string;
    is_recommended: boolean;
    stops: { name: string; note?: string }[];
  }[];
}

interface TableData {
  data: OrderRow[];
  totalItem: number;
  totalPage: number;
}

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, unknown>;
}

export default function SelectRouteTab() {
  // Hooks
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { getDetailRouteAPI } = useAPI();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const { fetchUpdateProcessing, fetchOperationOrder, fetchRouteSelect } =
    useOperationOrder();

  // State
  const [routePage, setRoutePage] = useState(1);
  const [pageSize, setPageSize] = useState<number>();
  const [listRoute, setListRoute] = useState<any[]>([]);
  const [routesMap, setRoutesMap] = useState<any[]>([]);
  const [hasMoreRoutes, setHasMoreRoutes] = useState(true);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [operationId, setOperationId] = useState<number | null>(null);
  const [isLoadingMoreRoutes, setIsLoadingMoreRoutes] = useState(false);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [selectedRowForDetail, setSelectedRowForDetail] =
    useState<OrderRow | null>(null);
  const [hasTriedLoadMore, setHasTriedLoadMore] = useState(false);
  // State
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // Columns for table
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

  //Get list route of order
  const handleViewOrderDetail = async (row: any) => {
    setSelectedOrderId(Number(row.id));
    setOperationId(Number(row.order_id));

    if (row.order_id) {
      try {
        setRoutePage(1);
        setListRoute([]);
        setHasMoreRoutes(true);
        setHasTriedLoadMore(false);

        const { data, hasMore } = await fetchRouteSelect({
          page: 1,
          operation_id: Number(row.id),
        });

        const listRoute = data.map((item: any) => ({
          id: item?.id,
          route_name: item?.name,
          route_description: item?.full_description,
          route_distance: item?.total_distance,
          route_duration: item?.estimated_time,
          routes: item?.full_description,
        }));
        if (listRoute.length > 0) {
          setSelectedRouteId(listRoute[0]?.id);
        }
        setListRoute(listRoute);
        setHasMoreRoutes(hasMore);
      } catch (error) {
        ToastTopHelper.error('Failed to load order details');
      }
    }
  };

  // Load more routes
  const loadMoreRoutes = async () => {
    if (isLoadingMoreRoutes || !hasMoreRoutes || !operationId) return;

    setIsLoadingMoreRoutes(true);
    setHasTriedLoadMore(true);

    try {
      const nextPage = routePage + 1;
      const { data, hasMore } = await fetchRouteSelect({
        page: nextPage,
        operation_id: Number(selectedOrderId),
      });

      const newRoutes = data.map((item) => ({
        id: item?.id,
        route_name: item?.name,
        route_description: item?.full_description,
        route_distance: item?.total_distance,
        route_duration: item?.estimated_time,
        routes: item?.full_description,
      }));

      setListRoute((prev) => [...prev, ...newRoutes]);
      setRoutePage(nextPage);
      setHasMoreRoutes(hasMore);
    } catch (error) {
      ToastTopHelper.error('Failed to load more routes');
    } finally {
      setIsLoadingMoreRoutes(false);
    }
  };

  // Scroll handler
  const handleScroll = (event: any) => {
    const { scrollTop, scrollHeight, clientHeight } = event.target;
    if (scrollHeight - scrollTop <= clientHeight + 100) {
      loadMoreRoutes();
    }
  };

  // Get Detail Order for modal
  const fetchOrderDetail = async (orderId: string) => {
    const { success, data } = await API.get(endpoint.detailOrder(orderId));
    if (success) {
      setSelectedRowForDetail(data);
    }
  };

  //Get list order for route
  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: ['select_route_processing'],
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
    }
    if (!selectedOrderId && response && response.data.length > 0) {
      handleViewOrderDetail(response.data[0]);
    }
  };

  // Get list order for route
  useEffect(() => {
    if (pageSize) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch]);

  // Get Detail Route for map
  const getDetailRoute = async (id: number) => {
    const { success, data, message } = await getDetailRouteAPI(id);
    if (success) {
      const routesMapData = data?.route_terminals?.map((item: any) => {
        return {
          lat: item.latitude,
          lng: item.longitude,
          name: item.name,
          for_robot: item.for_robot,
        };
      });
      setRoutesMap(routesMapData);
    }
    if (!success) {
      ToastTopHelper.error(message);
      return;
    }
  };

  // Get Detail Route for map
  useEffect(() => {
    if (selectedRouteId !== null) {
      getDetailRoute(selectedRouteId);
    }
  }, [selectedRouteId]);

  const [refreshListOrder, setRefreshListOrder] = useState<boolean>(false);

  // Confirm Route
  const handleConfirmRoute = async ({
    operation_id,
    route_id,
  }: {
    operation_id: number;
    route_id: number;
  }) => {
    const { success, data } = await fetchUpdateProcessing({
      operation_id: operation_id,
      route_id: route_id,
    });
    if (success) {
      ToastTopHelper.success('Route selection successful.');
      setRefreshListOrder(true);
      setSelectedRouteId(null);
      setSelectedOrderId(null);
      setListRoute([]);
      setRoutesMap([]);
      setHasMoreRoutes(true);
      setHasTriedLoadMore(false);
      setIsLoadingMoreRoutes(false);
    }
    if (!success) {
      ToastTopHelper.error('Failed to update route');
    }
  };

  // Space Table Height
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 400],
  });

  useEffect(() => {
    if (refreshListOrder && pageSize) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setRefreshListOrder(false);
    }
  }, [refreshListOrder, pageSize, currentPage, objSearch]);

  return (
    <Box>
      {listRoute && selectedOrderId !== null ? (
        <Box
          display="flex"
          gap={2}
        >
          {/* Map */}
          <Box flex={1}>
            <Map
              center={
                listRoute.length > 0 && routesMap.length > 0
                  ? { lat: routesMap[0].lat, lng: routesMap[0].lng }
                  : undefined
              }
              operatingMarkers={listRoute.length > 0 ? routesMap : []}
              polylines={
                listRoute.length > 0 && routesMap.length > 0 ? [routesMap] : []
              }
              // bounds={mapBounds || undefined}
              style={{ height: 350 }}
            />
          </Box>
          {/* Select Route section */}
          <Box
            flex={1}
            bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
            borderRadius={2}
            p={2}
            height={350}
          >
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
                {t('Select Route')}
              </Typography>
              <CustomBtn
                variant="contained"
                color="primary"
                size="medium"
                label={t('Confirm')}
                disabled={listRoute.length === 0 || selectedRouteId === null}
                style={{ minWidth: 100, borderRadius: 8 }}
                onClick={() =>
                  handleConfirmRoute({
                    operation_id: selectedOrderId,
                    route_id: selectedRouteId,
                  })
                }
              />
            </Box>
            <Box
              overflow="auto"
              height={350 - 32 - 27 - 16}
              maxHeight={350}
              onScroll={handleScroll}
              sx={{
                overflow: 'auto',
              }}
            >
              {listRoute.length === 0 && !isLoadingMoreRoutes && (
                <Box
                  sx={{
                    color: theme === 'dark' ? Colors.Gray5 : '#9C9D9D',
                  }}
                >
                  {t(
                    "Sorry! We couldn't find a matching route for your selected order. Please review your order details or try again shortly.",
                  )}
                </Box>
              )}

              {listRoute.map((route, index) => (
                <Box
                  key={`${route.id}-${index}`}
                  mb={2}
                  p={0}
                  onClick={() => setSelectedRouteId(route.id)}
                  sx={{
                    border: '1.5px solid',
                    borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                    borderRadius: 2,
                    background:
                      selectedRouteId === route.id
                        ? theme === 'dark'
                          ? '#2D2E30'
                          : '#f7fafd'
                        : theme === 'dark'
                          ? '#2D2E30'
                          : '#fafbfc',
                    transition: 'border-color 0.2s, background 0.2s',
                  }}
                >
                  <Box
                    display="flex"
                    alignItems="center"
                    sx={{ cursor: 'pointer' }}
                  >
                    <Radio
                      checked={selectedRouteId === route.id}
                      className={`custom-radio1 ${theme}`}
                    />
                    <Typography
                      variant="body1"
                      // fontWeight={selectedRouteId === route.id ? 600 : 400}
                      sx={{
                        color: theme === 'dark' ? Colors.Gray3 : Colors.Gray6,
                      }}
                    >
                      {route.route_name}
                      {route.route_distance && route.route_duration
                        ? ` - ${route.route_distance} - ${route.route_duration}`
                        : ''}
                    </Typography>
                  </Box>
                  {selectedRouteId === route?.id && (
                    <Box
                      px={2}
                      py={1}
                      color="#b0b0b0"
                      fontSize="0.95rem"
                      sx={{
                        borderTop: '1.5px solid',
                        borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                        background: theme === 'dark' ? '#1F1F20' : '#fff',
                        borderRadius: 2,
                        borderTopLeftRadius: 0,
                        borderTopRightRadius: 0,
                      }}
                    >
                      {route.routes}
                    </Box>
                  )}
                </Box>
              ))}

              {/* Loading indicator when loading more */}
              {isLoadingMoreRoutes && (
                <Box
                  display="flex"
                  justifyContent="center"
                  p={2}
                >
                  <CircularProgress size={24} />
                </Box>
              )}

              {/* Message when no more data to load */}
              {!hasMoreRoutes && listRoute.length > 0 && hasTriedLoadMore && (
                <Box
                  display="flex"
                  justifyContent="center"
                  p={2}
                  sx={{
                    color: theme === 'dark' ? Colors.Gray5 : '#9C9D9D',
                    fontSize: '0.9rem',
                  }}
                >
                  {t('No more routes to load')}
                </Box>
              )}
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
        hightlidhtRow={data.data?.find((item) => {
          return item.id === selectedOrderId;
        })}
      />
      <OrderDetailModal
        show={isDetailModalOpen}
        onHide={() => setIsDetailModalOpen(false)}
        detailData={selectedRowForDetail}
      />
    </Box>
  );
}
