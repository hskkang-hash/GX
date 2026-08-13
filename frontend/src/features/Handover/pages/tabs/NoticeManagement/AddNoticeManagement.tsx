import { ConfigProvider, theme as antdTheme } from 'antd';
import TextArea from 'antd/es/input/TextArea';
import dayjs from 'dayjs';
import { useCallback, useMemo } from 'react';
import { Controller, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  ToastTopHelper,
  useTheme,
  useUserInfo,
} from 'rj-core';

import { AttachedFilesUpload } from '../../../../../components/Form/AttachedFilesUpload';
import { CustomRoutes } from '../../../../../services/API';
import i18n from '../../../../../i18n';
import { useDateFormat, useTimezoneCode } from '../../../hooks/useDateFormat';
import { formatDate } from '../../../utils/dateFormat';
import { useNoticeManagement } from './hooks/useNoticeManagement';

export const AddNoticeManagement = () => {
  const { t } = useTranslation();
  const userProfile = useUserInfo();
  const [theme] = useTheme();
  const navigate = useNavigate();
  const userInfo = useUserInfo();
  const { dateFormat } = useDateFormat();
  const { timezoneCode } = useTimezoneCode();
  const methods = useForm({
    defaultValues: {
      created_time: `${formatDate(dayjs(), dateFormat, i18n.language, timezoneCode)} HH:mm:ss`,
      creator: (userProfile as { profile__name?: string })?.profile__name || '',
      editor: '',
      content: '',
      is_notice: false,
      files: [] as File[],
    },
  });
  const { handleSubmit, control, watch } = methods;

  const { addNoticeAPI } = useNoticeManagement();

  const handleAddNotice = useCallback(
    async (data: { content: string; files: File[] }) => {
      const { success, message } = await addNoticeAPI(data);
      if (success) {
        ToastTopHelper.success(message);
        navigate(CustomRoutes.handover.path + '?tab=notice-management');
      } else {
        ToastTopHelper.error(message);
      }
    },
    [addNoticeAPI, navigate],
  );

  const handleCancel = useCallback(() => {
    navigate(CustomRoutes.handover.path + '?tab=notice-management');
  }, [navigate]);

  return (
    <Container>
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(handleAddNotice)}>
          <CustomBreadcrumb
            items={[
              { url: CustomRoutes.handover.path + '?tab=notice-management' },
              { text: t('handover.Create Notice') },
            ]}
            buttons={[
              <CustomBtn
                label={t('handover.Cancel')}
                variant="outline"
                color="secondary"
                size="md"
                style={{ width: '6rem' }}
                type="button"
                onClick={handleCancel}
              />,
              <CustomBtn
                label={t('handover.Publish')}
                variant="contained"
                color="primary"
                size="md"
                style={{ width: '6rem' }}
                type="submit"
              />,
            ]}
          />
          <Main>
            <FormBlock>
              <div className="d-flex flex-column gap-3">
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr',
                  }}
                >
                  <div>
                    <span className="fw-bold">
                      {t('handover.Created Date Handover')}
                    </span>{' '}
                    {watch('created_time')
                      ? formatDate(
                          watch('created_time'),
                          dateFormat,
                          i18n.language,
                          timezoneCode,
                        )
                      : ''}
                  </div>
                  <div>
                    <span className="fw-bold">{t('handover.Creator')}</span>{' '}
                    {watch('creator') ? watch('creator') : ''}
                  </div>
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
                          />
                        </div>
                      )}
                    />
                  </ConfigProvider>
                </div>
                <div>
                  <AttachedFilesUpload
                    name="files"
                    control={control}
                    buttonLabel={t('handover.Add File')}
                  />
                </div>
              </div>
            </FormBlock>
          </Main>
        </form>
      </FormProvider>
    </Container>
  );
};
