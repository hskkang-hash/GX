import { yupResolver } from '@hookform/resolvers/yup';
import React, { useEffect } from 'react';
import { Control, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  OffCanvas,
  ROLE_PERMISSION,
  useTheme,
} from 'rj-core';
import styled from 'styled-components';

import CustomCheckBox from '../../../components/Form/CustomCheckBox';
import PickColorInput from '../../../components/Form/PickColorInput';
import MultiLanguageHookForm from '../../../components/input/MultiLanguageHookForm';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import Colors from '../../../configs/Colors';
import {
  schemaOrderStatus,
  schemaOrderStatusIsSuperuser,
} from '../../../services/schemaForm';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';
import {
  OrderStatusFormValues,
  OrderStatusState,
} from '../types/orderStatus.types';
import { cleanFormSubmit } from '../utils/cleanFormSubmit';

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
  noMarginBottom?: boolean;
}>(({ mode, error, noMarginBottom }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  marginBottom: noMarginBottom ? '0rem !important' : '0.4rem',
  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
  alignContent: 'center',
}));

const OffcanvasOrderStatusForm = ({
  show,
  onHide,
  id,
  initialValues = null,
  onSubmit,
}: {
  show: boolean;
  onHide: () => void;
  id: string;
  initialValues?: OrderStatusState | null;
  onSubmit: (values: OrderStatusFormValues) => Promise<void>;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { getListGroup } = useCommonAPI();

  const methods = useForm({
    resolver: yupResolver(
      isRoleSuperuser ? schemaOrderStatusIsSuperuser : schemaOrderStatus,
    ),
  });

  const {
    handleSubmit,
    formState: { isSubmitting, isValid },
    control,
    reset,
    watch,
    setValue,
  } = methods;
  console.log('initialValues', initialValues);
  useEffect(() => {
    if (show && initialValues) {
      // Reset logic here
      reset({
        id: initialValues.id,
        name: {
          en: initialValues?.name_en_translation || '',
          ko: initialValues?.name_ko_translation || '',
          th: initialValues?.name_th_translation || '',
        },
        value: initialValues.value || '',
        text_color: initialValues?.text_color || '',
        background_color: initialValues?.background_color || '',
        border_color: initialValues?.border_color || '',
        group: initialValues?.group__id
          ? {
              value: initialValues?.group__id,
              label: initialValues?.group__name || '',
            }
          : null,
        no_background_color: initialValues?.no_background_color || false,
        no_border_color: initialValues?.no_border_color || false,
      } as Record<string, unknown>);
    } else {
      reset({
        name: {
          en: '',
          ko: '',
        },
        value: '',
        text_color: '#1D9BE2',
        background_color: '#E3F5FF',
        border_color: '',
        group: null as unknown as object,
        no_background_color: false,
        no_border_color: true,
      } as Record<string, unknown>);
    }
  }, [show, initialValues, reset]);

  const PreviewStatus = ({
    background_color,
    border_color,
    text_color,
  }: {
    background_color: string;
    border_color: string;
    text_color: string;
  }) => {
    return (
      <div
        style={{
          backgroundColor: background_color,
          border: `1px solid ${border_color || 'transparent'}`,
          color: text_color,
          width: 'fit-content',
          height: 'fit-content',
          borderRadius: '0.375rem',
          fontWeight: 600,
          fontSize: '0.875rem',
          opacity: 1,
          padding: '0.2rem 0.5rem',
          marginLeft: '1rem',
        }}
      >
        {t('Status')}
      </div>
    );
  };

  return (
    <OffCanvas
      title={initialValues ? t('Edit Status') : t('Add New Status')}
      show={show}
      onHide={onHide}
      id={id}
    >
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit((data: Record<string, unknown>) => {
            const transformedData: OrderStatusFormValues = isRoleSuperuser
              ? {
                  id: (data.id as number) ?? null,
                  name: {
                    en: (data.name as Record<string, string>)?.en || '',
                    ko: (data.name as Record<string, string>)?.ko || '',
                    th: (data.name as Record<string, string>)?.th || '',
                  },
                  group_id:
                    ((data.group as Record<string, unknown>)
                      ?.value as number) ?? null,
                  value: (data.value as string) || '',
                  text_color: (data.text_color as string) || '',
                  background_color: (data.background_color as string) || '',
                  border_color: (data.border_color as string) || '',
                }
              : {
                  id: (data.id as number) ?? null,
                  name: {
                    en: (data.name as Record<string, string>)?.en || '',
                    ko: (data.name as Record<string, string>)?.ko || '',
                    th: (data.name as Record<string, string>)?.th || '',
                  },
                  value: (data.value as string) || '',
                  text_color: (data.text_color as string) || '',
                  background_color: (data.background_color as string) || '',
                  border_color: (data.border_color as string) || '',
                };
            onSubmit(cleanFormSubmit(transformedData) as OrderStatusFormValues);
          })}
        >
          <div className="body-canvas d-flex gap-3">
            <MultiLanguageHookForm
              name="name"
              control={control as unknown as Control<Record<string, unknown>>}
              label={t('Name')}
              placeholder={t('Name')}
              required
              onLanguageChange={(lang) => console.log('Language:', lang)}
            />
            {isRoleSuperuser && (
              <PaginationSelect
                required
                label={t('Group')}
                name="group"
                control={control as unknown as Control<Record<string, unknown>>}
                loadOptions={getListGroup() as any}
                placeholder={t('Select')}
              />
            )}
            <CustomInputHookForm
              required
              name="value"
              label={t('Value')}
              placeholder={t('Value')}
            />
            <PickColorInput
              name="text_color"
              label={t('Color')}
              value={watch('text_color') as unknown as number}
            />
            <div>
              <StyledLabel mode={theme as 'light' | 'dark'}>
                {t('Background Color')}
              </StyledLabel>
              <div className="row g-2 align-items-center">
                <div className="col-9">
                  <PickColorInput
                    name="background_color"
                    value={watch('background_color') as unknown as number}
                    disabled={watch('no_background_color')}
                  />
                </div>
                <div className="col-3">
                  <CustomCheckBox
                    name="no_background_color"
                    control={control}
                    subLabel={t('No Color')}
                    onChangeValue={() => {
                      if (watch('no_background_color')) {
                        setValue('background_color', '');
                      }
                    }}
                  />
                </div>
              </div>
            </div>
            <div>
              <StyledLabel mode={theme as 'light' | 'dark'}>
                {t('Border Color')}
              </StyledLabel>
              <div className="row g-2 align-items-center">
                <div className="col-9">
                  <PickColorInput
                    name="border_color"
                    value={watch('border_color') as unknown as number}
                    disabled={watch('no_border_color')}
                  />
                </div>
                <div className="col-3">
                  <CustomCheckBox
                    name="no_border_color"
                    control={control}
                    subLabel={t('No Color')}
                    onChangeValue={() => {
                      if (watch('no_border_color')) {
                        setValue('border_color', '');
                      }
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="d-flex gap-2 align-items-center">
              <StyledLabel
                mode={theme as 'light' | 'dark'}
                noMarginBottom={true}
              >
                {t('Review')}
              </StyledLabel>
              <PreviewStatus
                background_color={
                  watch('background_color') as unknown as string
                }
                border_color={watch('border_color') as unknown as string}
                text_color={watch('text_color') as unknown as string}
              />
            </div>
          </div>
          <div className="offcanvas-footer">
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  actionType={
                    initialValues
                      ? ROLE_PERMISSION.UPDATE
                      : ROLE_PERMISSION.CREATE
                  }
                  type="submit"
                  size="lg"
                  disabled={isSubmitting || !isValid}
                  color="primary"
                  label={t('Save')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  size="lg"
                  color="secondary"
                  onClick={onHide}
                  label={t('Cancel')}
                />,
              ]}
            />
          </div>
        </form>
      </FormProvider>
    </OffCanvas>
  );
};

export default React.memo(OffcanvasOrderStatusForm);
