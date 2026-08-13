import dayjs from 'dayjs';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../../../../services/API';
import { SearchObject, SearchParam } from '../../../../../../types/paramAPI';
import {
  HandoverManagementState,
  HandoverNoticeState,
  HandoverShiftState,
} from '../../../../types';

interface DataProps {
  data: HandoverManagementState[];
  totalPage: number;
  totalItem: number;
}

export const useHandoverManagement = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<DataProps>({
    data: [],
    totalPage: 0,
    totalItem: 0,
  });
  const [shiftList, setShiftList] = useState<HandoverShiftState[]>([]);
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [objSearch, setObjSearch] = useState<SearchObject>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const { showLoading, hideLoading } = useLoadingContext();

  const getHandoverManagementAPI = useCallback(
    async ({
      start_date_time,
      end_date_time,
    }: {
      start_date_time?: string;
      end_date_time?: string;
    }) => {
      try {
        showLoading();

        if (!pageSize || !currentPage) return;

        const params: {
          page_size: number;
          current_page: number;
          sort_obj?: Array<{ id: string; desc: boolean }>;
          filters?: Record<string, unknown>;
          [key: string]: unknown;
        } = {
          page_size: pageSize,
          current_page: currentPage ? currentPage : 1,
        };

        if (objSearch) {
          if (objSearch?.searchParams) {
            objSearch?.searchParams.forEach((item: SearchParam) => {
              params[item.id] = item.value;
            });
          }
          if (objSearch?.filters) {
            params['filters'] = objSearch.filters;
          }
          if (objSearch?.sortParams && objSearch?.sortParams.length) {
            params.sort_obj = objSearch.sortParams;
          }
        }

        if (start_date_time) {
          // If already in YYYY-MM-DD format, use directly; otherwise parse and format
          params['start_date_time'] =
            dayjs(start_date_time).format('YYYY-MM-DD');
        }
        if (end_date_time) {
          // If already in YYYY-MM-DD format, use directly; otherwise parse and format
          params['end_date_time'] = dayjs(end_date_time).format('YYYY-MM-DD');
        }

        const response = await API.get(endpoint.handoverManagement, { params });
        setData({
          data:
            response?.data.map((item: HandoverManagementState) => {
              return {
                notShowCheckbox: !item?.shift_id,
                status: item?.data ? 'have_shifts' : 'not_have_shifts',
                created_time: item.created_time ? item.created_time : '',
                date: item.date ? item.date : '',
                total_content: item.total_content,
                data: item.data,
                shift__name: item.shift__name,
                group__name: item.group__name,
                creator__full_name: item.creator__full_name,
                id: item.id,
              };
            }) || [],
          totalPage: response?.total_pages || 0,
          totalItem: response?.total_items || 0,
        });
      } catch (error) {
        setData({
          data: [],
          totalPage: 0,
          totalItem: 0,
        });
      } finally {
        hideLoading();
      }
    },
    [pageSize, currentPage, objSearch, showLoading, hideLoading],
  );

  const getHandoverShiftAPI = useCallback(async () => {
    try {
      const response = await API.get(endpoint.handoverShift);

      setShiftList(
        response?.data.map((item: HandoverShiftState) => {
          return {
            id: item?.id,
            name: item?.name || '',
          };
        }) || [],
      );
    } catch (error) {
      setShiftList([]);
    }
  }, [setShiftList]);

  const createShiftHandoverAPI = useCallback(
    async (data: { shift_id: number | null; date: string }) => {
      try {
        showLoading();
        const response = await API.post(endpoint.handoverManagement, {
          shift_id: data.shift_id,
          date: data.date,
        });
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const deleteShiftHandoverAPI = useCallback(
    async (ids: number[]) => {
      try {
        showLoading();
        const response = await API.delete(endpoint.handoverManagement, {
          data: { ids },
        });
        return {
          success: response.success,
          message: response.message,
          failed: response.data.failed,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const getListNoticeHandoverAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.get(endpoint.getListNoticeHandover, {
          params: { id },
        });
        return {
          success: response.success,
          data:
            response.data.map((item: HandoverNoticeState) => {
              return {
                id: item.id,
                content: item.content_text,
                is_notice: item.is_notice,
                handover_doc_id: item.handover_doc_id,
                created_time: item.created_time,
                updated_time: item.modified_on,
                creator__full_name: item.creator_full_name,
                editor__full_name: item.editor_full_name,
                is_edit: true,
              };
            }) || [],
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
          data: [],
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const createNoticeHandoverAPI = useCallback(
    async ({
      handover_doc_id,
      content,
      is_notice,
      content_id,
      is_edit = false,
    }: {
      handover_doc_id?: number;
      content: string;
      is_notice: boolean;
      content_id?: number;
      is_edit?: boolean;
    }) => {
      try {
        showLoading();
        const data = !is_edit
          ? {
              handover_doc_id: handover_doc_id,
              content: content,
              is_notice: is_notice,
            }
          : {
              content_id: content_id,
              content: content,
              is_notice: is_notice,
            };

        const response = await API.post(
          endpoint.createNoticeHandover,
          !is_edit
            ? {
                data: data,
              }
            : {
                update_data: data,
              },
        );
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const deleteNoticeHandoverAPI = useCallback(
    async ({
      content_id,
      handover_doc_id,
    }: {
      content_id?: number;
      handover_doc_id?: number;
    }) => {
      try {
        showLoading();
        const response = await API.delete(endpoint.createNoticeHandover, {
          data: { content_id, handover_doc_id },
        });
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const getHandoverDutyDetailAPI = useCallback(
    async (ids: number[]) => {
      try {
        showLoading();
        const response = await API.post(endpoint.handoverDutyDetail, {
          handover_ids: ids,
        });
        return {
          success: response.success,
          data: response.data,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || t('handover.Something went wrong'),
          data: [],
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  return {
    data,
    shiftList,
    pageSize,
    currentPage,
    objSearch,
    refreshTable,
    setShiftList,
    setPageSize,
    setCurrentPage,
    setObjSearch,
    setRefreshTable,
    getHandoverManagementAPI,
    getHandoverShiftAPI,
    deleteShiftHandoverAPI,
    createShiftHandoverAPI,
    createNoticeHandoverAPI,
    deleteNoticeHandoverAPI,
    getListNoticeHandoverAPI,
    getHandoverDutyDetailAPI,
  };
};
