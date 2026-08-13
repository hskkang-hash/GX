import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  FormBlock,
  Main,
  ToastTopHelper,
} from 'rj-core';

import CustomSlider from '@/components/Form/CustomSlider';
import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import useBoolean from '@/hooks/useBoolean';
import { CustomRoutes } from '@/services/API';
import { schemaOtherEquipments } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../utils/CheckRoleAccount';
import useCommonAPI from '../useCommonAPI/useAPI';
import useEquipment from './hooks/useEquipment';

interface EquipmentFormData {
  data: {
    name: string;
    resolution: {
      width: { value: number | null; unit: string };
      height: { value: number | null; unit: string };
    };
    frame_rate: { value: number | null; unit: string };
    field_of_view: { value: [number, number]; unit: string };
    weight: {
      min: { value: number | null; unit: string };
      max: { value: number | null; unit: string };
    };
    image_stabilization: { value: number } | null;
    note: string;
  };
  group: SelectOption | null;
}

function parseEquipmentFormData(formData: EquipmentFormData) {
  return {
    name: formData.data.name,
    group_id: formData.group?.value ?? null,
    night_vision: false,
    thermal_imaging: false,
    image_stabilization_id: formData.data.image_stabilization?.value ?? 0,
    resolution: `${formData.data.resolution.width.value ?? 0}x${
      formData.data.resolution.height.value ?? 0
    }${formData.data.resolution.width.unit}`,
    field_of_view: `${formData.data.field_of_view.value[0]}-${formData.data.field_of_view.value[1]}${formData.data.field_of_view.unit}`,
    frame_rate: `${formData.data.frame_rate.value ?? 0}${formData.data.frame_rate.unit}`,
    weight: `${formData.data.weight.min.value ?? 0}-${
      formData.data.weight.max.value ?? 0
    }${formData.data.weight.min.unit}`,
    note: formData.data.note,
  };
}

const defaultData = {
  name: '',
  resolution: {
    width: { value: null, unit: 'px' },
    height: { value: null, unit: 'px' },
  },
  frame_rate: { value: null, unit: 'fps' },
  field_of_view: { value: [0, 0], unit: '°' },
  weight: {
    min: { value: null, unit: 'g' },
    max: { value: null, unit: 'g' },
  },
  image_stabilization: { value: null },
  note: '',
};

function mergeData(data: any) {
  return {
    ...defaultData,
    ...data,
    resolution: {
      ...defaultData.resolution,
      ...data?.resolution,
      width: {
        ...defaultData.resolution.width,
        ...(data?.resolution?.width ?? {}),
        value: data?.resolution?.width?.value ?? null,
        unit:
          data?.resolution?.width?.unit ?? defaultData.resolution.width.unit,
      },
      height: {
        ...defaultData.resolution.height,
        ...(data?.resolution?.height ?? {}),
        value: data?.resolution?.height?.value ?? null,
        unit:
          data?.resolution?.height?.unit ?? defaultData.resolution.height.unit,
      },
    },
    frame_rate: {
      ...defaultData.frame_rate,
      ...(data?.frame_rate ?? {}),
      value: data?.frame_rate?.value ?? null,
      unit: data?.frame_rate?.unit ?? defaultData.frame_rate.unit,
    },
    field_of_view: {
      ...defaultData.field_of_view,
      ...(data?.field_of_view ?? {}),
      value: Array.isArray(data?.field_of_view?.value)
        ? data.field_of_view.value
        : defaultData.field_of_view.value,
      unit: data?.field_of_view?.unit ?? defaultData.field_of_view.unit,
    },
    weight: {
      ...defaultData.weight,
      ...data?.weight,
      min: {
        ...defaultData.weight.min,
        ...(data?.weight?.min ?? {}),
        value: data?.weight?.min?.value ?? null,
        unit: data?.weight?.min?.unit ?? defaultData.weight.min.unit,
      },
      max: {
        ...defaultData.weight.max,
        ...(data?.weight?.max ?? {}),
        value: data?.weight?.max?.value ?? null,
        unit: data?.weight?.max?.unit ?? defaultData.weight.max.unit,
      },
    },
    image_stabilization: {
      ...defaultData.image_stabilization,
      ...(data?.image_stabilization ?? {}),
      value: data?.image_stabilization?.value ?? null,
    },
    note: data?.note ?? defaultData.note,
    name: data?.name ?? defaultData.name,
  };
}

