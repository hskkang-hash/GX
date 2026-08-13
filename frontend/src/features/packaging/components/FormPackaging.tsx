import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  FormBlock,
  Main,
  ToastTopHelper,
  useConfigSystem,
  useTheme,
  useUserInfo,
} from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { schemaPackaging } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import './FormPackaging.scss';

// Define types for form data
interface FormData {
  code: string;
  name: string;
  dimensions: {
    length: {
      value: number;
      unit: string;
    };
    width: {
      value: number;
      unit: string;
    };
    height: {
      value: number;
      unit: string;
    };
    icon_device: string;
  };
  maximum_weight: {
    value: number;
    unit: string;
  };
  package_type_id: {
    value: number;
    type: string;
  };
  water_proof: boolean;
  fragile: boolean;
  note: string;
}

interface FormPackagingProps {
  initialData?: FormData;
  title: string;
  breadcrumbItems: { url?: string; text: string }[];
  loading: boolean;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
}

const FormPackaging = ({
  initialData,
  onSubmit,
  onCancel,
  loading,
  breadcrumbItems,
}: FormPackagingProps) => {
  const [configSystem, , , fetchFreshConfig] = useConfigSystem();
  const isRoleSuperuser = CheckRoleAccount('superuser');

  useEffect(() => {
    fetchFreshConfig();
  }, []);
  const formatIPValue = (value: string) => {
    if (!value) return '';
    const numbers = value.replace(/\D/g, '');
    return numbers ? `IP ${numbers}` : '';
  };

  const systemConfigUnit =
    configSystem?.['Unit Config']?.['unit_preferences']?.[
      'PackagingSpecification'
    ];

  console.log('systemConfigUnit', systemConfigUnit);

  const { getOptionsByModel } = useCommonAPI();
  const { t } = useTranslation();
  const userInfo = useUserInfo();
  console.log('userInfo', userInfo);
  const methods = useForm({
    defaultValues: initialData
      ? initialData
      : {
          code: 'D-' + new Date().getTime().toString(),
          name: '',
          group: {
            value: null,
            type: 'select',
          },
          dimensions: {
            length: {
              value: null,
              unit: 'mm',
            },
            width: {
              value: null,
              unit: 'mm',
            },
            height: {
              value: null,
              unit: 'mm',
            },
            icon_device: 'x',
          },
          maximum_weight: {
            value: null,
            unit: 'kg',
          },
          package_type_id: {
            value: null,
            type: 'select',
          },
          water_proof: '',
          fragile: false,
          note: '',
        },
    resolver: yupResolver(schemaPackaging(t, isRoleSuperuser)),
  });

  const {
    handleSubmit,
    control,
    setValue,
    reset,
    getValues,
    watch,
    formState,
  } = methods;
  const navigate = useNavigate();

  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
    if (systemConfigUnit) {
      setValue('dimensions.length.unit', systemConfigUnit.dimensions || 'mm');
      setValue('dimensions.width.unit', systemConfigUnit.dimensions || 'mm');
      setValue('dimensions.height.unit', systemConfigUnit.dimensions || 'mm');
      setValue('maximum_weight.unit', systemConfigUnit.max_weight || 'kg');
    }
  }, [initialData, reset, systemConfigUnit, setValue]);

  const [clickSave, setClickSave] = useState(false);
  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    try {
      await onSubmit(data);
      reset(data, {
        keepDirty: false,
        keepValues: true,
      });
      navigate(CustomRoutes.packaging.path);
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };
  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && formState.isDirty,
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const onError = (errors: Record<string, any>) => {
    console.log(errors);
    // Navigate to the tab with errors
    ToastTopHelper.error(t('Please fill in all required fields'));
  };

  const [theme] = useTheme();
  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        className="form-add-new-packaging"
      >
        <CustomBreadcrumb
          items={breadcrumbItems}
          buttons={[
            <CustomBtn
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={onCancel}
            />,
            <CustomBtn
              size="md"
              style={{ width: '6rem' }}
              label={t('Save')}
              type="submit"
              disabled={loading || !formState.isValid || !formState.isDirty}
              loading={formState.isSubmitting}
            />,
          ]}
        />
        <Main>
          <div className={`form-container ${theme}`}>
            <FormBlock>
              <div className="form-grid">
                {isRoleSuperuser && (
                  <div className="grid-span-full">
                    <PaginationSelect
                      name="group.value"
                      label={t('Group')}
                      required
                      control={control}
                      placeholder={t('Select')}
                      loadOptions={getOptionsByModel({
                        name_modal: 'usergroup',
                        search_field: 'name',
                        key: 'name',
                        value: 'id',
                      })}
                      className="flex-fill"
                    />
                  </div>
                )}
                <CustomInputHookForm
                  name="code"
                  label="ID"
                  disabled
                />
                <CustomInputHookForm
                  required
                  name="name"
                  label={t('Package Name')}
                />
                <div className="device-size">
                  <div className={`device-size__label`}>
                    {' '}
                    {t('Dimensions')}{' '}
                    <span style={{ color: Colors.Red }}>*</span>
                  </div>
                  <div className={`device-size__dimensions`}>
                    <UnitInput
                      name="dimensions.length.value"
                      unit={getValues('dimensions.length.unit')}
                      iconDivider="x"
                      placeholder={t('Length')}
                      onChange={(value) => {
                        setValue('dimensions.length.value', value);
                      }}
                    />
                    <UnitInput
                      name="dimensions.width.value"
                      unit={getValues('dimensions.width.unit')}
                      iconDivider="x"
                      placeholder={t('Width')}
                      onChange={(value) => {
                        setValue('dimensions.width.value', value);
                      }}
                    />
                    <UnitInput
                      name="dimensions.height.value"
                      unit={getValues('dimensions.height.unit')}
                      placeholder={t('Height')}
                      onChange={(value) => {
                        setValue('dimensions.height.value', value);
                      }}
                    />
                  </div>
                </div>
                <UnitInput
                  name="maximum_weight.value"
                  unit={getValues('maximum_weight.unit')}
                  label={t('Max Weight')}
                  placeholder={t('Max Weight')}
                  isRequired
                />

                <PaginationSelect
                  required
                  label={t('Packaging Type')}
                  name="package_type_id.value"
                  control={control}
                  loadOptions={getOptionsByModel({
                    name_modal: 'packagetype',
                    search_field: 'name',
                  })}
                  placeholder={t('Select')}
                />
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <div style={{ flex: 1 }}>
                    <CustomInputHookForm
                      name="water_proof"
                      label={t('Waterproof')}
                      placeholder={t('IP {number}')}
                      onChange={(e: any) => {
                        setValue('water_proof', formatIPValue(e.target.value));
                      }}
                    />
                  </div>
                  <CustomCheckBox
                    name="fragile"
                    label={t('Fragile')}
                    control={control}
                    minWidthStyle="80px"
                  />
                </div>

                <div className="grid-column-2">
                  <CustomInputHookForm
                    name="note"
                    label={t('Note')}
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
        onHide={() => setShowModal(false)}
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
              onClick={handleModalSave}
              label={t('Save')}
              loading={formState.isSubmitting}
              disabled={loading || formState.isSubmitting}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              onClick={handleModalCancel}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </FormProvider>
  );
};

export default FormPackaging;
