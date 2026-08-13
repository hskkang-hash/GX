import { yupResolver } from '@hookform/resolvers/yup';
import { useCallback, useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  useLoadingContext,
} from 'rj-core';
import * as yup from 'yup';

import { CustomSwitchBtn } from '../../../../../components/Form/CustomSwitchBtn';
import CustomSelect from '../../../../../components/selects/CustomSelect';
import API, { endpoint } from '../../../../../services/API';

interface StreamSettingModalProps {
  show: boolean;
  onHide: () => void;
  onSubmit: (data: StreamSettingData) => void;
  camera: any;
}

interface AIModel {
  id: number;
  name: string;
}

export interface StreamSettingData {
  id_stream: number | null;
  drone_id: number | null;
  ip: string;
  ai_model: number | null;
  display: boolean;
  ai_enabled: boolean;
}

const StreamSettingModal = ({
  show,
  onHide,
  onSubmit,
  camera,
}: StreamSettingModalProps) => {
  const INITIAL_VALUES = {
    id_stream: null,
    drone_id: null,
    ip: '',
    ai_model: null,
    display: true,
    ai_enabled: false,
  };

  const { t } = useTranslation();
  const { showLoadingGlobal, hideLoadingGlobal } = useLoadingContext();
  const [aiModelOptions, setAiModelOptions] = useState<
    Array<{ value: number; label: string }>
  >([]);

  const form = useForm<StreamSettingData>({
    defaultValues: INITIAL_VALUES,
    resolver: yupResolver(
      yup.object().shape({
        ai_model: yup.number().required(t('AI Model is required')),
      }),
    ),
  });
  const { handleSubmit, control, watch, setValue, reset } = form;

  useEffect(() => {
    if (show) {
      reset({
        id_stream: camera.id_stream,
        drone_id: camera.drone_id,
        ip: camera.ip_source,
        ai_model:
          camera.ai_models[camera.ai_models.length - 1]?.ai_model_id || null,
        display: camera.isVisualize,
        ai_enabled:
          camera.ai_models[camera.ai_models.length - 1]?.in_use || false,
      });
      fetchAIModels();
    } else {
      reset(INITIAL_VALUES);
    }
  }, [show]);

  const fetchAIModels = useCallback(async () => {
    try {
      showLoadingGlobal();
      const response = await API.get(endpoint.aiModels);

      setAiModelOptions(
        response.data.map((item: AIModel) => ({
          value: item.id,
          label: item.name,
        })),
      );
    } catch {
      setAiModelOptions([]);
    } finally {
      hideLoadingGlobal();
    }
  }, [showLoadingGlobal, hideLoadingGlobal]);

  return (
    <CustomModal
      title={t('Stream Setting')}
      show={show}
      onHide={onHide}
      style={{
        zIndex: '1200 !important',
      }}
    >
      <FormProvider {...form}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CustomInputHookForm
            name="ip"
            label={t('IP')}
            placeholder={t('IP')}
          />
          <CustomSelect
            name="ai_model"
            label={t('AI')}
            options={aiModelOptions}
            required
            control={control}
            value={
              aiModelOptions.find((opt) => opt.value === watch('ai_model')) ||
              null
            }
            setValue={(opt) => {
              if (opt) {
                setValue('ai_model', Number(opt.value));
              } else {
                setValue('ai_model', null);
              }
            }}
            placeholder={t('Select AI Model')}
          />
          <div className="d-flex gap-2 flex-row">
            <div className="flex-fill">
              <CustomSwitchBtn
                control={control}
                name="display"
                label={t('Display')}
                isHorizontal
              />
            </div>
            <div className="flex-fill">
              <CustomSwitchBtn
                control={control}
                name="ai_enabled"
                label={t('AI Enabled')}
                isHorizontal
              />
            </div>
          </div>
          <ActionBtn
            styles={{ maxWidth: '100%' }}
            leftButtons={[
              <CustomBtn
                type="submit"
                variant="contained"
                color="primary"
                size="lg"
                label={t('Save')}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={onHide}
                label={t('Cancel')}
              />,
            ]}
          />
        </form>
      </FormProvider>
    </CustomModal>
  );
};

export default StreamSettingModal;
