import { yupResolver } from '@hookform/resolvers/yup';
import React, { useEffect } from 'react';
import { Control, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, OffCanvas, ROLE_PERMISSION } from 'rj-core';

import MultiLanguageHookForm from '../../../components/input/MultiLanguageHookForm';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import { schemaChecklistSetting } from '../../../services/schemaForm';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';
import {
  ChecklistSettingFormValues,
  ChecklistSettingState,
} from '../types/checklistSetting.types';

const OffcanvasChecklistSettingForm = ({
  show,
  onHide,
  id,
  initialValues = null,
  onSubmit,
  loading,
}: {
  show: boolean;
  onHide: () => void;
  id: string;
  initialValues?: ChecklistSettingState | null;
  onSubmit: (values: ChecklistSettingFormValues) => Promise<void>;
  loading: boolean;
}) => {
  const { t } = useTranslation();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { getOptionsByModel } = useCommonAPI();

  const methods = useForm({
    defaultValues: {
      item_name: {
        en: '',
        ko: '',
        th: '',
      },
      category: null as any,
    },
    resolver: yupResolver(schemaChecklistSetting(isRoleSuperuser)),
  });

  const {
    handleSubmit,
    formState: { isValid },
    control,
    reset,
  } = methods;

  useEffect(() => {
    if (show && initialValues) {
      // Reset logic here
      reset({
        id: initialValues.id,
        item_name: {
          en: initialValues.item_name_translations?.en || '',
          ko: initialValues.item_name_translations?.ko || '',
          th: initialValues.item_name_translations?.th || '',
        },
        category: initialValues.category_id
          ? {
              value: initialValues.category_id,
              label: initialValues.category__name,
            }
          : undefined,
        group: initialValues.group__id
          ? {
              value: initialValues.group__id,
              label: initialValues.group__name,
            }
          : null,
      });
    } else {
      reset({
        item_name: {
          en: '',
          ko: '',
          th: '',
        },
        category: null as unknown as object,
      });
    }
  }, [show, initialValues, reset]);

  return (
    <OffCanvas
      title={initialValues ? t('Edit Item') : t('Add New Item')}
      show={show}
      onHide={onHide}
      id={id}
    >
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit((data) => {
            const transformedData: ChecklistSettingFormValues = {
              ...data,
              category: data.category.value || null,
              item_name: {
                en: data.item_name.en || '',
                ko: data.item_name.ko || '',
                th: data.item_name.th || '',
              },
            };
            onSubmit(transformedData);
          })}
        >
          <div className="body-canvas d-flex gap-2">
            <MultiLanguageHookForm
              name="item_name"
              control={
                control as unknown as Control<ChecklistSettingFormValues>
              }
              label={t('Name')}
              placeholder={t('Name')}
              required
              onLanguageChange={(lang) => console.log('Language:', lang)}
            />
            <PaginationSelect
              required
              label={t('Category')}
              name="category"
              control={
                control as unknown as Control<ChecklistSettingFormValues>
              }
              loadOptions={
                getOptionsByModel({
                  name_modal: 'ChecklistSettingCategory',
                  search_field: 'name',
                }) as unknown as any
              }
              placeholder={t('Select')}
            />
            {isRoleSuperuser && (
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
            )}
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
                  loading={loading}
                  disabled={loading || !isValid}
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

export default React.memo(OffcanvasChecklistSettingForm);
