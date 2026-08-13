import { useState } from 'react';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import { DataAnalysisState } from '../types';

export const useDataAnalysis = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const [dataAnalysis, setDataAnalysis] = useState<{
    data: DataAnalysisState[];
    totalPage: number;
    totalItem: number;
  }>({
    data: [],
    totalPage: 0,
    totalItem: 0,
  });
  const [detailDataAnalysis, setDetailDataAnalysis] =
    useState<DataAnalysisState | null>(null);
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [objSearch, setObjSearch] = useState<SearchObject>({});

  const getDataAnalysisAPI = async () => {
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

      const response = await API.get(endpoint.dataAnalysis, {
        params,
      });
      setDataAnalysis({
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      });
    } catch (error) {
      setDataAnalysis({
        data: [],
        totalPage: 0,
        totalItem: 0,
      });
    } finally {
      hideLoading();
    }
  };

  const getDetailDataAnalysisAPI = async (id: number, useLoading = true) => {
    try {
      useLoading && showLoading();
      const response = await API.get(endpoint.detailDataAnalysis(id));
      setDetailDataAnalysis(response.data);
    } catch (error) {
      setDetailDataAnalysis(null);
    } finally {
      useLoading && hideLoading();
    }
  };

  return {
    dataAnalysis,
    setDataAnalysis,
    detailDataAnalysis,
    setDetailDataAnalysis,
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    objSearch,
    setObjSearch,
    getDataAnalysisAPI,
    getDetailDataAnalysisAPI,
  };
};
