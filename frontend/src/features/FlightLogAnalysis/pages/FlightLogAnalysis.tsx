import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomModal,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { SearchObject } from '../../../types/paramAPI';
import { remToPx } from '../../../utils/utils';
import { CustomBadgeStatus } from '../components/CustomBadgeStatus';
import DetailFlightLogModal from '../components/DetailFlightLogModal';
import { FlightLogAnalysisColumn } from '../data/FlightLogAnalysisColumn';
import { useFlightLogAnalysis } from '../hooks/useFlightLogAnalysis';
import {
  FlightLogAnalysisPageReducer,
  initialFlightLogAnalysisState,
} from '../store/flightLogAnalysis.reducer';
import { FlightLogAnalysisState } from '../types/flightLogAnalysis.types';

const FlightLogAnalysis = () => {
  const { t } = useTranslation();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const [objSearch, setObjSearch] = useState<SearchObject>({});
  const [detailInfo, setDetailInfo] = useState<FlightLogAnalysisState | null>(
    null,
  );
  const [showFirstDeleteModal, setShowFirstDeleteModal] = useState(false);
  const [showSecondDeleteModal, setShowSecondDeleteModal] = useState(false);
  const {
    getLogAnalysisAPI,
    getDetailLogAnalysisAPI,
    downloadFlightLogAnalysisAPI,
    deleteFlightLogAnalysisAPI,
  } = useFlightLogAnalysis();

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const [state, dispatch] = useReducer(
    FlightLogAnalysisPageReducer,
    initialFlightLogAnalysisState,
  );

  const {
    pageSize,
    currentPage,
    selectedRow,
    modalDetail,
    refreshTable,
    openOffcanvas,
    data,
    selectedRows,
  } = state;

  const getLogAnalysis = useCallback(async () => {
    const { data, totalPage, totalItem } = await getLogAnalysisAPI({
      pageSize: pageSize || 10,
      currentPage,
      objSearch,
    });
    dispatch({
      type: 'SET_DATA',
      payload: {
        data,
        totalPage,
        totalItem,
      },
    });
  }, [getLogAnalysisAPI, pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (pageSize) {
      getLogAnalysis();
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const setRefreshTable = useCallback((refresh: boolean) => {
    dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
  }, []);

  const setCurrentPageCb = useCallback((page: number) => {
    dispatch({ type: 'SET_CURRENT_PAGE', payload: page });
  }, []);

  const setPageSizeCb = useCallback((size: number | null) => {
    dispatch({ type: 'SET_PAGE_SIZE', payload: size ?? 25 });
  }, []);

  const setOpenOffcanvasCb = useCallback((open: boolean) => {
    dispatch({ type: 'OPEN_OFFCANVAS', payload: open });
  }, []);

  const setModalDetailCb = useCallback((open: boolean) => {
    dispatch({ type: 'OPEN_MODAL_DETAIL', payload: open });
  }, []);

  const getDetailLogAnalysis = useCallback(
    async (id: number) => {
      const { data } = await getDetailLogAnalysisAPI(id);
      dispatch({ type: 'SET_SELECTED_ROW', payload: data });
      setModalDetailCb(true);
    },
    [getDetailLogAnalysisAPI, setModalDetailCb],
  );

  const handleClickRow = useCallback(
    (row: FlightLogAnalysisState) => {
      if (row && row?.id) {
        setDetailInfo(row);
        getDetailLogAnalysis(row.id);
      }
    },
    [getDetailLogAnalysis],
  );

  const handleDownload = useCallback(
    async (id: number) => {
      await downloadFlightLogAnalysisAPI(id);
    },
    [downloadFlightLogAnalysisAPI],
  );
  const handleDeleteClick = useCallback(() => {
    setShowFirstDeleteModal(true);
  }, []);

  const handleFirstConfirm = useCallback(() => {
    setShowFirstDeleteModal(false);
    setShowSecondDeleteModal(true);
  }, []);

  const handleSecondConfirm = useCallback(async () => {
    const ids = selectedRows.map((row) => row.id).join(',');
    const { success, message } = await deleteFlightLogAnalysisAPI(ids);
    if (success && message) {
      ToastTopHelper.success(message);
      dispatch({ type: 'TOGGLE_REFRESH', payload: true });
      dispatch({ type: 'SET_SELECTED_ROWS', payload: [] });
      getLogAnalysis();
    } else {
      ToastTopHelper.error(message);
    }
    setShowSecondDeleteModal(false);
  }, [deleteFlightLogAnalysisAPI, selectedRows, dispatch, getLogAnalysis]);

  const handleCancelDelete = useCallback(() => {
    setShowFirstDeleteModal(false);
    setShowSecondDeleteModal(false);
  }, []);

  const handleSelectedRows = useCallback((rows: FlightLogAnalysisState[]) => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  }, []);

  const columns = useMemo(() => {
    return [
      ...FlightLogAnalysisColumn,
      {
        Header: 'Drone State Prediction',
        accessor: 'drone_anomaly_prediction__name',
        filterVariant: 'select',
        filterOptions: [
          { label: t('Select'), value: '' },
          { label: t('flight.normal'), value: 'Normal' },
          { label: t('flight.warning'), value: 'Warning' },
        ],
        cell: (row: {
          getValue: () => string;
          row: { original: FlightLogAnalysisState };
        }) => {
          return row.getValue() ? (
            <CustomBadgeStatus
              status={
                row.row.original.drone_anomaly_prediction__code.toLowerCase() as
                  | 'normal'
                  | 'loading'
                  | 'warning'
              }
              label={row.getValue()}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: ' ',
        accessor: 'action',
        enableColumnFilter: false,
        enableSorting: false,
        notUseConfigTable: true,
        customStyle: {
          width: '10rem',
        },
        cell: (row: { row: { original: FlightLogAnalysisState } }) => {
          return (
            <div>
              <CustomBtn
                label={t('Download')}
                variant="outline"
                color="primary"
                type="button"
                size="sm"
                onClick={() => handleDownload(row.row.original.id)}
              />
            </div>
          );
        },
      },
    ];
  }, [t, handleDownload]);

  return (
    <div style={{ position: 'relative' }}>
      <Container
        id="list-flight-log-analysis"
        isOpenCanvas={openOffcanvas}
      >
        <HeaderWithBtn
          ref={headerPageRef}
          buttons={[]}
        />
        <Main>
          <CustomizableTable
            subTable
            stickyHeader
            onSelectedRows={handleSelectedRows}
            useSystemSetting
            availableHeight={spaceTableHeight}
            columns={columns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleClickRow}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPageCb}
            pageSize={pageSize}
            setPageSize={setPageSizeCb}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={setOpenOffcanvasCb}
            buttons={[
              <CustomBtn
                key="delete-btn"
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={handleDeleteClick}
              />,
            ]}
          />
        </Main>
        {modalDetail && (
          <DetailFlightLogModal
            show={modalDetail}
            onHide={() => {
              setModalDetailCb(false);
              dispatch({ type: 'SET_SELECTED_ROW', payload: null });
            }}
            detailData={selectedRow}
            detailInfo={detailInfo}
          />
        )}
      </Container>

      {/* First Delete Confirmation Modal */}
      {showFirstDeleteModal && (
        <CustomModal
          title={t('Delete Flight Log')}
          show={showFirstDeleteModal}
          onHide={handleCancelDelete}
        >
          <div style={{ width: '25rem' }}>
            <p>
              {t('Are you sure you want to delete selected flight log(s)?')}
            </p>
          </div>

          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="delete-btn"
                variant="contained"
                color="primary"
                size="lg"
                type="button"
                label={t('Delete')}
                onClick={handleFirstConfirm}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={handleCancelDelete}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      )}

      {/* Second Delete Confirmation Modal */}
      {showSecondDeleteModal && (
        <CustomModal
          title={t('Confirmation')}
          show={showSecondDeleteModal}
          onHide={handleCancelDelete}
        >
          <div style={{ width: '25rem' }}>
            <p>{t('Delete Flight Log Permanently?')}</p>
            <p>
              {t(
                'Deleting flight log will permanently erase all related flight data.',
              )}{' '}
              <strong>{t('You will not be able to recover this data.')}</strong>
            </p>
          </div>

          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="delete-permanently-btn"
                variant="contained"
                color="primary"
                size="lg"
                type="button"
                label={t('Delete Permanently')}
                onClick={handleSecondConfirm}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={handleCancelDelete}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      )}
    </div>
  );
};

export default FlightLogAnalysis;
