import { Box } from '@mui/material';
import { useEffect, useMemo, useState, type ReactElement } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsExclamationCircle } from 'react-icons/bs';
import { useNavigate } from 'react-router-dom';
import { CustomBtn, FormBlock, ROLE_PERMISSION, useTheme } from 'rj-core';

import GearIcon from '../../../../../../assets/images/GearIcon';
import CustomCheckBox from '../../../../../../components/Form/CustomCheckBox';
import { CustomRoutes } from '../../../../../../services/API';
import { useOperationOrder } from '../../../hooks/useOperationOrder';
import { checkStatusAllDrone } from '../../../utils/checkStatus';
import ApproveFlightModal from './ApproveFlightModal';
import CancelOrderModal from './CancelOrderModal';
import DroneSensorStatus, { DroneSensorStatusType } from './DroneSensorStatus';
import ListDroneToChangeModal from './ListDroneToChangeModal';

interface ChecklistSetting {
  name_category: string;
  item: {
    id: string;
    item_name: string;
  }[];
}

interface ChecklistFormValues {
  checklistValues: {
    selectedIds: string[];
    byId: Record<string, boolean>;
  };
  action?: string;
}

export const CheckList = ({
  checklistSetting,
  droneSensorStatus,
  sensorStatus,
  loadingSensorStatus,
  orderIds,
  droneId,
  droneUniqueId,
  routeId,
  refetchChecklist = false,
  checklistDisabled = false,
  selectedChecklist = [],
  selectedRowForDetail = null,
  setDroneSensorStatus = () => {},
  setRefetchChecklist = () => {},
  handleRefreshDroneList = () => {},
  onRefreshSensorStatus = () => {},
  onNavigateToInTransit,
  currentOrderData,
}: {
  checklistSetting: ChecklistSetting[];
  droneSensorStatus: DroneSensorStatusType[];
  sensorStatus: any;
  loadingSensorStatus: boolean;
  orderIds: number[];
  droneId: number | null;
  droneUniqueId: string | null;
  routeId: number;
  refetchChecklist: boolean;
  checklistDisabled: boolean;
  selectedChecklist: number[];
  selectedRowForDetail: any | null;
  setDroneSensorStatus: (droneSensorStatus: DroneSensorStatusType[]) => void;
  setRefetchChecklist: (refetch: boolean) => void;
  handleRefreshDroneList: () => void;
  onRefreshSensorStatus?: () => void;
  onNavigateToInTransit?: (tabIndex: number, orderData?: any) => void;
  currentOrderData?: any;
}): ReactElement => {
  console.log('routeId', routeId);
  const { t } = useTranslation();
  const [theme] = useTheme();
  const methods = useForm<ChecklistFormValues>({
    defaultValues: {
      checklistValues: {
        selectedIds: [],
        byId: {},
      },
      action: '',
    },
  });
  const navigate = useNavigate();
  const [toDrone, setToDrone] = useState<number | null>(null);
  const [reasonNote, setReasonNote] = useState<string>('');
  const [showApproveFlightModal, setShowApproveFlightModal] = useState(false);
  const [showCancelOrderModal, setShowCancelOrderModal] = useState(false);
  const orderFixPosition = [
    'Pre-flight Check',
    'Controller Check',
    'Weather Check',
  ];
  const positionOrder = new Map(
    orderFixPosition.map((name, index) => [name, index] as const),
  );
  const [showListDroneToChangeModal, setShowListDroneToChangeModal] =
    useState(false);
  const sortedChecklistSetting = (checklistSetting ?? [])
    .map((item, originalIndex) => ({ item, originalIndex }))
    .sort((a, b) => {
      const rankA = positionOrder.get(a.item.name_category);
      const rankB = positionOrder.get(b.item.name_category);
      const valueA =
        typeof rankA === 'number' ? rankA : Number.MAX_SAFE_INTEGER;
      const valueB =
        typeof rankB === 'number' ? rankB : Number.MAX_SAFE_INTEGER;
      if (valueA !== valueB) return valueA - valueB;
      return a.originalIndex - b.originalIndex;
    })
    .map(({ item }) => item);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = methods;

  const {
    actionCancelOrder,
    actionCancelFlight,
    actionChangeDrone,
    actionUploadRoute,
    actionConfirmFlight,
  } = useOperationOrder();

  useEffect(() => {
    if (refetchChecklist) {
      setRefetchChecklist(false);
    }

    // Always update form values when selectedChecklist changes or when refetching
    if (selectedChecklist && selectedChecklist.length > 0) {
      const selectedIds = selectedChecklist.map((id) => String(id));
      const byId = selectedIds.reduce(
        (acc, id) => {
          acc[id] = true;
          return acc;
        },
        {} as Record<string, boolean>,
      );

      methods.reset({
        checklistValues: {
          selectedIds,
          byId,
        },
        action: '',
      });
    } else {
      methods.reset({
        checklistValues: {
          selectedIds: [],
          byId: {},
        },
        action: '',
      });
    }
  }, [selectedChecklist, refetchChecklist, methods]);

  const onValidSubmit = async (data: ChecklistFormValues): Promise<void> => {
    const action = data.action;
    if (!action) {
      return;
    }
    switch (action) {
      case 'cancelOrder': {
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionCancelOrder({
          order_ids: orderIds,
          reason_note: reasonNote,
        });
        if (response?.success) {
          handleRefreshDroneList();
          setRefetchChecklist(true);
          setReasonNote('');
          setDroneSensorStatus([]);
        }
        break;
      }
      case 'cancelFlight': {
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionCancelFlight({
          drone_id: droneId,
          order_ids: orderIds,
        });
        if (response?.success) {
          handleRefreshDroneList();
          setRefetchChecklist(true);
          setDroneSensorStatus([]);
        }
        break;
      }
      case 'changeDrone': {
        console.log('changeDrone', droneId, orderIds, toDrone, routeId);
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionChangeDrone({
          order_ids: orderIds,
          from_drone: droneId,
          to_drone: toDrone,
          route_id: routeId,
        });
        if (response?.success) {
          handleRefreshDroneList();
          setDroneSensorStatus([]);
        }
        break;
      }
      case 'uploadRoute': {
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionUploadRoute({
          order_ids: orderIds,
          drone_unique_id: droneUniqueId || '',
        });
        if (response?.success) {
          handleRefreshDroneList();
        }
        break;
      }
      case 'confirmFlight': {
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionConfirmFlight({
          order_ids: orderIds,
          check_lists: data.checklistValues.selectedIds.map((id) => Number(id)),
          drone_id: droneId,
          auto_checklist: droneSensorStatus,
        });
        if (response?.success) {
          setRefetchChecklist(true);
          handleRefreshDroneList();
          setDroneSensorStatus([]);

          // Navigate to In Transit tab after successful approval
          if (onNavigateToInTransit && currentOrderData) {
            console.log(
              '✅ Flight approved, navigating to In Transit tab with order:',
              currentOrderData,
            );
            onNavigateToInTransit(2, currentOrderData);
          }
          // if (response?.data?.message?.en || response?.data?.message?.kr) {
          //   ToastTopHelper.success(
          //     response?.data?.message[i18n.language === 'en' ? 'en' : 'kr'],
          //   );
          // }
        }

        break;
      }
      case 'confirmFlightNotYet': {
        if (!droneId) return;
        // eslint-disable-next-line no-console
        const response = await actionConfirmFlight({
          order_ids: orderIds,
          check_lists: data.checklistValues.selectedIds.map((id) => Number(id)),
          drone_id: droneId,
          not_yet: true,
        });
        if (response?.success) {
          setRefetchChecklist(true);
          handleRefreshDroneList();
          setDroneSensorStatus([]);
        }
        break;
      }
      default:
        // eslint-disable-next-line no-console
        console.log('Submit: unknown action', action, data);
    }
  };

  const renderChecklistWithCategory = (
    checklist: ChecklistSetting,
  ): ReactElement => {
    return (
      <FormBlock
        key={checklist.name_category}
        style={{
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          height: '22rem',
          overflow: 'auto',
          width: '100%',
        }}
      >
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
          {t(checklist.name_category)}
        </div>
        <div className="content-title d-flex flex-column">
          {checklist.item.map((item) => {
            const selectedIds =
              methods.watch('checklistValues.selectedIds') ?? [];
            const isChecked = selectedIds.includes(String(item.id));

            return (
              <CustomCheckBox
                name={`checklistValues.byId.${item.id}`}
                subLabel={item.item_name}
                control={control}
                checked={isChecked}
                onChangeValue={(checked): void => {
                  const current =
                    methods.getValues('checklistValues.selectedIds') ?? [];
                  const itemIdStr = String(item.id);
                  const exists = current.includes(itemIdStr);
                  const next = checked
                    ? exists
                      ? current
                      : [...current, itemIdStr]
                    : exists
                      ? current.filter((id) => id !== itemIdStr)
                      : current;
                  methods.setValue('checklistValues.selectedIds', next, {
                    shouldDirty: true,
                  });
                }}
                disabled={!droneId || checklistDisabled}
                key={`${item.id}-${checklist.name_category}-${item.item_name}`}
              />
            );
          })}
        </div>
      </FormBlock>
    );
  };

  const isAllDroneSensorStatusNormal = useMemo(() => {
    return (
      droneSensorStatus &&
      droneSensorStatus.length > 0 &&
      checkStatusAllDrone('Normal', droneSensorStatus)
    );
  }, [droneSensorStatus]);

  return (
    <>
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onValidSubmit)}>
          <Box
            height={410}
            overflow={'auto'}
            display="flex"
            flexDirection="column"
          >
            <DroneSensorStatus
              droneSensorStatus={droneSensorStatus}
              sensorStatus={sensorStatus}
              loadingSensorStatus={loadingSensorStatus}
              onRefreshSensorStatus={onRefreshSensorStatus}
            />
            {droneSensorStatus && droneSensorStatus.length > 0 && (
              <>
                {isAllDroneSensorStatusNormal ? (
                  <>
                    <div className="d-flex justify-content-between align-items-center mt-4">
                      <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>
                          {t('Check List')}
                        </h1>
                        <p
                          className="mt-3 mb-0"
                          style={{
                            fontSize: '1rem',
                            fontWeight: 400,
                            color: '#9C9D9D',
                          }}
                        >
                          {t(
                            'Complete the checklist and upload the route before you can approve the flight.',
                          )}
                        </p>
                      </div>
                      <div
                        style={{
                          cursor: 'pointer',
                          border: '1px solid #E0E0E0',
                          borderRadius: '8px',
                          padding: '0.25rem',
                        }}
                        onClick={() => {
                          navigate(CustomRoutes.checklistSetting.path);
                        }}
                      >
                        <GearIcon
                          color={theme === 'dark' ? '#FFFFFF' : '#2D2E30'}
                        />
                      </div>
                    </div>
                    <div className="d-flex gap-4 flex-row mt-3">
                      {sortedChecklistSetting &&
                        sortedChecklistSetting.map((checklist) => {
                          return renderChecklistWithCategory(checklist);
                        })}
                    </div>
                  </>
                ) : (
                  <div
                    className="d-flex justify-content-center align-items-center"
                    style={{
                      flex: 1,
                      minHeight: 0,
                      color: '#EB7509',
                      fontSize: '1rem',
                      fontWeight: 600,
                    }}
                  >
                    <BsExclamationCircle
                      className="me-2"
                      size={16}
                    />
                    <p className="text-center mb-0">
                      {t(
                        'This drone has a malfunctioning sensor and cannot fly. Please select another drone or cancel the operation',
                      )}
                    </p>
                  </div>
                )}
              </>
            )}
          </Box>
          {droneId && (
            <div className="d-flex justify-content-center gap-3 mt-3">
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Cancel Order')}
                color="secondary"
                variant="outline"
                type="button"
                onClick={() => {
                  setShowCancelOrderModal(true);
                }}
                loading={isSubmitting}
                disabled={!droneId}
              />
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Cancel Flight')}
                color="secondary"
                variant="outline"
                type="submit"
                onClick={() => {
                  methods.setValue('action', 'cancelFlight');
                }}
                loading={isSubmitting}
                disabled={
                  !droneId ||
                  checklistDisabled ||
                  selectedRowForDetail?.is_upload_mission
                }
              />
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Change Drone')}
                variant="outline"
                color="primary"
                type="button"
                onClick={() => {
                  setShowListDroneToChangeModal(true);
                }}
                disabled={
                  !droneId ||
                  checklistDisabled ||
                  selectedRowForDetail?.is_upload_mission
                }
              />
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Upload Route')}
                type="submit"
                onClick={() => {
                  methods.setValue('action', 'uploadRoute');
                }}
                loading={isSubmitting}
                disabled={
                  !droneId ||
                  selectedRowForDetail?.is_upload_mission ||
                  !isAllDroneSensorStatusNormal
                }
              />
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Approve Flight')}
                type="button"
                onClick={() => {
                  setShowApproveFlightModal(true);
                }}
                loading={isSubmitting}
                disabled={
                  !droneId ||
                  checklistDisabled ||
                  !isAllDroneSensorStatusNormal ||
                  !selectedRowForDetail?.is_upload_mission ||
                  !methods.getValues('checklistValues.selectedIds').length
                }
              />
            </div>
          )}
        </form>
      </FormProvider>
      <ListDroneToChangeModal
        droneId={Number(droneId)}
        orderIds={orderIds}
        routeId={routeId}
        show={showListDroneToChangeModal}
        onChangeDroneSuccess={() => {
          setRefetchChecklist(true);
          handleRefreshDroneList();
        }}
        onClose={() => setShowListDroneToChangeModal(false)}
      />

      <ApproveFlightModal
        show={showApproveFlightModal}
        onClose={() => setShowApproveFlightModal(false)}
        onApproveFlight={() => {
          methods.setValue('action', 'confirmFlight');
          setShowApproveFlightModal(false);
          handleSubmit(onValidSubmit)();
        }}
        onNotYet={() => {
          methods.setValue('action', 'confirmFlightNotYet');
          setShowApproveFlightModal(false);
          handleSubmit(onValidSubmit)();
        }}
      />
      <CancelOrderModal
        show={showCancelOrderModal}
        onClose={() => {
          setShowCancelOrderModal(false);
          setReasonNote('');
        }}
        onCancelOrder={(reason: string) => {
          setReasonNote(reason);
          methods.setValue('action', 'cancelOrder');
          setShowCancelOrderModal(false);
          handleSubmit(onValidSubmit)();
        }}
        reasonNote={reasonNote}
        onReasonChange={setReasonNote}
      />
    </>
  );
};
