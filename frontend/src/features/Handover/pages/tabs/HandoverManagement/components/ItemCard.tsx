import { ConfigProvider, theme as antdTheme } from 'antd';
import TextArea from 'antd/es/input/TextArea';
import {
  useEffect,
  useImperativeHandle,
  forwardRef,
  useState,
  useRef,
} from 'react';
import { Controller, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomModal,
  FormBlock,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import CustomCheckBox from '../../../../../../components/Form/CustomCheckBox';
import i18n from '../../../../../../i18n';
import { useDateTimeFormat } from '../../../../hooks/useDateFormat';
import { HandoverNoticeState } from '../../../../types';
import { formatDateTime } from '../../../../utils/dateFormat';
import { useHandoverManagement } from '../hooks/useHandoverManagement';
import { failureLine } from '@/features/session/apiFailure';

export interface ItemCardRef {
  isDirty: boolean;
  handleSave: () => Promise<boolean>;
}

export const ItemCard = forwardRef<
  ItemCardRef,
  {
    item: HandoverNoticeState;
    handleGetListNoticeHandover: (temp_id?: number) => void;
    onDirtyChange?: (isDirty: boolean) => void;
    onRemoveItem?: (itemId: number) => void;
  }
>(
  (
    {
      item,
      handleGetListNoticeHandover,
      onDirtyChange,
      onRemoveItem = () => {},
    },
    ref,
  ) => {
    const { t } = useTranslation();
    const [theme] = useTheme();
    const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();
    const methods = useForm<{ content: string; is_notice: boolean }>({
      defaultValues: {
        content: item.content || '',
        is_notice: item.is_notice || false,
      },
    });

    const [showModalDelete, setShowModalDelete] = useState(false);
    const { createNoticeHandoverAPI, deleteNoticeHandoverAPI } =
      useHandoverManagement();

    const {
      control,
      handleSubmit,
      reset,
      getValues,
      formState: { isDirty, isValid },
    } = methods;

    const onDirtyChangeRef = useRef(onDirtyChange);
    useEffect(() => {
      onDirtyChangeRef.current = onDirtyChange;
    }, [onDirtyChange]);

    useEffect(() => {
      if (onDirtyChangeRef.current) {
        onDirtyChangeRef.current(isDirty);
      }
    }, [isDirty]);

    const handleSave = async (values?: {
      content: string;
      is_notice: boolean;
    }): Promise<boolean> => {
      const formValues = values || getValues();
      // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절이 「저장됨」으로 읽히지 않게 한다.**
      //   이 함수는 `boolean` 을 돌려주고, 그 값으로 화면을 떠날지 말지가 갈린다.
      //   `try` 가 없던 종전에는 거절이 예외가 되어 **`false` 조차 못 돌려줬다** —
      //   부르는 쪽의 `await` 도 같이 터지고, 사람은 아무 말도 못 듣는다.
      try {
        const { success, message } = await createNoticeHandoverAPI({
          handover_doc_id: item.handover_doc_id,
          content: formValues.content,
          is_notice: formValues.is_notice,
          content_id: item.id,
          is_edit: item.is_edit,
        });
        if (success) {
          ToastTopHelper.success(message);
          reset(formValues);
          handleGetListNoticeHandover(item.id);
          return true;
        }
        ToastTopHelper.error(message);
        return false;
      } catch (error) {
        ToastTopHelper.error(failureLine('ItemCard.save', error));
        // **거짓 `true` 를 돌려주지 않는다.** 저장 못 한 것을 저장했다고 답하면
        // 부르는 쪽이 서식을 깨끗한 것으로 표시하고 사람은 글을 잃는다.
        return false;
      }
    };

    const handleSaveWrapper = async (values: {
      content: string;
      is_notice: boolean;
    }) => {
      await handleSave(values);
    };

    useImperativeHandle(ref, () => ({
      isDirty,
      handleSave: async () => {
        if (!isDirty) return true;
        return await handleSave();
      },
    }));

    const handleDelete = async () => {
      // ★ [SEC-11a ② · 턴 J · 차선 C] 같은 파일 둘째 자리 — 여기도 `try` 가 없었다.
      try {
        const { success, message } = await deleteNoticeHandoverAPI({
          content_id: item.id,
          handover_doc_id: item.handover_doc_id,
        });
        if (success) {
          ToastTopHelper.success(message);
          handleGetListNoticeHandover(item.id);
        } else {
          ToastTopHelper.error(message);
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('ItemCard.delete', error));
      } finally {
        // 확인 상자는 **어느 갈래에서도 닫힌다.**
        setShowModalDelete(false);
      }
    };

    return (
      <FormBlock key={item.id}>
        <div className="d-flex flex-column gap-3">
          <FormProvider {...methods}>
            <form onSubmit={handleSubmit(handleSaveWrapper)}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr 1fr 0.5fr',
                  gap: '1.5rem',
                  fontSize: '1rem',
                }}
              >
                <div>
                  <span className="fw-bold me-3">
                    {t('handover.Created Date Handover')}
                  </span>
                  {item.created_time
                    ? formatDateTime(
                        item.created_time,
                        dateFormat,
                        timeFormat,
                        i18n.language,
                        timezoneCode,
                      )
                    : ''}
                </div>
                <div>
                  <span className="fw-bold me-3">
                    {t('handover.Updated Date-Handover')}
                  </span>
                  {item.updated_time
                    ? formatDateTime(
                        item.updated_time,
                        dateFormat,
                        timeFormat,
                        i18n.language,
                        timezoneCode,
                      )
                    : ''}
                </div>

                <div>
                  <span className="fw-bold me-3">
                    {t('handover.Creator-Handover')}
                  </span>
                  {item?.creator__full_name ? item?.creator__full_name : ''}
                </div>
                <div>
                  <span className="fw-bold me-3">
                    {t('handover.Editor-Handover')}
                  </span>
                  {item?.editor__full_name ? item?.editor__full_name : ''}
                </div>
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '14fr 2fr',
                  gap: '1rem',
                }}
              >
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
                      <TextArea
                        rows={4}
                        placeholder={t('handover.Enter text here')}
                        maxLength={1000}
                        style={{ height: 125, resize: 'none' }}
                        value={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                </ConfigProvider>
                <div className="d-flex flex-column gap-2">
                  <CustomCheckBox
                    name="is_notice"
                    subLabel={t('handover.Duplicate as a notice post')}
                    control={control}
                  />
                  <CustomBtn
                    type="submit"
                    color="primary"
                    size="lg"
                    label={t('handover.Save')}
                    disabled={!isValid || !isDirty}
                  />
                  <CustomBtn
                    type="button"
                    variant="outline"
                    color="secondary"
                    size="lg"
                    label={t('handover.Delete')}
                    onClick={() => {
                      if (item.is_edit === false) {
                        onRemoveItem(item.id);
                        setShowModalDelete(false);
                      } else {
                        setShowModalDelete(true);
                      }
                    }}
                  />
                </div>
              </div>
            </form>
          </FormProvider>
        </div>
        {showModalDelete && (
          <CustomModal
            title={t('handover.Delete Content')}
            show={showModalDelete}
            onHide={() => setShowModalDelete(false)}
          >
            <div style={{ width: '25rem' }}>
              {t('handover.Are you sure you want to delete this content?')}
            </div>
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  type="submit"
                  color="primary"
                  variant="outline"
                  size="lg"
                  onClick={() => {
                    handleDelete();
                  }}
                  label={t('handover.Delete')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="lg"
                  onClick={() => {
                    setShowModalDelete(false);
                  }}
                  label={t('handover.Cancel')}
                />,
              ]}
            />
          </CustomModal>
        )}
      </FormBlock>
    );
  },
);
