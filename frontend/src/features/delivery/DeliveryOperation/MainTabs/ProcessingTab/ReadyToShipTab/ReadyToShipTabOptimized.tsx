import { Box, debounce } from '@mui/material';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  CustomBtn,
  CustomizableTable,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import checkIcon from '@/assets/images/checkIcon.svg';
import DeliveryLocationIcon from '@/assets/images/delivery_location.svg';
import errorIcon from '@/assets/images/errorIcon.svg';
import useAPI from '@/features/routes/useAPI/useAPI';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { remToPx } from '@/utils/utils';

import { CancelOrder } from '../../../../deliveryInquiry/components/CancelOrder';
import { useOperationOrder } from '../../../hooks/useOperationOrder';
import OrderDetailModalV2 from '../components/OrderDetailModalV2';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ErrorMessage, LoadingSkeleton } from './components/LoadingStates';
import { MapPanel } from './components/MapPanel';
import { SelectionPanelContainer } from './components/SelectionPanelContainer';
import { useApiSubmission } from './hooks/useApiSubmission';
import { useOrderDataManager } from './hooks/useOrderDataManager';
import { useReadyToShipTab } from './hooks/useReadyToShipTab';
import { OrderRow, TableData } from './types';

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, unknown>;
}

interface ReadyToShipTabProps {
  onNavigateToDeviceCheck?: (tabIndex: number, orderData?: any) => void;
}

