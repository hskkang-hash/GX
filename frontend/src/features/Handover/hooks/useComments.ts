import { useCallback, useState } from 'react';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';

interface CommentAPIResponse {
  id: number;
  parent_id: number | null;
  content_text: string;
  writer__first_name?: string;
  writer__last_name?: string;
  writer__username?: string;
  writer_id?: number;
  created_by_id?: number;
  updated_time?: string;
  modified_on?: string;
  has_replies?: number;
  modified_by_id?: number | null;
  writer?: string;
}

export const useComments = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const [comments, setComments] = useState([]);
  const [totalPages, setTotalPages] = useState(0);

  const getCommentsAPI = useCallback(
    async ({
      notice_id,
      page_size,
      page_number,
      parent_id,
      append = false,
    }: {
      notice_id: number;
      page_size: number;
      page_number: number;
      parent_id?: number;
      append?: boolean;
    }) => {
      try {
        const response = await API.get(endpoint.comments, {
          params: {
            notice_id,
            page_size,
            page_number,
            parent_id,
          },
        });
        if (response.success && response.data?.items?.length) {
          const mappedComments = response.data.items.map(
            (item: CommentAPIResponse) => ({
              id: item.id,
              parentId: item.parent_id || undefined,
              content: item.content_text || '',
              writer_name:
                item.writer__first_name && item.writer__last_name
                  ? `${item.writer__first_name} ${item.writer__last_name}`
                  : item.writer__first_name ||
                    item.writer__username ||
                    item.writer ||
                    '',
              userId: item.writer_id || item.created_by_id,
              updated_time: item.updated_time || item.modified_on || '',
              count_child:
                item.has_replies && item.has_replies > 0
                  ? item.has_replies
                  : undefined,
              is_update: item.modified_by_id !== null,
              children: [],
            }),
          );

          if (parent_id) {
            // Load more replies - concat to existing
            setComments((prevList) => prevList.concat(mappedComments));
          } else if (append) {
            // Load more root comments - append to existing
            setComments((prevList) => prevList.concat(mappedComments));
            setTotalPages(response?.total_pages || 0);
          } else {
            // Load new comments - replace
            setComments(mappedComments);
            setTotalPages(response?.total_pages || 0);
          }
        } else if (!parent_id) {
          // Reset if no data and it's initial load
          setComments([]);
          setTotalPages(response?.total_pages || 0);
        }
      } catch (error) {
        setComments([]);
        setTotalPages(0);
      }
    },
    [showLoading, hideLoading],
  );

  const actionCommentAPI = useCallback(
    async ({
      notice_id,
      comment_id,
      comment,
      parent_id,
      is_update = false,
    }: {
      notice_id: number;
      comment_id?: number;
      comment: string;
      parent_id?: number;
      is_update?: boolean;
    }) => {
      try {
        showLoading();
        const data = is_update
          ? {
              comment_id: comment_id,
              comment: comment,
            }
          : {
              notice_id,
              comment: comment,
              parent_id: parent_id,
            };
        const response = await API.post(
          endpoint.comments,
          is_update ? { update_data: data } : { create_data: data },
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
              ?.data?.message || 'Something went wrong',
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading],
  );

  const deleteCommentAPI = useCallback(
    async ({ comment_id }: { comment_id: number }) => {
      try {
        showLoading();
        const response = await API.delete(endpoint.comments, {
          params: { id: comment_id },
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
              ?.data?.message || 'Something went wrong',
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading],
  );
  return {
    comments,
    setComments,
    getCommentsAPI,
    actionCommentAPI,
    deleteCommentAPI,
    totalPages,
    setTotalPages,
  };
};
