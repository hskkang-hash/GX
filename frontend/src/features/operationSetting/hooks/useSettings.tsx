import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

interface SearchParam {
  id: string;
  value: string | number | boolean;
}

interface SortParam {
  id: string;
  desc: boolean;
}

interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
}

export default function useSettings() {
  const { showLoading, hideLoading } = useLoadingContext();
  const getOperationSettings = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    try {
      showLoading();
      const paramsFetch: Record<string, unknown> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch.searchParams) {
          objSearch.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }

        if (objSearch.filters) {
          paramsFetch.filters = objSearch.filters;
        }

        if (objSearch.sortParams?.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.operationSettings, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  return {
    getOperationSettings,
  };
}
