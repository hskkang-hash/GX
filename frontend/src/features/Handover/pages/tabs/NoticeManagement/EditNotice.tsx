import { ConfigProvider, theme as antdTheme } from 'antd';
import TextArea from 'antd/es/input/TextArea';
import { useCallback, useEffect, useState } from 'react';
import { Controller, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  OffCanvas,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
  useUserInfo,
} from 'rj-core';

import { AttachedFilesUpload } from '../../../../../components/Form/AttachedFilesUpload';
import i18n from '../../../../../i18n';
import NestedComments from '../../../components/NestedComments/NestedComments';
import { useComments } from '../../../hooks/useComments';
import { useDateTimeFormat } from '../../../hooks/useDateFormat';
import { useHandover } from '../../../hooks/useHandover';
import { NoticeManagementState } from '../../../types';
import { formatDateTime } from '../../../utils/dateFormat';
import { useNoticeManagement } from './hooks/useNoticeManagement';
import './styles/EditNotice.scss';
import { failureLine } from '@/features/session/apiFailure';

const EditNotice = ({
  noticeId,
  isCompletedNotice = false,
  open,
  onClose,
  handleRefresh,
}: {
  noticeId: number | null;
  open: boolean;
  onClose: () => void;
  isCompletedNotice?: boolean;
  handleRefresh: () => void;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const userInfo = useUserInfo();
  const currentUserId = (userInfo as { id?: number })?.id;
  const [showComments, setShowComments] = useState({});
  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();
  const methods = useForm({
    defaultValues: {
      id: 0,
      created_time: '',
      creator: '',
      updated_time: '',
      editor: '',
      content: '',
      files: [] as File[],
      deleted: false,
    },
  });
  const [currentPage, setCurrentPage] = useState(1);
  const {
    comments,
    setComments,
    getCommentsAPI,
    actionCommentAPI,
    deleteCommentAPI,
    totalPages,
  } = useComments();

  const { completeNoticeAPI, deleteNoticeAPI, restoreNoticeAPI } =
    useHandover();

  const { addNoticeAPI, getNoticeManagementByIdAPI, cancelCompletedNoticeAPI } =
    useNoticeManagement();

  const {
    handleSubmit,
    watch,
    control,
    formState: { isSubmitting, isDirty, isValid },
  } = methods;

  const getDetailNotice = useCallback(async () => {
    if (!noticeId) return;
    // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절을 삼키지 않는다.**
    //   이 파일에는 `await` 가 여덟인데 `try` 가 **하나도 없었다.** 접두 승격이 켜지면
    //   그 여덟이 전부 예외로 끝나고, 전역 `unhandledrejection` 처리기는 0건이다 —
    //   즉 서식이 빈 채로 뜨고 단추는 아무 말도 안 한다.
    try {
    const { success, data, message } =
      await getNoticeManagementByIdAPI(noticeId);
    if (success) {
      const noticeData = data as NoticeManagementState;
      methods.reset({
        id: noticeData?.id || 0,
        created_time: noticeData?.created_time || '',
        creator: noticeData?.creator__full_name || '',
        updated_time: noticeData?.updated_time || '',
        editor: noticeData?.editor__full_name || '',
        content: noticeData?.content || '',
        files: noticeData?.files || [],
        deleted: noticeData?.deleted ?? false,
      });
    } else {
      ToastTopHelper.error(message);
    }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.detail', error));
    }
  }, [noticeId, methods, getNoticeManagementByIdAPI]);

  useEffect(() => {
    if (noticeId) {
      getDetailNotice();
    }
  }, [noticeId]);

  useEffect(() => {
    if (open && noticeId) {
      setComments([]);
      setShowComments({});
      setCurrentPage(1);
      getCommentsAPI({
        notice_id: noticeId,
        page_size: 5,
        page_number: 1,
      });
    } else if (!open) {
      // Reset when closing
      setComments([]);
      setShowComments({});
      setCurrentPage(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, noticeId]);

  const loadMoreComment = async (params: {
    parent_id: string | number;
  }): Promise<void> => {
    if (!noticeId) return;
    const newParams = {
      notice_id: noticeId,
      page_size: 5,
      page_number: currentPage,
      parent_id: Number(params.parent_id),
    };
    getCommentsAPI(newParams);
  };

  const onReplyComment = async (value: {
    comment_id?: string | number;
    parent_id?: string | number;
    comment: string;
  }): Promise<void> => {
    if (!noticeId) return;
    const params = value?.comment_id
      ? {
          notice_id: noticeId,
          comment_id: Number(value.comment_id),
          comment: value.comment,
          is_update: true,
        }
      : {
          notice_id: noticeId,
          comment: value.comment,
          parent_id: value.parent_id ? Number(value.parent_id) : undefined,
          is_update: false,
        };

    // ★ [SEC-11a ② · 턴 J · 차선 C] 돌려준 값을 **읽지도 않던** 자리다 —
    //   댓글이 안 달려도 화면은 목록만 새로 그리고 아무 말도 안 했다.
    try {
      await actionCommentAPI(params);
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.comment', error));
      return;
    }

    // Refresh comments from page 1
    setComments([]);
    setCurrentPage(1);
    getCommentsAPI({
      notice_id: noticeId,
      page_size: 5,
      page_number: 1,
    });
    setShowComments({});
  };

  const onDeleteComment = async (id: string | number): Promise<void> => {
    if (!noticeId) return;
    try {
    const { success, message } = await deleteCommentAPI({
      comment_id: Number(id),
    });
    if (success) {
      ToastTopHelper.success(message);
      // Refresh comments from page 1
      setShowComments({});
      setComments([]);
      setCurrentPage(1);
      getCommentsAPI({
        notice_id: noticeId,
        page_size: 5,
        page_number: 1,
      });
    } else {
      ToastTopHelper.error(message);
    }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.deleteComment', error));
    }
  };

  const handleLoadMoreComments = async (): Promise<void> => {
    if (!noticeId || currentPage >= totalPages) return;
    const nextPage = currentPage + 1;
    setCurrentPage(nextPage);
    getCommentsAPI({
      notice_id: noticeId,
      page_size: 5,
      page_number: nextPage,
      append: true,
    });
  };

  const onSubmit = async (data: { content: string; files: File[] }) => {
    const { content, files } = data;

    try {
      const { success, message } = await addNoticeAPI({
        id: noticeId,
        content,
        files,
      });
      if (success) {
        ToastTopHelper.success(message);
        onClose();
        handleRefresh();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.submit', error));
    }
  };

  const handleCompleteNotice = async () => {
    if (!noticeId) return;
    try {
      const { success, message } = await completeNoticeAPI(noticeId);
      if (success) {
        ToastTopHelper.success(message);
        onClose();
        handleRefresh();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.complete', error));
    }
  };

  const handleCancelCompletedNotice = async () => {
    if (!noticeId) return;
    try {
      const { success, message } = await cancelCompletedNoticeAPI(noticeId);
      if (success) {
        ToastTopHelper.success(message);
        onClose();
        handleRefresh();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.cancelCompleted', error));
    }
  };

  const handleDeleteNotice = async () => {
    if (!noticeId) return;
    try {
      const { success, message } = await deleteNoticeAPI(noticeId);
      if (success) {
        ToastTopHelper.success(message);
        handleRefresh();
        getDetailNotice();

        !isCompletedNotice && onClose();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.delete', error));
    }
  };

  const handleRestoreNotice = async () => {
    if (!noticeId) return;
    try {
      const { success, message } = await restoreNoticeAPI(noticeId);
      if (success) {
        ToastTopHelper.success(message);
        handleRefresh();
        getDetailNotice();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('EditNotice.restore', error));
    }
  };

  return (
    <OffCanvas
      show={open}
      title={t('handover.Edit Notice')}
      onHide={onClose}
      id="edit-notice"
    >
      <div className="body-canvas">
        <FormProvider {...methods}>
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="d-flex flex-column gap-3">
              <div className="d-flex">
                <span
                  className="fw-bold "
                  style={{ minWidth: '10rem' }}
                >
                  {t('handover.Created Date Handover')}
                </span>
                <span>
                  {watch('created_time')
                    ? formatDateTime(
                        watch('created_time'),
                        dateFormat,
                        timeFormat,
                        i18n.language,
                        timezoneCode,
                      )
                    : ''}
                </span>
              </div>
              <div className="d-flex">
                <span
                  className="fw-bold "
                  style={{ minWidth: '10rem' }}
                >
                  {t('handover.Creator')}
                </span>
                <span>{watch('creator') ? watch('creator') : ''}</span>
              </div>
              <div className="d-flex">
                <span
                  className="fw-bold"
                  style={{ minWidth: '10rem' }}
                >
                  {t('handover.Updated Date')}
                </span>
                <span>
                  {watch('updated_time')
                    ? formatDateTime(
                        watch('updated_time'),
                        dateFormat,
                        timeFormat,
                        i18n.language,
                        timezoneCode,
                      )
                    : ''}
                </span>
              </div>
              <div className="d-flex">
                <span
                  className="fw-bold "
                  style={{ minWidth: '10rem' }}
                >
                  {t('handover.Editor')}
                </span>
                <span>{watch('editor') ? watch('editor') : ''}</span>
              </div>
              <div>
                <ConfigProvider
                  theme={{
                    algorithm:
                      theme === 'dark'
                        ? antdTheme.darkAlgorithm
                        : antdTheme.defaultAlgorithm,
                  }}
                >
                  <Controller
                    control={control}
                    name="content"
                    render={({ field }) => (
                      <div>
                        <label className={`custom-checkbox-label ${theme}`}>
                          {t('handover.Content')}
                        </label>
                        <TextArea
                          rows={4}
                          placeholder={t('handover.Enter text here')}
                          maxLength={1000}
                          style={{ height: 125, resize: 'none' }}
                          value={field.value}
                          onChange={field.onChange}
                          disabled={isCompletedNotice}
                        />
                      </div>
                    )}
                  />
                </ConfigProvider>
              </div>
              <div>
                <AttachedFilesUpload
                  name="files"
                  disabled={isCompletedNotice}
                  control={control}
                  buttonLabel={t('handover.Add File')}
                />
              </div>
              <div>
                {watch('deleted') ? (
                  <>
                    <div className="d-flex gap-3">
                      <CustomBtn
                        type="button"
                        label={t('handover.Restore Notice')}
                        color="primary"
                        variant="outline"
                        onClick={handleRestoreNotice}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="d-flex gap-3">
                      <CustomBtn
                        type="button"
                        label={
                          isCompletedNotice
                            ? t('handover.Cancel Completed')
                            : t('handover.Complete Notice')
                        }
                        color="primary"
                        variant="outline"
                        onClick={
                          isCompletedNotice
                            ? handleCancelCompletedNotice
                            : handleCompleteNotice
                        }
                      />
                      <CustomBtn
                        type="button"
                        label={t('handover.Delete Notice')}
                        color="secondary"
                        variant="outline"
                        onClick={handleDeleteNotice}
                      />
                    </div>
                  </>
                )}
                <div style={{ height: 'fit-content' }}>
                  <NestedComments
                    data={comments}
                    loadMoreComment={loadMoreComment}
                    commentAdded={onReplyComment}
                    onDelete={onDeleteComment}
                    paginationSize={5}
                    userId={currentUserId}
                    showComments={showComments}
                    setShowComments={setShowComments}
                    disableComment={watch('deleted')}
                    totalPages={totalPages}
                    currentPage={currentPage}
                    onLoadMore={handleLoadMoreComments}
                    maxHeight="27.5rem"
                  />
                </div>
              </div>
            </div>
            <div
              className="offcanvas-footer"
              style={{
                bottom: isCompletedNotice ? '1rem' : 0,
                right: isCompletedNotice ? '8.4rem' : '1.4rem',
              }}
            >
              {!isCompletedNotice ? (
                <ActionBtn
                  leftButtons={[
                    <CustomBtn
                      label={t('handover.Save')}
                      actionType={ROLE_PERMISSION.UPDATE}
                      type="submit"
                      variant="contained"
                      color="primary"
                      size="lg"
                      loading={isSubmitting}
                      disabled={!isDirty || !isValid || isSubmitting}
                    />,
                  ]}
                  rightButtons={[
                    <CustomBtn
                      label={t('handover.Cancel')}
                      type="button"
                      onClick={() => {
                        onClose();
                      }}
                      variant="outline"
                      color="secondary"
                      size="lg"
                    />,
                  ]}
                />
              ) : (
                <CustomBtn
                  label={t('handover.Cancel')}
                  type="button"
                  onClick={() => {
                    onClose();
                  }}
                  variant="outline"
                  color="secondary"
                  size="lg"
                />
              )}
            </div>
          </form>
        </FormProvider>
      </div>
    </OffCanvas>
  );
};

export default EditNotice;