export default function ReadyToShipTabOptimized({
  onNavigateToDeviceCheck,
}: ReadyToShipTabProps) {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { getDetailRouteAPI } = useAPI();
  const { getDetailOrder, cancelOrder } = useReadyToShipTab();
  const { fetchOperationOrder } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);

  // Core state
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [currentOrderDetails, setCurrentOrderDetails] =
    useState<OrderRow | null>(null);
  const [selectedDroneIds, setSelectedDroneIds] = useState<
    Record<string, string>
  >({});
  const [droneLocation, setDroneLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  // Table state
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [showModalCancelOrder, setShowModalCancelOrder] = useState(false);

  const { getLatLongFromAddressGoogle } = useCommonAPI();

  // Helper function to calculate distance between two lat/lng points using Haversine formula
  const calculateDistance = (
    lat1: number,
    lng1: number,
    lat2: number,
    lng2: number,
  ): number => {
    const R = 6371; // Radius of the Earth in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in km
  };

  // Modal state
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [dataDetailOrder, setDataDetailOrder] = useState<any>(null);

  // Map state
  const [routesMap, setRoutesMap] = useState<any[]>([]);
  const routeDetailCache = useRef<Record<string, any[]>>({});
  const initialLoadComplete = useRef(false);

  // Height calculation
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 450],
  });

  // Order data manager hook
  const {
    isLoading,
    isLoadingDrones,
    error,
    routes,
    packages,
    drones,
    selectedRouteId,
    selectedPackageIdx,
    isSubmitting,
    crossOrderState,
    globalDroneAssignments,
    handleOrderSelection,
    handlePackageSelection,
    handleRouteSelection,
    setIsSubmitting,
    getDroneStatus,
    generateRouteKey,
    getRouteGroup,
    hasSameRoute,
  } = useOrderDataManager({
    currentOrderDetails,
    selectedDroneIds,
    onDroneLocationChange: setDroneLocation,
    onDroneAssignment: (packageId: string, droneId: string) => {
      console.log('🎯 Auto-assigning drone from manager:', {
        packageId,
        droneId,
      });
      setSelectedDroneIds((prev) => ({
        ...prev,
        [packageId]: droneId,
      }));

      // Update drone location
      const selectedDrone = drones.find((d) => d.doneId === droneId);
      if (selectedDrone?.droneLocation) {
        setDroneLocation(selectedDrone.droneLocation);
      }
    },
  });

  // API submission hook
  const { submitAssignments } = useApiSubmission({
    currentOrderDetails,
    selectedRouteId,
    generateRouteKey,
    getRouteGroup,
  });

  // Table data optimization
  const highlightedOrders = data.data
    .filter(
      (order) =>
        currentOrderDetails &&
        order.id !== currentOrderDetails.id &&
        hasSameRoute(currentOrderDetails, order),
    )
    .map((order) => order.id);

  // Cross-order assignment status: Get orders that have drone assignments
  const assignedOrderIds = useMemo(() => {
    const assignedIds = new Set<number>();

    if (!currentOrderDetails || !crossOrderState) return assignedIds;

    // Get current route key
    const routeKey = generateRouteKey(currentOrderDetails);
    const routeGroup = crossOrderState.routeGroups[routeKey];

    if (!routeGroup?.droneAssignments) return assignedIds;

    // Get all orders that have drone assignments in this route group
    Object.values(routeGroup.droneAssignments).forEach((assignment: any) => {
      assignment.orders.forEach((orderId: number) => {
        assignedIds.add(orderId);
      });
    });

    return assignedIds;
  }, [currentOrderDetails, crossOrderState, generateRouteKey]);

  // Get order detail for modal
  const handleGetDetailOrder = useCallback(
    async (orderId: number) => {
      const { success, data, message } = await getDetailOrder(orderId);
      setDataDetailOrder(data);
      if (!success) {
        ToastTopHelper.error(message);
      }
    },
    [getDetailOrder],
  );

  // Memoized table columns
  const columns = useMemo(
    () => [
      {
        Header: 'Assigned?',
        accessor: 'assignment_status',
        customStyle: {
          maxWidth: '6.5rem',
          minWidth: '5.5rem',
          textAlign: 'center',
        },
        enableColumnFilter: false,
        enableSorting: false,
        notUseConfigTable: true,
        cell: (info: any) => {
          const orderId = info.row.original?.id;
          const isAssigned = assignedOrderIds.has(orderId);
          return (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: '1.2rem',
              }}
            >
              {isAssigned ? (
                <img
                  src={checkIcon}
                  style={{ margin: '0.5em', width: '1.5em', height: '1.5em' }}
                  alt="checkIcon"
                />
              ) : (
                <img
                  src={errorIcon}
                  style={{ margin: '0.5em', width: '1.5em', height: '1.5em' }}
                  alt="errorIcon"
                />
              )}
            </div>
          );
        },
      },
      { Header: 'Order ID', accessor: 'order__order_code' },
      {
        Header: 'Order Time',
        accessor: 'order__created_on',
        filterVariant: 'datetime',
      },
      { Header: 'Origin', accessor: 'origin' },
      { Header: 'Destination', accessor: 'destination' },
      { Header: 'Sender', accessor: 'order__sender_name' },
      { Header: 'Recipient', accessor: 'order__recipient_name' },
      // {
      //   Header: 'Mapped Status',
      //   accessor: 'mapped_status',
      //   enableColumnFilter: false,
      //   cell: (info: any) => {
      //     const mappedListStatus = info.row.original?.mapped_status_list;
      //     const mappedStatusCode = info.row.original?.mapped_status_code;
      //     const currentStatusName = info.row.original?.mapped_status;
      //     const currentTextColor = getContrastTextColor(
      //       info.row.original?.mapped_status_background_color,
      //     );
      //     const currentBackgroundColor =
      //       info.row.original?.mapped_status_background_color;
      //     const currentBorderColor =
      //       info.row.original?.mapped_status_border_color;
      //     return (
      //       <div
      //         style={{
      //           display: 'flex',
      //           gap: 8,
      //           width: 'fit-content',
      //           flexFlow: 'wrap',
      //         }}
      //       >
      //         {mappedListStatus?.length > 0
      //           ? mappedListStatus?.map(
      //               (item: {
      //                 name: string;
      //                 code: string;
      //                 background_color: string;
      //                 text_color: string;
      //                 border_color: string;
      //               }) =>
      //                 formatStatusDeliveryInquiry({
      //                   t,
      //                   status_name: item.name,
      //                   status_code: mappedStatusCode,
      //                   backgroundColor: item.background_color,
      //                   color: item.text_color,
      //                   border: item.border_color,
      //                   isShowButton: false,
      //                 }),
      //             )
      //           : mappedStatusCode &&
      //             formatStatusDeliveryInquiry({
      //               t,
      //               status_name: currentStatusName,
      //               status_code: mappedStatusCode,
      //               backgroundColor: currentBackgroundColor,
      //               color: currentTextColor,
      //               border: currentBorderColor,
      //               isShowButton: false,
      //             })}
      //       </div>
      //     );
      //   },
      // },
      {
        Header: t(' '),
        accessor: 'action',
        enableColumnFilter: false,
        enableSorting: false,
        cell: (row: any) => (
          <div
            className="special-label"
            onClick={(e) => {
              e.stopPropagation();
              setDataDetailOrder(null);
              handleGetDetailOrder(row?.row?.original.order__id);
              setIsDetailModalOpen(true);
            }}
          >
            <BsEye size={16} />
          </div>
        ),
        customStyle: { maxWidth: 20, textAlign: 'center' },
        notUseConfigTable: true,
      },
    ],
    [t, handleGetDetailOrder, setIsDetailModalOpen],
  );

  // Enhanced table data with highlights
  const enhancedTableData = useMemo(
    () => ({
      ...data,
      data: data.data.map((order) => ({
        ...order,
        isHighlighted: highlightedOrders.includes(order.id),
      })),
    }),
    [data, highlightedOrders],
  );

  // Search params
  const searchParams = useMemo(
    () => ({
      status_codes: ['select_route_processing'],
    }),
    [],
  );

  // Drone selection handler
  const handleDroneSelection = useCallback(
    (packageId: string, droneId: string) => {
      console.log('🎯 Drone selected:', { packageId, droneId });

      setSelectedDroneIds((prev) => ({
        ...prev,
        [packageId]: droneId,
      }));

      // Update drone location
      const selectedDrone = drones.find((d) => d.doneId === droneId);
      if (selectedDrone?.droneLocation) {
        setDroneLocation(selectedDrone.droneLocation);
      }
    },
    [drones],
  );

  // Order detail handler
  const handleViewOrderDetail = useCallback(
    async (order: OrderRow) => {
      try {
        setSelectedOrderId(Number(order.id));
        setCurrentOrderDetails(order);

        // Reset local state
        setSelectedDroneIds({});
        setDroneLocation(null);

        // Handle order selection through data manager
        const result = await handleOrderSelection(order);

        // Restore preserved assignments if same route
        if (result?.preservedAssignments) {
          setSelectedDroneIds(result.preservedAssignments);
        }
      } catch (error) {
        console.error('Error viewing order detail:', error);
        ToastTopHelper.error('Failed to load order details');
      }
    },
    [handleOrderSelection],
  );

  // Highlighted order click handler
  const handleHighlightedOrderClick = useCallback(
    async (row: OrderRow) => {
      if (!currentOrderDetails || !hasSameRoute(currentOrderDetails, row)) {
        await handleViewOrderDetail(row);
        return;
      }

      // Same route - preserve assignments and switch context
      console.log('✨ Same route detected - switching order context');
      setCurrentOrderDetails(row);
      setSelectedOrderId(Number(row.id));

      // Load packages for the new order but preserve route state
      const result = await handleOrderSelection(row);

      if (result?.preservedAssignments) {
        setSelectedDroneIds(result.preservedAssignments);
      }
    },
    [
      currentOrderDetails,
      hasSameRoute,
      handleViewOrderDetail,
      handleOrderSelection,
    ],
  );

  // Get orders from API
  const handleGetOrders = useCallback(
    async ({ pageSize, currentPage, objSearch }: SearchParams) => {
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
        // Map the response data to include real_order_id
        const enhancedData = response.data.map((order: any) => ({
          ...order,
          real_order_id: order.order_id, // Store the actual order_id as real_order_id
        }));

        setData({
          data: enhancedData,
          totalPage: response.totalPage,
          totalItem: response.totalItem,
        });

        // Auto-select first order if none selected (only on initial load)
        if (
          !selectedOrderId &&
          enhancedData.length > 0 &&
          !initialLoadComplete.current
        ) {
          initialLoadComplete.current = true;
          handleViewOrderDetail(enhancedData[0]);
        }
      }
    },
    [
      fetchOperationOrder,
      handleViewOrderDetail,
      selectedOrderId,
      initialLoadComplete,
    ],
  );

  // Drone scroll handler
  const handleDroneScroll = useCallback(
    debounce((event: any) => {
      const { scrollTop, scrollHeight, clientHeight } = event.target;
      if (scrollHeight - scrollTop <= clientHeight + 10) {
        // Handle infinite scroll if needed
        console.log('Drone scroll reached bottom');
      }
    }, 200),
    [],
  );

  // Package assignment handler
  const handleAssignPackage = useCallback(async () => {
    try {
      setIsSubmitting(true);

      // Force refresh packages if needed
      if (currentOrderDetails) {
        const routeKey = generateRouteKey(currentOrderDetails);
        const routeGroup = getRouteGroup(routeKey);
        if (routeGroup && routeGroup.orders.length > 0) {
          console.log('🔄 Ensuring packages are up to date...');
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
      }

      const success = await submitAssignments();

      if (success) {
        // Refresh table data
        if (pageSize) {
          await handleGetOrders({
            pageSize,
            currentPage,
            objSearch: { ...objSearch, ...searchParams },
          });
        }

        // Store the order data before clearing
        const assignedOrderData = currentOrderDetails;

        setSelectedOrderId(null);
        setCurrentOrderDetails(null);
        setSelectedDroneIds({});

        // Navigate to Device Check tab with the assigned order
        if (onNavigateToDeviceCheck && assignedOrderData) {
          console.log(
            '✅ Assignment successful, navigating to Device Check tab with order:',
            assignedOrderData,
          );
          onNavigateToDeviceCheck(1, assignedOrderData);
        }
      }
    } catch (error) {
      console.error('Error assigning packages:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    currentOrderDetails,
    generateRouteKey,
    getRouteGroup,
    submitAssignments,
    pageSize,
    currentPage,
    objSearch,
    searchParams,
    onNavigateToDeviceCheck,
    handleGetOrders,
    setIsSubmitting,
  ]);

  // Fetch route detail for map with caching
  const fetchOrderDetail = useCallback(
    async (orderId: string) => {
      // Check cache first
      if (routeDetailCache.current[orderId]) {
        setRoutesMap(routeDetailCache.current[orderId]);
        return;
      }

      try {
        const response = await getDetailRouteAPI(Number(orderId));
        if (response?.success) {
          let closestTerminalIndex: number | null = null;

          // If no delivery terminal, find the closest terminal to destination
          if (!currentOrderDetails?.order_terminal_id) {
            const result = await getLatLongFromAddressGoogle(
              currentOrderDetails?.destination || '',
            );

            if (
              result.data?.lat &&
              result.data?.lng &&
              response.data?.route_terminals
            ) {
              const destinationLat = result.data.lat;
              const destinationLng = result.data.lng;
              let minDistance = Infinity;
              response.data.route_terminals.forEach(
                (
                  terminal: { latitude: number; longitude: number },
                  index: number,
                ) => {
                  const distance = calculateDistance(
                    destinationLat,
                    destinationLng,
                    terminal.latitude,
                    terminal.longitude,
                  );
                  if (distance < minDistance) {
                    minDistance = distance;
                    closestTerminalIndex = index;
                  }
                },
              );
            }
          }

          const routesMapData =
            response.data?.route_terminals?.map((item: any, index: number) => {
              if (
                currentOrderDetails?.order_terminal_id &&
                item.terminal_id === currentOrderDetails?.order_terminal_id
              ) {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                  icon: DeliveryLocationIcon,
                };
              } else if (
                !currentOrderDetails?.order_terminal_id &&
                closestTerminalIndex !== null &&
                index === closestTerminalIndex
              ) {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                  icon: DeliveryLocationIcon,
                };
              } else {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                };
              }
            }) || [];

          // Cache the result
          routeDetailCache.current[orderId] = routesMapData;
          setRoutesMap(routesMapData);
        }
      } catch (error) {
        console.error('Error fetching route detail:', error);
      }
    },
    [getDetailRouteAPI, getLatLongFromAddressGoogle, currentOrderDetails],
  );

  // Check if package assignment is disabled
  const getDisabledAssignPackageStatus = useCallback(() => {
    if (!currentOrderDetails || !selectedRouteId) return true;

    try {
      const routeKey = generateRouteKey(currentOrderDetails);
      const routeGroup = getRouteGroup(routeKey);

      if (!routeGroup || typeof routeGroup !== 'object') return true;
      if (Object.keys(routeGroup?.droneAssignments || {}).length === 0)
        return true;

      return false;
    } catch (error) {
      console.warn('Error calculating disabled status:', error);
      return true;
    }
  }, [currentOrderDetails, selectedRouteId, generateRouteKey, getRouteGroup]);

  // Memoized search object to prevent unnecessary re-renders
  const memoizedSearchObject = useMemo(
    () => ({
      ...objSearch,
      ...searchParams,
    }),
    [objSearch, searchParams],
  );

  // Debounced effect to prevent rapid successive API calls
  useEffect(() => {
    if (!pageSize) return;

    const timeoutId = setTimeout(() => {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch: memoizedSearchObject,
      });
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [pageSize, currentPage, memoizedSearchObject]); // Removed handleGetOrders from deps

  useEffect(() => {
    if (selectedRouteId !== null) {
      fetchOrderDetail(String(selectedRouteId));
    }
  }, [selectedRouteId]); // Removed fetchOrderDetail from deps

  // Error handling
  if (error) {
    return <ErrorMessage message={error} />;
  }
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const listId = selectedRows?.map((item: any) => item.order__id);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleCancelOrder = async (listId: any, reason: string) => {
    const { success, message } = await cancelOrder(listId, reason);
    if (success) {
      const updatedData = data?.data?.filter((item: any) => {
        return !listId.includes(item.order__id);
      });
      setData({
        ...data,
        data: updatedData,
      });
      setRefreshTable(true);
      setShowModalCancelOrder(false);
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  };

  return (
    <ErrorBoundary>
      <Box>
        {selectedOrderId ? (
          <Box
            display="flex"
            gap={2}
          >
            <MapPanel
              routes={routes}
              routesMap={routesMap}
              droneLocation={droneLocation}
            />
            <SelectionPanelContainer
              routes={routes}
              selectedRouteId={selectedRouteId}
              onRouteSelect={handleRouteSelection}
              drones={drones}
              selectedPackageIdx={selectedPackageIdx}
              selectedDroneIds={selectedDroneIds}
              globalDroneAssignments={globalDroneAssignments}
              optimizedAssignments={{}}
              listPackage={packages}
              isLoadingMoreDrones={isLoading}
              hasMoreDrones={false}
              hasTriedLoadMoreDrones={true}
              onDroneSelection={handleDroneSelection}
              onDroneLocationChange={setDroneLocation}
              onDroneScroll={handleDroneScroll}
              getDroneStatus={getDroneStatus}
              onPackageSelection={handlePackageSelection}
              disabledAssignPackage={
                getDisabledAssignPackageStatus() || isLoadingDrones
              }
              onAssignPackage={handleAssignPackage}
              isSubmitting={isSubmitting || isLoadingDrones}
              isLoading={isLoading}
            />
          </Box>
        ) : (
          <LoadingSkeleton />
        )}

        {/* Order Table */}
        <CustomizableTable
          // notShowSelectRow
          subTable
          useSystemSetting
          columns={columns as any}
          data={enhancedTableData}
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
          onClickRow={handleHighlightedOrderClick}
          onSelectedRows={handleSelectionRows}
          hightlidhtRow={currentOrderDetails}
          customHighlightRows={highlightedOrders}
          buttons={[
            <CustomBtn
              label={t('Cancel Order')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              actionType={ROLE_PERMISSION.UPDATE}
              disabled={selectedRows.length === 0}
              onClick={() => {
                if (selectedRows.length > 0) {
                  setShowModalCancelOrder(true);
                }
              }}
            />,
          ]}
          customHighlightColor={theme === 'dark' ? '#4C3E08' : '#FFF3B8'}
        />

        <OrderDetailModalV2
          show={isDetailModalOpen}
          onHide={() => setIsDetailModalOpen(false)}
          detailData={dataDetailOrder}
        />

        <CancelOrder
          showModal={showModalCancelOrder}
          setHideModal={() => {
            setShowModalCancelOrder(false);
          }}
          handleCancelOrder={(reason: string) => {
            if (selectedRows.length > 0 && reason) {
              handleCancelOrder(listId, reason);
            } else {
              ToastTopHelper.error(t('Cannot Get Order ID'));
            }
          }}
        />
      </Box>
    </ErrorBoundary>
  );
}
