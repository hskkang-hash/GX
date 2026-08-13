import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  CenterBtn,
  Container,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { CustomRoutes } from '../../../services/API';
import { SearchObject } from '../../../types/paramAPI';
import { remToPx } from '../../../utils/utils';
import {
  convertFieldsAndData,
  replaceQRParagraphWithDiv,
} from '../../waybillTemplate/hooks/convertFields';
import '../assets/style/ReportTemplate.scss';
import CustomNunjucksRerender from '../components/CustomNunjucksRerender';
import useReportTemplate from '../hooks/useReportTemplate';
import {
  initialReportTemplatePageState,
  ReportTemplatePageReducer,
} from '../store/reportTemplate.reducer';
import { ReportTemplateState } from '../types/reportTemplate.types';

const ReportTemplate = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLElement>(
    null,
  ) as React.RefObject<HTMLElement>;
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });
  const [objSearch, setObjSearch] = useState({});
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [templateContent, setTemplateContent] = useState('');
  const [dataExample, setDataExample] = useState<
    Record<string, string | number | boolean | null | undefined>
  >({});
  const [state, dispatch] = useReducer(
    ReportTemplatePageReducer,
    initialReportTemplatePageState,
  );

  const {
    pageSize,
    currentPage,
    selectedRows,
    refreshTable,
    openOffcanvas,
    data,
  } = state;

  const { getReportTemplate, deleteReportTemplate, getFieldsTemplate } =
    useReportTemplate();

  useEffect(() => {
    if (pageSize) {
      handleGetData(pageSize, currentPage, objSearch);
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    (async () => {
      const response = await getFieldsTemplate('DeliveryOperation');
      const result = await convertFieldsAndData(response[0].fields);
      setDataExample(result.data);
    })();
  }, []);

  const handleGetData = useCallback(
    async (pageSize: number, currentPage: number, objSearch: SearchObject) => {
      const {
        data: dataReportTemplate,
        totalPage,
        totalItem,
      } = await getReportTemplate({
        currentPage,
        pageSize,
        objSearch,
      });
      dispatch({
        type: 'SET_DATA',
        payload: { data: dataReportTemplate, totalPage, totalItem },
      });
    },
    [getReportTemplate, dispatch],
  );

  const handleClickRow = (row: ReportTemplateState) => {
    navigate(
      CustomRoutes.reportTemplate.subRoutes.editReportTemplate.path.replace(
        ':id',
        row.id,
      ),
    );
  };

  const handleSelectionRows = (rows: ReportTemplateState[]): void => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  };

  const handleAddNewTemplate = () => {
    navigate(CustomRoutes.reportTemplate.subRoutes.addNewReportTemplate.path);
  };

  const handleDelete = useCallback(async (): Promise<void> => {
    const ids = selectedRows.map((row) => row.id).join(',');
    const { message, success } = await deleteReportTemplate(ids);
    if (success) {
      dispatch({ type: 'TOGGLE_REFRESH', payload: true });
      if (pageSize && currentPage) {
        handleGetData(pageSize, currentPage, objSearch);
      }
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  }, [
    deleteReportTemplate,
    selectedRows,
    pageSize,
    currentPage,
    objSearch,
    handleGetData,
  ]);

  const CustomColumns = useMemo(() => {
    return [
      {
        Header: t('Usage Count'),
        accessor: 'usage_count',
      },
      {
        Header: t(' '),
        accessor: 'template',
        cell: (row: {
          getValue: () => string;
          row: { original: ReportTemplateState };
        }) =>
          row.getValue() && row.getValue() !== '' ? (
            <div
              className="special-label"
              onClick={(e) => {
                e.stopPropagation();
                setTemplateContent(row.row.original.template || ``);
                setShowPreviewModal(true);
              }}
            >
              <BsEye size={16} />
            </div>
          ) : null,
        customStyle: { maxWidth: 20, textAlign: 'center' as const },

        enableSorting: false,
        enableColumnFilter: false,
        notUseConfigTable: true,
      },
    ];
  }, [t, setShowPreviewModal]);

  return (
    <Container
      id="list-report-template"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            actionType={ROLE_PERMISSION.CREATE}
            label={t('Add New Template')}
            icon={<GoPlus size={18} />}
            onClick={handleAddNewTemplate}
          />,
        ]}
      />
      <Main>
        <CustomizableTable
          stickyHeader
          availableHeight={spaceTableHeight}
          columns={CustomColumns}
          data={data}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onClickRow={handleClickRow}
          onSelectedRows={handleSelectionRows}
          refreshTable={refreshTable}
          setRefreshTable={(refresh: boolean) => {
            dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
          }}
          currentPage={currentPage}
          setCurrentPage={(page: number) => {
            dispatch({ type: 'SET_CURRENT_PAGE', payload: page });
          }}
          buttons={[
            <CustomBtn
              label={t('Delete')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              actionType={ROLE_PERMISSION.DELETE}
              disabled={selectedRows.length === 0}
              onClick={handleDelete}
            />,
          ]}
          pageSize={pageSize}
          setPageSize={(size: number) => {
            dispatch({ type: 'SET_PAGE_SIZE', payload: size });
          }}
          offcanvas={openOffcanvas}
          setOpenOffcanvas={(boolean: boolean) => {
            dispatch({ type: 'OPEN_OFFCANVAS', payload: boolean });
          }}
        />

        <CustomModal
          title={t('Preview')}
          show={showPreviewModal}
          onHide={() => setShowPreviewModal(false)}
          id="preview-report-template-modal"
        >
          <div className="mb-3 custom-modal-preview">
            <CustomNunjucksRerender
              template={replaceQRParagraphWithDiv(templateContent)}
              data={dataExample}
            />
          </div>
          <CenterBtn
            color="secondary"
            type="button"
            variant="outline"
            size="lg"
            onClick={() => setShowPreviewModal(false)}
            label={t('Close')}
          />
        </CustomModal>
      </Main>
    </Container>
  );
};

export default ReportTemplate;
