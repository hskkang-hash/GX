import dayjs from 'dayjs';
import { useCallback, useMemo, useReducer, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useLoadingContext, useUserInfo } from 'rj-core';

import { SearchObject, SearchParam, SortParam } from '@/types/paramAPI';

import API, { endpoint } from '../../../services/API';
import {
  addListDownloadFile,
  addTaskIdToFile,
  removeFile,
} from '../../../utils/actionFileManagement';
import {
  initialMediaDataState,
  MediaDataPageReducer,
} from '../store/MediaData.reducer';
import { MediaDataState } from '../types';

export const useMediaData = () => {
  const { t } = useTranslation();
  const userInfo = useUserInfo();

  // Lấy userId hiện tại từ userInfo
  const currentUserId = useMemo(() => {
    if (!userInfo) return undefined;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      undefined
    );
  }, [userInfo]);
  const { showLoading, hideLoading } = useLoadingContext();
  const [objSearch, setObjSearch] = useState<SearchObject>({});
  /**
   * UX-10 — **목록을 못 가져왔다는 사실.**
   *
   * ★ [실측 2026-09-14 · D-397] `GET /api/media-data/` 가 **500** 인데 화면은
   *   「0 of 0」 을 그렸다. 아래 `catch` 가 `console.error` 한 줄이라 실패가
   *   **콘솔에만** 남고, 표는 앞의 빈 상태를 그대로 들고 서 있었기 때문이다 —
   *   당직자에게는 **「영상 자료가 없다」**로 보인다(D-378).
   *
   *   「없다」와 「못 가져왔다」는 다른 사실이다(DA-03 §2-5 규칙 1):
   *     없다        = 기다릴 것이 없다
   *     못 가져왔다 = **다시 시도할 것이 있다**
   *   그래서 이 값을 세운다. `null` 이면 목록이 사실이고, 아니면 표를 믿으면 안 된다.
   *
   * ★ 503 은 **저장소가 죽은 것**이다. 우리 코드가 깨진 것(500)과 다른 사실이라
   *   다른 문장으로 적는다 — 하나로 묶으면 저장소 장애가 「자료 없음」으로 위장된다.
   */
  const [listError, setListError] = useState<{
    storageDown: boolean;
    status: number;
  } | null>(null);
  const [state, dispatch] = useReducer(
    MediaDataPageReducer,
    initialMediaDataState,
  );

  const {
    data,
    pageSize,
    currentPage,
    viewFile,
    detectionTypes,
    videoAnalysisData,
    videoAnalysisId,
    isLoadingAnalysis,
  } = state;

  const setDetectionTypes = useCallback(
    (detectionTypes: { value: string; label: string }[]) => {
      dispatch({ type: 'SET_DETECTION_TYPES', payload: detectionTypes });
    },
    [dispatch],
  );

  const setData = useCallback(
    (data: {
      data: MediaDataState[];
      totalItem: number;
      totalPage: number;
    }) => {
      dispatch({ type: 'SET_DATA', payload: data });
    },
    [dispatch],
  );
  const setPageSize = useCallback(
    (pageSize: number | null) => {
      dispatch({ type: 'SET_PAGE_SIZE', payload: pageSize ?? 25 });
    },
    [dispatch],
  );
  const setCurrentPage = useCallback(
    (currentPage: number) => {
      dispatch({ type: 'SET_CURRENT_PAGE', payload: currentPage });
    },
    [dispatch],
  );

  const setViewFile = useCallback(
    (
      viewFile: {
        url: string;
        type: string;
        analysisId?: number | null;
      } | null,
    ) => {
      dispatch({
        type: 'SET_VIEW_FILE',
        payload: viewFile || null,
      });
    },
    [dispatch],
  );

  const setVideoAnalysisData = useCallback(
    (
      data: {
        object: string;
        object_count: number | string;
        detected_image_path: string;
        detect_time: string;
      }[],
    ) => {
      dispatch({ type: 'SET_VIDEO_ANALYSIS_DATA', payload: data });
    },
    [dispatch],
  );

  const setVideoAnalysisId = useCallback(
    (id: number | null) => {
      dispatch({ type: 'SET_VIDEO_ANALYSIS_ID', payload: id });
    },
    [dispatch],
  );

  const setLoadingAnalysis = useCallback(
    (loading: boolean) => {
      dispatch({ type: 'SET_LOADING_ANALYSIS', payload: loading });
    },
    [dispatch],
  );

  const getMediaDataAPI = useCallback(async () => {
    try {
      showLoading();
      const paramsFetch: {
        page_size?: number | null;
        current_page: number;
        filters?: Record<string, unknown>;
        sort_obj?: SortParam[];
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch?.searchParams) {
          objSearch?.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }
        if (objSearch?.filters) {
          paramsFetch['filters'] = objSearch.filters;
        }
        if (objSearch?.sortParams && objSearch?.sortParams.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.mediaData, {
        params: paramsFetch,
      });

      //: 성공했으니 앞 실패를 지운다 — 안 지우면 「다시 시도」가 성공해도 빨강이 남는다
      setListError(null);
      setData({
        data: response.data.map(
          (item: {
            id: number;
            object_name: string;
            full_object_name: string;
            type: string;
            size: string;
            group_name: string;
            last_modified: string;
          }) => ({
            // Use full_object_name as id since BE doesn't provide id
            // This enables row highlighting in CustomizableTable
            id: item.id || item.full_object_name,
            object_name: item.object_name,
            full_object_name: item.full_object_name,
            type: item.type,
            size: item.size,
            group__name: item.group_name,
            last_modified: item.last_modified,
          }),
        ),
        totalPage: response.total_pages,
        totalItem: response.total_items,
      });
    } catch (error) {
      //: ★ [UX-10 · 2026-09-26] 앞판은 여기서 `console.error` 하고 **아무것도 안
      //:   했다.** 실패가 콘솔에만 남고 화면은 「0 of 0」 을 그렸다 — 조용한 실패는
      //:   없는 실패보다 나쁘다. 이제 실패를 **화면이 들 수 있는 값으로** 올린다.
      //: ★ 표를 억지로 비우지 않는다. 앞서 받아 둔 목록이 있으면 그것은 「그때는
      //:   사실이었던 것」이고, 화면이 그 위에 **못 가져왔다**를 덮어 말한다.
      const status =
        (error as { response?: { status?: number } })?.response?.status ?? 0;
      console.error(error);
      setListError({ storageDown: status === 503, status });
    } finally {
      hideLoading();
    }
  }, [showLoading, hideLoading, pageSize, currentPage, objSearch, setData]);

  const previewFileAPI = useCallback(
    async (object_path: string) => {
      try {
        showLoading();
        setViewFile(null);
        setVideoAnalysisId(null);
        setVideoAnalysisData([]);
        const response = await API.post(endpoint.previewFile, {
          object_path: object_path,
        });
        const analysisId = response.data?.analysis_id || null;
        const analysisJson = response.data?.analysis_json || null;

        setViewFile({
          url: response.data.url,
          type: response.data.content_type.includes('pdf')
            ? 'pdf'
            : response.data.content_type.includes('docx')
              ? 'docx'
              : response.data.content_type.includes('pptx')
                ? 'pptx'
                : response.data.content_type.includes('xlsx')
                  ? 'xlsx'
                  : response.data.content_type.includes('xls')
                    ? 'xls'
                    : response.data.content_type.includes('ppt')
                      ? 'ppt'
                      : response.data.content_type.includes('doc')
                        ? 'doc'
                        : response.data.type,
          analysisId,
        });

        // Process analysis data if available
        if (analysisId) {
          setVideoAnalysisId(analysisId);
          if (analysisJson && Array.isArray(analysisJson)) {
            // Format analysis data from preview response
            const formattedData = analysisJson
              .map(
                (item: {
                  detections: Array<{ label: string }>;
                  detection_count: number;
                  datetime: string;
                  detected_image_path: string;
                  timestamp: number | null;
                }) => ({
                  object:
                    (Array.isArray(item.detections) &&
                      item.detections.length > 0 &&
                      item.detections[0]?.label) ||
                    '-',
                  object_count: item.detection_count || '-',
                  detected_image_path: item.detected_image_path || '-',
                  detect_time: item.datetime || '-',
                  timestamp: item.timestamp,
                }),
              )
              .sort((a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0));
            setVideoAnalysisData(formattedData);
          } else {
            // Fallback: fetch from detail endpoint
            await getVideoAnalysisAPI(analysisId);
          }
        } else {
          setVideoAnalysisId(null);
          setVideoAnalysisData([]);
        }
      } catch (error) {
        console.error('[previewFileAPI] Error:', error);
        setViewFile(null);
        setVideoAnalysisId(null);
        setVideoAnalysisData([]);
        ToastTopHelper.error(
          error?.response?.data?.message || t('Expected error'),
        );
        // Re-throw to allow callers to handle the error (e.g., set previewError state)
        throw error;
      } finally {
        hideLoading();
      }
    },
    [
      showLoading,
      hideLoading,
      setViewFile,
      setVideoAnalysisId,
      setVideoAnalysisData,
      t,
    ],
  );

  const getVideoAnalysisAPI = useCallback(
    async (analysisId: number) => {
      try {
        setLoadingAnalysis(true);
        const response = await API.get(endpoint.detailDataAnalysis(analysisId));
        const analysis = response.data?.analysis || [];
        if (Array.isArray(analysis)) {
          const formattedData = analysis
            .map(
              (item: {
                detections: Array<{ label: string }>;
                detection_count: number;
                datetime: string;
                detected_image_path: string;
                timestamp: number | null;
              }) => ({
                object:
                  (Array.isArray(item.detections) &&
                    item.detections.length > 0 &&
                    item.detections[0]?.label) ||
                  '-',
                object_count: item.detection_count || '-',
                detected_image_path: item.detected_image_path || '-',
                detect_time: item.datetime || '-',
                timestamp: item.timestamp,
              }),
            )
            .sort((a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0));
          setVideoAnalysisData(formattedData);
        } else {
          setVideoAnalysisData([]);
        }
      } catch (error) {
        console.error('Error fetching video analysis:', error);
        setVideoAnalysisData([]);
      } finally {
        setLoadingAnalysis(false);
      }
    },
    [setLoadingAnalysis, setVideoAnalysisData],
  );

  const downloadFileAPI = useCallback(
    async (object_paths: string[], type: string) => {
      const fileKey = `${dayjs().format('YYYY-MM-DD')}-${object_paths.join('-')}`;
      try {
        let filename = 'download.zip';

        if (object_paths.length > 1) {
          filename = `media-data-${Date.now()}.zip`;
        } else if (object_paths.length == 1 && type === 'file') {
          const pathParts = object_paths[0].split('/');
          filename = pathParts[pathParts.length - 1];
        } else if (object_paths.length == 1 && type === 'folder') {
          filename = `media-data-${Date.now()}.zip`;
        }

        await addListDownloadFile({
          id_file: fileKey,
          name: filename,
          type: 'downloadFileAll',
          userId: currentUserId,
        });

        const response = await API.post(endpoint.downloadMediaDataFile, {
          object_paths,
        });
        const taskId = response?.data?.task_id;
        addTaskIdToFile(taskId, fileKey, 'downloadFileAll', 'download');
      } catch (error) {
        removeFile(fileKey, 'downloadFileAll');
        ToastTopHelper.error(
          (error as any)?.response?.data?.message || t('Expected error'),
        );
      }
    },
    [t, currentUserId],
  );

  const detectFileTypeAPI = useCallback(
    async ({
      media_items,
      detection_type,
    }: {
      media_items: { object_path: string; media_type: string }[];
      detection_type: string;
    }) => {
      try {
        showLoading();
        const response = await API.post(endpoint.detectFileType, {
          media_items: media_items,
          detection_type: detection_type,
        });

        ToastTopHelper.success(response.message, {
          autoClose: false,
        });
      } catch (error) {
        ToastTopHelper.error(
          error?.response?.data?.message || t('Expected error'),
        );
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading, t],
  );

  const getDetectionTypeAPI = useCallback(async () => {
    try {
      showLoading();
      const response = await API.get(endpoint.aiModels);

      setDetectionTypes(
        response.data.map((item: { code: string; name: string }) => ({
          value: item.code,
          label: item.name,
        })),
      );
    } catch (error) {
      ToastTopHelper.error(
        error?.response?.data?.message || t('Expected error'),
      );
    } finally {
      hideLoading();
    }
  }, [showLoading, hideLoading, t, setDetectionTypes]);

  return {
    data,
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    objSearch,
    setObjSearch,
    getMediaDataAPI,
    listError,
    setData,
    previewFileAPI,
    viewFile,
    downloadFileAPI,
    detectFileTypeAPI,
    getDetectionTypeAPI,
    detectionTypes,
    videoAnalysisData,
    videoAnalysisId,
    isLoadingAnalysis,
    getVideoAnalysisAPI,
  };
};