export default function DetailEquipment() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [showModal, openModal, setHideModal] = useBoolean();
  const [loading, setLoading] = useState<boolean>(false);
  const { getOptionsByModel } = useCommonAPI();
  const { getDetailEquipment, updateEquipment } = useEquipment();
  const { id } = useParams();

  // Create resolver with current translation function that updates reactively
  const resolver = useMemo(
    () => yupResolver(schemaOtherEquipments(t, isRoleSuperuser)) as any,
    [t, isRoleSuperuser],
  );

  const methods = useForm({
    defaultValues: { data: defaultData, group: null },
    resolver,
    mode: 'onChange',
  });
  const {
    handleSubmit,
    control,
    reset,
    watch,
    clearErrors,
    trigger,
    formState: { isValid, isDirty, errors },
  } = methods;

  // Re-trigger validation when language changes to update error messages
  useEffect(() => {
    // Only trigger if there are existing errors to translate
    const hasErrors = Object.keys(errors).length > 0;
    if (hasErrors) {
      trigger();
    }
  }, [t, trigger]);

  const onSubmit = async (data: EquipmentFormData) => {
    setLoading(true);
    const payload = parseEquipmentFormData(data);
    const { success, message } = await updateEquipment(payload, Number(id));
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.otherEquipments.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.otherEquipments.path);
  };

  useEffect(() => {
    const fetchDetailEquipment = async () => {
      const { success, data } = await getDetailEquipment(Number(id));
      if (success) {
        reset({
          data: mergeData(data),
          group: data?.group,
        });
      }
    };
    fetchDetailEquipment();
  }, [id]);

  const watchedWidth = watch('data.resolution.width.value');
  const watchedHeight = watch('data.resolution.height.value');
  const watchedWeightMin = watch('data.weight.min.value');
  const watchedWeightMax = watch('data.weight.max.value');
  useEffect(() => {
    const handleValidation = async () => {
      if (watchedWidth != null && watchedHeight != null) {
        const widthNum = Number(watchedWidth);
        const heightNum = Number(watchedHeight);
        if (widthNum > heightNum) {
          clearErrors([
            'data.resolution.width.value',
            'data.resolution.height.value',
          ]);
        } else if (widthNum < heightNum) {
          await trigger(['data.resolution.height.value']);
        } else if (widthNum === heightNum) {
          await trigger([
            'data.resolution.width.value',
            'data.resolution.height.value',
          ]);
        }
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [watchedWidth, watchedHeight, clearErrors, trigger]);

  useEffect(() => {
    const handleValidation = async () => {
      if (watchedWeightMin != null && watchedWeightMax != null) {
        const minNum = Number(watchedWeightMin);
        const maxNum = Number(watchedWeightMax);
        if (minNum < maxNum) {
          clearErrors(['data.weight.min.value', 'data.weight.max.value']);
        } else if (minNum == maxNum) {
          await trigger(['data.weight.min.value', 'data.weight.max.value']);
        } else if (minNum > maxNum) {
          await trigger(['data.weight.min.value']);
        }
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [watchedWidth, watchedHeight, clearErrors, trigger]);

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CustomBreadcrumb
          items={[
            { url: '/other-equipments', text: t('Other Equipments') },
            { text: t('Edit Equipment') },
          ]}
          buttons={[
            <CustomBtn
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={handleCancel}
            />,
            <CustomBtn
              size="md"
              style={{ width: '6rem' }}
              label={t('Save')}
              type="submit"
              disabled={loading || !isValid || !isDirty}
            />,
          ]}
        />
        <Main>
          <div className="form-container">
            <FormBlock>
              <div
                className="form-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '1.5rem',
                }}
              >
                {isRoleSuperuser && (
                  <div className="grid-span-full">
                    <PaginationSelect
                      required
                      label={t('Group')}
                      name="group"
                      control={control}
                      loadOptions={getOptionsByModel({
                        name_modal: 'usergroup',
                        search_field: 'name',
                        key: 'name',
                        value: 'id',
                      })}
                      placeholder={t('Select')}
                    />
                  </div>
                )}
                {/* Name */}
                <CustomInputHookForm
                  name="data.name"
                  label={t('Name')}
                  placeholder={t('Name')}
                  required
                />

                {/* Resolution */}
                <div className="device-size">
                  <div className="device-size__label">
                    {t('Resolution')}{' '}
                    <span style={{ color: Colors.Red }}>*</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <UnitInput
                      name="data.resolution.width.value"
                      // label={t("Resolution")}
                      placeholder="0"
                      unit="px"
                      isRequired
                      onChange={() => {
                        methods.trigger('data.resolution.height.value');
                      }}
                      iconDivider={'x'}
                    />
                    <UnitInput
                      name="data.resolution.height.value"
                      unit="px"
                      isRequired
                      placeholder="0"
                    />
                  </div>
                </div>

                {/* Frame Rate */}
                <UnitInput
                  name="data.frame_rate.value"
                  label={t('Frame Rate (FPS)')}
                  unit="FPS"
                  isRequired
                  placeholder="0"
                />

                {/* Field of View (FOV) */}
                <CustomSlider
                  name="data.field_of_view.value"
                  label={t('Field of View (FOV) (Degrees)')}
                  control={control}
                  min={0}
                  max={360}
                  step={1}
                  range
                  unit=""
                  required
                />

                {/* Weight */}
                <div className="device-size">
                  <div className="device-size__label">
                    {t('Weight')} <span style={{ color: Colors.Red }}>*</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <UnitInput
                      name="data.weight.min.value"
                      unit="g"
                      isRequired
                      placeholder="0"
                      iconDivider={'-'}
                    />
                    <UnitInput
                      name="data.weight.max.value"
                      unit="g"
                      isRequired
                      placeholder="0"
                    />
                  </div>
                </div>

                {/* Image Stabilization */}
                <PaginationSelect
                  name="data.image_stabilization"
                  label={t('Image Stabilization')}
                  control={control}
                  required
                  placeholder={t('Select')}
                  loadOptions={getOptionsByModel({
                    name_modal: 'imagestabilization',
                    search_field: 'name',
                  })}
                />

                {/* Note */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <CustomInputHookForm
                    name="data.note"
                    label={t('Note')}
                    placeholder={t('Note')}
                  />
                </div>
              </div>
            </FormBlock>
          </div>
        </Main>
      </form>

      <CustomModal
        title={t('Save changes')}
        show={showModal}
        onHide={setHideModal}
      >
        <div style={{ width: '25rem' }}>
          {t(
            'Your unsaved changes will be lost. Do you want to save changes before leaving?',
          )}
        </div>

        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="submit"
              color="primary"
              size="lg"
              onClick={() => {
                handleSubmit(onSubmit)();
                // setHideModal();
              }}
              label={t('Save')}
              disabled={loading || !isValid}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              onClick={setHideModal}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </FormProvider>
  );
}
