import { useCallback, useState } from 'react';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../../../../services/API';
import { SearchObject, SearchParam } from '../../../../../../types/paramAPI';
import { CompletedNoticeState } from '../../../../types';

interface DataProps {
  data: CompletedNoticeState[];
  totalPage: number;
  totalItem: number;
}

export const useCompletedNotice = () => {
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

  const getCompletedNoticeAPI = useCallback(async () => {
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
        is_processed: true,
        deleted: true,
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
    getCompletedNoticeAPI,
  };
};
