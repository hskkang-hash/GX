import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
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

import useBoolean from '@/hooks/useBoolean';
import { CustomRoutes } from '@/services/API';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import './assets/style/WaybillTemplate.scss';
import NunjucksRenderer from './components/NunjucksRenderer';
import {
  convertFieldsAndData,
  replaceQRParagraphWithDiv,
} from './hooks/convertFields';
import useWaybill from './hooks/useWaybill';
import { WaybillTemplateData } from './type';

const WaybillTemplate = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [objSearch, setObjSearch] = useState({});
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [selectedRows, setSelectedRows] = useState<WaybillTemplateData[]>([]);
  const [data, setData] = useState<{
    data: WaybillTemplateData[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const headerPageRef = useRef<HTMLElement>(
    null,
  ) as React.RefObject<HTMLElement>;

  const [templateContent, setTemplateContent] = useState<string>('');
  const [dataExample, setDataExample] = useState<Record<string, any>>({});

  const [deleteModal, setShowDeleteModal, setHideDeleteModal] = useBoolean();
  const [previewModal, setShowPreviewModal, setHidePreviewModal] = useBoolean();

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const { getWaybillTemplateList, deleteWaybillTemplate, getFieldsTemplate } =
    useWaybill();

  useEffect(() => {
    if (pageSize) {
      getFieldsTemplate().then(async (res) => {
        const result = await convertFieldsAndData(res[0].fields);
        setDataExample(result.data);
      });
      getWaybillTemplateList({ pageSize, currentPage, objSearch }).then(
        (res) => {
          setData(res);
        },
      );
    }
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: WaybillTemplateData[]) => {
    setSelectedRows(selectedData);
  };

  const handleClickRow = (selectedRow: WaybillTemplateData) => {
    console.log(selectedRow.id);
    if (selectedRow.id) {
      navigate(
        CustomRoutes.waybillTemplate.subRoutes.editWaybillTemplate.path.replace(
          ':id',
          selectedRow.id.toString(),
        ),
      );
    }
  };

  const handleDelete = () => {
    deleteWaybillTemplate(
      selectedRows.map((row) => row.id.toString()).join(','),
    ).then((res) => {
      if (res.success) {
        setRefreshTable(!refreshTable);
        setSelectedRows([]);
        setData({
          data: data.data.filter((row) => !selectedRows.includes(row)),
          totalItem: data.totalItem - selectedRows.length,
          totalPage: data.totalPage,
        });
        ToastTopHelper.success(res.message);
      } else {
        ToastTopHelper.error(res.message);
      }
    });
  };

  const handleAddNewTemplate = () => {
    navigate(CustomRoutes.waybillTemplate.subRoutes.addNewWaybillTemplate.path);
  };

  console.log(dataExample);

  return (
    <>
      <Container
        id="list-waybill-template"
        isOpenCanvas={openOffcanvas}
      >
        <HeaderWithBtn
          ref={headerPageRef}
          buttons={[
            <CustomBtn
              label={t('Add New Template')}
              icon={<GoPlus size={18} />}
              actionType={ROLE_PERMISSION.CREATE}
              onClick={handleAddNewTemplate}
            />,
          ]}
        />
        <Main>
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={[
              {
                Header: t('Created On'),
                accessor: 'created_on',
                filterVariant: 'datetime',
              },
              {
                Header: t('Is Enabled'),
                accessor: 'is_enabled',
                filterVariant: 'checkbox',
                filterOptions: ['True', 'False'],
                cell: (row: any) => formatEnabled(row.getValue()),
              },
              {
                Header: t('Usage Count'),
                accessor: 'usage_count',
              },
              {
                Header: t('Is Default'),
                accessor: 'is_default',
                filterVariant: 'checkbox',
                filterOptions: ['True', 'False'],
                cell: (row: any) => formatEnabled(row.getValue()),
              },
              {
                Header: t(' '),
                accessor: 'template',
                cell: (row: any) =>
                  row.getValue() && row.getValue() !== '' ? (
                    <div
                      className="special-label"
                      onClick={(e) => {
                        e.stopPropagation();
                        setTemplateContent(row.row.original.template || ``);
                        setShowPreviewModal();
                      }}
                    >
                      <BsEye size={16} />
                    </div>
                  ) : null,
                customStyle: { maxWidth: 20, textAlign: 'center' },
                enableSorting: false,
                enableColumnFilter: false,
                notUseConfigTable: true,
              },
            ]}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleClickRow}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            buttons={[
              <CustomBtn
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.DELETE}
                disabled={selectedRows.length === 0}
                onClick={() => {
                  handleDelete();
                  // setShowDeleteModal();
                }}
              />,
            ]}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              setOpenOffcanvas(boolean);
            }}
          />
        </Main>

        {/* Delete Modal */}
        <CustomModal
          title={t('Delete Waybill Template')}
          show={deleteModal}
          onHide={setHideDeleteModal}
          id="delete-modal"
        >
          {t(
            'Are you sure you want to delete {{count}} selected waybill template(s)?',
            {
              count: selectedRows.length,
            },
          )}
          <ActionBtn
            leftButtons={[
              <CustomBtn
                type="submit"
                variant="outline"
                color="primary"
                size="lg"
                onClick={handleDelete}
                actionType={ROLE_PERMISSION.DELETE}
                label={t('Delete')}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => setHideDeleteModal()}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>

        <CustomModal
          title={t('Preview')}
          show={previewModal}
          onHide={setHidePreviewModal}
          id="preview-modal"
        >
          <div className="mb-3 custom-modal-preview">
            <NunjucksRenderer
              template={replaceQRParagraphWithDiv(templateContent)}
              data={dataExample}
            />
          </div>
          <CenterBtn
            color="secondary"
            type="button"
            variant="outline"
            size="lg"
            onClick={() => setHidePreviewModal()}
            label={t('Close')}
          />
        </CustomModal>
      </Container>
    </>
  );
};

export default WaybillTemplate;
