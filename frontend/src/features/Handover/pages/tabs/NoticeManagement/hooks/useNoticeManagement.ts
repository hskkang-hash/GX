import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../../../../services/API';
import { SearchObject, SearchParam } from '../../../../../../types/paramAPI';
import { NoticeManagementState } from '../../../../types';

interface DataProps {
  data: NoticeManagementState[];
  totalPage: number;
  totalItem: number;
}

export const useNoticeManagement = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<DataProps>({
    data: [],
    totalPage: 0,
    totalItem: 0,
  });
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [objSearch, setObjSearch] = useState<SearchObject>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const { showLoading, hideLoading } = useLoadingContext();

  const getNoticeManagementAPI = useCallback(async () => {
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
        is_processed: false,
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

      const response = await API.get(endpoint.noticeManagement, { params });
      setData({
        data: response?.data || [],
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
  }, [pageSize, currentPage, objSearch, showLoading, hideLoading]);

  const getNoticeManagementByIdAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.get(endpoint.detailNoticeManagement, {
          params: { id },
        });
        return {
          success: response.success,
          data: response.data,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          data: {},
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

  const completeNoticeAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.post(endpoint.noticeProcess, {
          id,
          is_processed: true,
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

  const cancelCompletedNoticeAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.post(endpoint.noticeProcess, {
          id,
          is_processed: false,
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

  const addNoticeAPI = useCallback(
    async (data: { id?: number | null; content: string; files: File[] }) => {
      try {
        showLoading();
        const formData = new FormData();
        if (data.id) {
          formData.append(
            'data',
            JSON.stringify({
              notice_id: data.id,
              content: data.content,
            }),
          );
        } else {
          formData.append(
            'data',
            JSON.stringify({
              content: data.content,
            }),
          );
        }
        data.files.forEach((file: File) => {
          formData.append('files', file as unknown as string);
        });
        const response = await API.post(endpoint.noticeManagement, formData);
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

  return {
    data,
    pageSize,
    currentPage,
    objSearch,
    refreshTable,
    setPageSize,
    setCurrentPage,
    setObjSearch,
    setRefreshTable,
    getNoticeManagementAPI,
    getNoticeManagementByIdAPI,
    completeNoticeAPI,
    cancelCompletedNoticeAPI,
    addNoticeAPI,
  };
};
