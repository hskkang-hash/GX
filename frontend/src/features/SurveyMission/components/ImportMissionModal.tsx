import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import { useEffect, useMemo } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { Trans, useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
} from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { importSurveyMissionSchema } from '@/services/schemaForm';

import { useSurveyMission } from '../hooks/useSurveyMission';

interface ImportMissionFormValues {
  route_ids: string[];
  name: string | null;
  purpose_id: {
    code: string;
    label: string;
    value: number;
  } | null;
  log_collection: boolean;
  video_recording: boolean;
  video_analysis: boolean;
}

const ImportMissionModal = ({
  show,
  onClose,
  handleImportMission,
}: {
  show: boolean;
  onClose: () => void;
  refreshListMission: () => void;
  handleImportMission: (data: ImportMissionFormValues) => void | Promise<void>;
}) => {
  const { t } = useTranslation();
  const { getListRouteForImportMission } = useSurveyMission();
  const { getOptionsByModel, useFetchOptions } = useCommonAPI();

  const purposeConfig = useMemo(
    () => ({
      type: 'model' as const,
      params: { name_modal: 'MissionPurpose', search_field: 'name' },
    }),
    [],
  );
  const purpose = useFetchOptions(getOptionsByModel, purposeConfig);
  const defaultPurpose = purpose?.find(
    (item: any) => item.code === 'surveillance',
  );

  const methods = useForm<ImportMissionFormValues>({
    defaultValues: {
      route_ids: [],
      name: null,
      purpose_id: null,
      log_collection: false,
      video_recording: false,
      video_analysis: false,
    },
    resolver: yupResolver(importSurveyMissionSchema()),
  });

  const {
    control,
    watch,
    handleSubmit,
    formState: { isValid },
  } = methods;

  useEffect(() => {
    if (defaultPurpose) {
      methods.reset({
        ...methods.getValues(),
        purpose_id: defaultPurpose,
      });
    }
  }, [defaultPurpose]);

  return (
    <FormProvider {...methods}>
      <CustomModal
        title={t('SurveyMission.Import Mission')}
        show={show}
        onHide={onClose}
      >
        <div style={{ width: '37.5rem', paddingBottom: '1.6rem' }}>
          <Trans
            i18nKey="SurveyMission.ImportMissionText"
            components={{ bold: <strong className="font-bold" /> }}
            q
          />
        </div>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <PaginationSelect
            label={t('Route')}
            name="route_ids"
            required
            isMulti
            control={control}
            loadOptions={getListRouteForImportMission({
              key: 'name',
              value: 'id',
            })}
            placeholder={t('Select')}
          />
          <div className="form-grid-9-1 gap-3">
            <CustomInputHookForm
              control={control}
              required
              name="name"
              label={t('SurveyMission.Name')}
              placeholder={t('SurveyMission.Name')}
            />
            {/* <div className="align-content-center mt-4">
              <CustomSwitchBtn
                name="return_to_home"
                control={control}
                label={t('SurveyMission.Return')}
                isHorizontal
              />
            </div> */}
          </div>
          <PaginationSelect
            required
            label={t('SurveyMission.Purpose')}
            name="purpose_id"
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'MissionPurpose',
              search_field: 'name',
            })}
            placeholder={t('SurveyMission.Select')}
          />
          <div>
            <CustomCheckBox
              name="log_collection"
              control={control}
              label={t('SurveyMission.Log Collection')}
              subLabel={t('SurveyMission.Allow')}
            />
            <CustomCheckBox
              name="video_recording"
              control={control}
              label={t('SurveyMission.Video Recording')}
              subLabel={t('SurveyMission.Allow')}
            />
            <CustomCheckBox
              name="video_analysis"
              control={control}
              label={t('SurveyMission.Video Analysis')}
              subLabel={t('SurveyMission.Allow')}
            />
          </div>
        </Box>
        <ActionBtn
          styles={{ maxWidth: '100%' }}
          leftButtons={[
            <CustomBtn
              key="modal-save-btn"
              type="button"
              color="primary"
              size="lg"
              onClick={handleSubmit((data) => handleImportMission(data))}
              label={t('Import')}
              disabled={!isValid}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              key="modal-cancel-btn"
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              onClick={onClose}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </FormProvider>
  );
};

export default ImportMissionModal;
