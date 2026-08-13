import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import { CustomRoutes } from '../../../services/API';
import { SearchObject } from '../../../types/paramAPI';
import { formatStatusSurveyMission } from '../../../utils/formatColumns';
import { remToPx } from '../../../utils/utils';
import { ApproveMissionModal } from '../components/ApproveMissionModal';
import ImportMissionModal from '../components/ImportMissionModal';
import { RejectMissionModal } from '../components/RejectMissionModal';
import { useSurveyMission } from '../hooks/useSurveyMission';
import {
  initialSurveyMissionPageState,
  SurveyMissionPageReducer,
} from '../store/surveyMission.reducer';
import {
  ImportMissionFormValues,
  SurveyMissionState,
} from '../types/surveyMission.types';

export const SurveyMissionPage = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });
  const navigate = useNavigate();

  const [objSearch, setObjSearch] = useState<SearchObject | null>(null);

  const {
    getSurveyMission,
    approveSurveyMission,
    rejectSurveyMission,
    activateSurveyMission,
    deactivateSurveyMission,
    checkPermissionActionSurveyMission,
  } = useSurveyMission();

  const [state, dispatch] = useReducer(
    SurveyMissionPageReducer,
    initialSurveyMissionPageState,
  );

  const {
    data,
    pageSize,
    currentPage,
    selectedRows,
    refreshTable,
    openOffcanvas,
    showApproveMissionModal,
    showRejectMissionModal,
    showImportMissionModal,
    missionId,
    hasPermissionActionSurveyMission,
  } = state;

  const checkHasPermissionActionSurveyMission = useCallback(async () => {
    const result = await checkPermissionActionSurveyMission();
    dispatch({
      type: 'SET_HAS_PERMISSION_ACTION_SURVEY_MISSION',
      payload: result,
    });
  }, [checkPermissionActionSurveyMission]);

  const getSurveyMissionData = useCallback(async () => {
    const { data, totalPage, totalItem } = await getSurveyMission({
      currentPage,
      pageSize,
      objSearch,
    });
    if (data) {
      dispatch({ type: 'SET_DATA', payload: { data, totalPage, totalItem } });
    }
  }, [currentPage, pageSize, objSearch, getSurveyMission]);

  useEffect(() => {
    checkHasPermissionActionSurveyMission();
  }, []);

  useEffect(() => {
    if (pageSize) {
      getSurveyMissionData();
    }
  }, [currentPage, pageSize, objSearch]);

  const handleClickRow = useCallback(
    (selectedRow: SurveyMissionState) => {
      navigate(
        CustomRoutes.surveyMission.subRoutes.detailSurveyMission.path.replace(
          ':id',
          selectedRow.id.toString(),
        ),
      );
    },
    [navigate],
  );

  const setRefreshTable = useCallback((refresh: boolean) => {
    dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
  }, []);

  const handleActionButton = useCallback(
    async (action: 'activate' | 'deactivate') => {
      if (action === 'activate') {
        const { success, message } = await activateSurveyMission({
          ids: selectedRows.map((row) => row.id).join(','),
        });
        if (success) {
          ToastTopHelper.success(message);
          setRefreshTable(true);
          getSurveyMissionData();
        } else {
          ToastTopHelper.error(message);
        }
      } else {
        const { success, message } = await deactivateSurveyMission({
          ids: selectedRows.map((row) => row.id).join(','),
        });
        if (success) {
          ToastTopHelper.success(message);
          setRefreshTable(true);
          getSurveyMissionData();
        } else {
          ToastTopHelper.error(message);
        }
      }
    },
    [
      activateSurveyMission,
      deactivateSurveyMission,
      selectedRows,
      setRefreshTable,
      getSurveyMissionData,
    ],
  );

  const setCurrentPage = useCallback((page: number) => {
    dispatch({ type: 'SET_CURRENT_PAGE', payload: page });
  }, []);

  const setPageSize = useCallback((size: number) => {
    dispatch({ type: 'SET_PAGE_SIZE', payload: size });
  }, []);

  const setOpenOffcanvas = useCallback((open: boolean) => {
    dispatch({ type: 'OPEN_OFFCANVAS', payload: open });
  }, []);

  const handleButtonApproveMission = useCallback(
    (show: boolean, id?: number | null) => {
      dispatch({ type: 'OPEN_APPROVE_MISSION_MODAL', payload: show });
      if (id) {
        dispatch({ type: 'SET_MISSION_ID', payload: id });
      }
    },
    [],
  );

  const handleButtonRejectMission = useCallback(
    (show: boolean, id?: number | null) => {
      if (id) {
        dispatch({ type: 'SET_MISSION_ID', payload: id });
      }
      dispatch({ type: 'OPEN_REJECT_MISSION_MODAL', payload: show });
    },
    [],
  );

  const handleApproveMission = useCallback(async () => {
    const { success, message } = await approveSurveyMission({
      id: missionId || 0,
    });
    if (success) {
      ToastTopHelper.success(message);
      setRefreshTable(true);
      getSurveyMissionData();
      handleButtonApproveMission(false);
    } else {
      ToastTopHelper.error(message);
    }
  }, [
    missionId,
    approveSurveyMission,
    setRefreshTable,
    handleButtonApproveMission,
    getSurveyMissionData,
  ]);

  const handleRejectMission = useCallback(
    async (values: { reason: string }) => {
      const data = {
        reason: values.reason,
      };
      const { success, message } = await rejectSurveyMission({
        id: missionId || 0,
        data,
      });
      if (success) {
        ToastTopHelper.success(message);
        setRefreshTable(true);
        getSurveyMissionData();
        handleButtonRejectMission(false);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [
      missionId,
      rejectSurveyMission,
      setRefreshTable,
      getSurveyMissionData,
      handleButtonRejectMission,
    ],
  );

  const { importSurveyMissionAPI } = useSurveyMission();
  const handleImportMission = useCallback(
    async (data: ImportMissionFormValues) => {
      const payload = {
        ...data,
        purpose_id: data.purpose_id?.value,
        route_ids: data.route_ids.map((item: any) => Number(item.value)),
        note: '',
        total_distance: 0,
        estimated_time: 0,
        altitude: 150,
        takeoff_altitude: 100,
        altitude_separation: 10,
        cruise_speed: 0,
        hover_speed: 5,
      };
      dispatch({ type: 'OPEN_IMPORT_MISSION_MODAL', payload: false });

      try {
        const response = await importSurveyMissionAPI(payload, {
          onSuccess: () => {
            ToastTopHelper.success(t('SurveyMission.Import mission completed'));
            setRefreshTable(true);
            getSurveyMissionData();
          },
          onError: () => {
            ToastTopHelper.error(t('SurveyMission.Import mission failed'));
          },
        });

        if (response.success) {
          ToastTopHelper.success(
            response.message || t('SurveyMission.Import mission started'),
          );
        } else {
          ToastTopHelper.error(response.message);
        }
      } catch (error) {
        console.error('Import mission error:', error);
        ToastTopHelper.error(t('Something went wrong'));
      }
    },
    [importSurveyMissionAPI, getSurveyMissionData, setRefreshTable, t],
  );

  const COLUMNS = useMemo(() => {
    return [
      {
        Header: 'Start Point',
        accessor: 'start_point',
        cell: (row: {
          row: { original: SurveyMissionState; start_point: string };
        }) => {
          const formattedStartPoint = row.row.original.start_point
            .split(', ')
            .map((item: string) => item.trim());
          return (
            <div style={{ whiteSpace: 'pre-line' }}>
              {formattedStartPoint.join(',\n')}
            </div>
          );
        },
      },
      {
        Header: 'End Point',
        accessor: 'end_point',
        cell: (row: {
          row: { original: SurveyMissionState; end_point: string };
        }) => {
          const formattedEndPoint = row.row.original.end_point
            .split(', ')
            .map((item: string) => item.trim());
          return (
            <div style={{ whiteSpace: 'pre-line' }}>
              {formattedEndPoint.join(',\n')}
            </div>
          );
        },
      },
      {
        Header: 'Status',
        accessor: 'status__name',
        filterVariant: 'select',
        filterOptions: [
          {
            label: t('All'),
            value: '',
          },
          {
            label: t('Pending Approval-Survey'),
            value: t('Pending Approval-Survey'),
          },
          { label: t('Approved-Survey'), value: t('Approved-Survey') },
          { label: t('Rejected-Survey'), value: t('Rejected-Survey') },
        ],
        cell: (row: {
          row: { original: SurveyMissionState; status__code: string };
        }) => {
          return formatStatusSurveyMission(
            row.row.original.status__code,
            row.row.original.status__name,
            t,
            theme,
          );
        },
      },
      ...(hasPermissionActionSurveyMission
        ? [
            {
              Header: ' ',
              accessor: 'code',
              enableColumnFilter: false,
              enableSorting: false,
              notUseConfigTable: true,
              customStyle: {
                width: '170px',
                justifyItems: 'center',
              },
              cell: (row: {
                row: { original: SurveyMissionState; status__code: string };
              }) => {
                return (
                  <>
                    {row.row.original.status__code === 'pending_approval' && (
                      <div className="d-flex gap-2">
                        <CustomBtn
                          label={t('SurveyMission.Approve')}
                          type="button"
                          variant="outline"
                          color="primary"
                          size="sm"
                          onClick={() =>
                            handleButtonApproveMission(
                              true,
                              Number(row.row.original.id),
                            )
                          }
                        />
                        <CustomBtn
                          label={t('Reject')}
                          type="button"
                          variant="outline"
                          color="primary"
                          size="sm"
                          onClick={() =>
                            handleButtonRejectMission(
                              true,
                              Number(row.row.original.id),
                            )
                          }
                        />
                      </div>
                    )}
                  </>
                );
              },
            },
          ]
        : []),
    ];
  }, [
    handleButtonApproveMission,
    handleButtonRejectMission,
    t,
    theme,
    hasPermissionActionSurveyMission,
  ]);

  return (
    <Container
      id="list-survey-mission"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('SurveyMission.Import Mission')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              dispatch({ type: 'OPEN_IMPORT_MISSION_MODAL', payload: true });
            }}
          />,
          <CustomBtn
            label={t('SurveyMission.Add New Mission')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => navigate('/survey-mission/add-new-survey-mission')}
          />,
        ]}
      />
      <Main>
        <CustomizableTable
          stickyHeader
          availableHeight={spaceTableHeight}
          columns={COLUMNS}
          data={data}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onClickRow={handleClickRow}
          onSelectedRows={(rows: SurveyMissionState[]) => {
            dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
          }}
          refreshTable={refreshTable}
          setRefreshTable={setRefreshTable}
          buttons={[
            <CustomBtn
              label={t('Delete')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              // actionType={ROLE_PERMISSION.UPDATE}
              disabled={selectedRows.length === 0}
              onClick={() => handleActionButton('activate')}
            />,
            <CustomBtn
              label={t('SurveyMission.Activate')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              // actionType={ROLE_PERMISSION.UPDATE}
              disabled={selectedRows.length === 0}
              onClick={() => handleActionButton('activate')}
            />,
            <CustomBtn
              label={t('SurveyMission.Deactivate')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              // actionType={ROLE_PERMISSION.UPDATE}
              disabled={selectedRows.length === 0}
              onClick={() => handleActionButton('deactivate')}
            />,
          ]}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          pageSize={pageSize}
          setPageSize={setPageSize}
          offcanvas={openOffcanvas}
          setOpenOffcanvas={setOpenOffcanvas}
        />

        {showApproveMissionModal && (
          <ApproveMissionModal
            show={showApproveMissionModal}
            onClose={() => handleButtonApproveMission(false)}
            onApprove={handleApproveMission}
          />
        )}

        {showRejectMissionModal && (
          <RejectMissionModal
            show={showRejectMissionModal}
            onClose={() => handleButtonRejectMission(false)}
            onReject={handleRejectMission}
          />
        )}

        {showImportMissionModal && (
          <ImportMissionModal
            show={showImportMissionModal}
            onClose={() =>
              dispatch({ type: 'OPEN_IMPORT_MISSION_MODAL', payload: false })
            }
            refreshListMission={() => setRefreshTable(true)}
            handleImportMission={handleImportMission}
          />
        )}
      </Main>
    </Container>
  );
};
