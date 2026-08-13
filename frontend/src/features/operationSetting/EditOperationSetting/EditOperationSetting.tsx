import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import { memo, useCallback, useEffect, useState } from 'react';
import { FormProvider, useForm, useController, Control } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomBtn,
  CustomInputHookForm,
  OffCanvas,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import CustomRadio from '@/components/Form/CustomRadio';
import CustomTextarea from '@/components/Form/CustomTextarea';
import PaginationSelect from '@/components/selects/PaginationSelect';
import API, { endpoint } from '@/services/API';
import { schemaOperationSetting } from '@/services/schemaForm';

import { SelectOption } from '../../../components/selects/CustomSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';

const METHODS_OPTIONS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'PATCH', label: 'PATCH' },
  { value: 'DELETE', label: 'DELETE' },
] as const;

interface FormDataProps {
  menu_id: number;
  tab_id: number;
  name: string;
  group?: SelectOption | null;
  is_active: boolean;
  api_url: string;
  url: string;
  http_method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  api_params: string;
  expected_response: string;
  body_params: string;
  receive_data: boolean;
  send_data: boolean;
  retry_count: number;
  timeout_seconds: number;
  description: string;
  notes: string;
}

// Interface cho API (object values)
interface ApiDataProps {
  group_id?: number;
  menu_id: number;
  tab_id: number;
  name: string;
  is_active: boolean;
  api_url: string;
  url: string;
  http_method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  api_params: object;
  expected_response: object;
  body_params: object;
  receive_data: boolean;
  send_data: boolean;
  retry_count: number;
  timeout_seconds: number;
  description: string;
  notes: string;
}

export default memo(function EditOperationSetting({
  open,
  onClose,
  data,
  refreshData,
}: {
  open: boolean;
  onClose: () => void;
  data: any; // API data với objects
  refreshData: () => void;
}) {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [isActive, setIsActive] = useState(true);
  const [isDataLoaded, setIsDataLoaded] = useState(false);
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { getOptionsByModel } = useCommonAPI();

  // Backup original values from API
  const [originalValues, setOriginalValues] = useState({
    api_url: '',
    is_active: true,
    http_method: 'GET' as const,
    api_params: '{}',
    body_params: '{}',
    expected_response: '{}',
  });

  const methods = useForm<FormDataProps>({
    defaultValues: {
      menu_id: 0,
      tab_id: 0,
      name: '',
      group: null,
      is_active: true,
      api_url: '',
      url: '',
      api_params: '',
      expected_response: '',
      body_params: '',
      retry_count: 0,
      timeout_seconds: 0,
      http_method: 'GET',
      receive_data: false,
      send_data: false,
      description: '',
      notes: '',
    },
    resolver: yupResolver(schemaOperationSetting(isRoleSuperuser)),
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const {
    handleSubmit,
    control,
    setValue,
    watch,
    reset,
    trigger,
    clearErrors,
    formState: { isValid, isDirty, isSubmitting },
  } = methods;

  const watchIsActive = watch('is_active');
  const watchHttpMethod = watch('http_method');

  // Helper function để transform API data thành form data
  const transformApiDataForForm = (apiData: any) => {
    const stringifyJsonField = (value: any): string => {
      if (!value) return '{}';
      if (typeof value === 'string') return value; // Đã là string
      return JSON.stringify(value, null, 2); // Convert object to string
    };

    return {
      ...apiData,
      api_params: stringifyJsonField(apiData.api_params),
      body_params: stringifyJsonField(apiData.body_params),
      expected_response: stringifyJsonField(apiData.expected_response),
    };
  };

  // Helper function để transform form data thành API data
  const transformFormDataForSubmit = useCallback(
    (formData: FormDataProps): ApiDataProps => {
      const parseJsonField = (value: string): object => {
        try {
          return value ? JSON.parse(value) : {};
        } catch (error) {
          console.warn('Failed to parse JSON, using empty object', error);
          return {};
        }
      };

      return isRoleSuperuser
        ? {
            ...formData,
            group_id: formData.group?.value as number,
            api_params: parseJsonField(formData.api_params),
            body_params: parseJsonField(formData.body_params),
            expected_response: parseJsonField(formData.expected_response),
          }
        : {
            ...formData,
            api_params: parseJsonField(formData.api_params),
            body_params: parseJsonField(formData.body_params),
            expected_response: parseJsonField(formData.expected_response),
          };
    },
    [isRoleSuperuser],
  );

  // Handle is_active change với backup/restore logic
  const handleIsActiveChange = (value: string) => {
    const newIsActive = value === 'true';
    setValue('is_active', newIsActive);

    if (newIsActive === originalValues.is_active) {
      // Restore về giá trị ban đầu từ API
      setValue('api_url', originalValues.api_url);
      setValue('http_method', originalValues.http_method);
      setValue('api_params', originalValues.api_params);
      setValue('body_params', originalValues.body_params);
      setValue('expected_response', originalValues.expected_response);
    } else {
      // Clear về default values khi chuyển sang trạng thái khác
      setValue('api_url', '');
      setValue('http_method', 'GET');
      // setValue("api_params", "{}");
      // setValue("body_params", "{}");
      // setValue("expected_response", "{}");
    }
  };

  const displayFollowMethod = (method: string) => {
    switch (method) {
      case 'GET':
        return (
          <>
            <CustomTextarea
              control={control}
              name="api_params"
              label={t('Param')}
              isRequired={true}
              placeholder={t('Enter Param')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="expected_response"
              label={t('Response')}
              isRequired={true}
              placeholder={t('Enter Response')}
              className="message-textarea"
              rows={10}
              disabled
              enableJsonFormat
            />
          </>
        );
      case 'POST':
        return (
          <>
            <CustomTextarea
              control={control}
              name="body_params"
              label={t('Body')}
              isRequired={true}
              placeholder={t('Enter Body')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="expected_response"
              label={t('Response')}
              isRequired={true}
              placeholder={t('Enter Response')}
              className="message-textarea"
              rows={10}
              disabled
              enableJsonFormat
            />
          </>
        );
      case 'PUT':
        return (
          <>
            <CustomTextarea
              control={control}
              name="api_params"
              label={t('Param')}
              isRequired={true}
              placeholder={t('Enter Param')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="body_params"
              label={t('Body')}
              isRequired={true}
              placeholder={t('Enter Body')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="expected_response"
              label={t('Response')}
              isRequired={true}
              placeholder={t('Enter Response')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
              disabled
            />
          </>
        );
      case 'PATCH':
        return (
          <>
            <CustomTextarea
              control={control}
              name="api_params"
              label={t('Param')}
              isRequired={true}
              placeholder={t('Enter Param')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="body_params"
              label={t('Body')}
              isRequired={true}
              placeholder={t('Enter Body')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="expected_response"
              label={t('Response')}
              isRequired={true}
              placeholder={t('Enter Response')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
              disabled
            />
          </>
        );
      case 'DELETE':
        return (
          <>
            <CustomTextarea
              control={control}
              name="api_params"
              label={t('Param')}
              isRequired={true}
              placeholder={t('Enter Param')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="body_params"
              label={t('Body')}
              isRequired={true}
              placeholder={t('Enter Body')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
            />
            <CustomTextarea
              control={control}
              name="expected_response"
              label={t('Response')}
              isRequired={true}
              placeholder={t('Enter Response')}
              className="message-textarea"
              rows={10}
              enableJsonFormat
              disabled
            />
          </>
        );
      default:
        return null;
    }
  };

  useEffect(() => {
    if (!isDataLoaded) return;

    const isActiveValue =
      String(watchIsActive) === 'true' || watchIsActive === true;
    setIsActive(isActiveValue);

    if (isActiveValue) {
      setValue('send_data', true);
      setValue('receive_data', false);
    } else {
      setValue('send_data', false);
      setValue('receive_data', true);
    }

    // Clear errors và trigger validation cho api_url
    clearErrors();
    setTimeout(() => {
      trigger('api_url');
    }, 100);
  }, [watchIsActive, setValue, trigger, clearErrors, isDataLoaded]);

  useEffect(() => {
    if (!isDataLoaded) return;

    if (watchIsActive && watchHttpMethod) {
      setTimeout(() => {
        trigger(['api_url', 'api_params', 'body_params', 'expected_response']);
      }, 100);
    } else if (!watchIsActive) {
      setTimeout(() => {
        trigger(['api_url']);
      }, 100);
    }
  }, [watchHttpMethod, watchIsActive, trigger, isDataLoaded]);

  // useEffect set data - backup original values và set form
  useEffect(() => {
    // CRITICAL: Reset isDataLoaded FIRST to prevent race conditions
    // when switching records while offcanvas is open.
    // This ensures dependent useEffects (that check isDataLoaded) don't run
    // until ALL form values are properly set.
    setIsDataLoaded(false);

    if (data) {
      // Transform API data thành form data
      const formData = transformApiDataForForm(data);

      // Backup original values từ API
      setOriginalValues({
        api_url: data.api_url || '',
        is_active: data.is_active,
        http_method: data.http_method || 'GET',
        api_params: formData.api_params,
        body_params: formData.body_params,
        expected_response: formData.expected_response,
      });

      setValue('menu_id', data?.menu_id);
      setValue('tab_id', data.tab_id);
      setValue('name', data.name);
      setValue(
        'group',
        data.group_id
          ? {
              value: data.group_id,
              label: data.group__name,
            }
          : null,
      );
      setValue('is_active', data.is_active);
      setValue('api_url', data.api_url);
      setValue('api_params', formData.api_params);
      setValue('body_params', formData.body_params);
      setValue('expected_response', formData.expected_response);
      setValue('http_method', data.http_method || 'GET');
      setValue('receive_data', data.receive_data);
      setValue('send_data', data.send_data);
      setValue('retry_count', 0);
      setValue('timeout_seconds', 0);
      setValue('description', '');
      setValue('notes', '');

      // Sync isActive state directly to prevent timing issues
      // This ensures UI renders correctly even before useEffect chain completes
      setIsActive(data.is_active);

      // Set flag INSIDE setTimeout to ensure all setValue calls have propagated
      // before dependent useEffects (that check isDataLoaded) run
      setTimeout(() => {
        setIsDataLoaded(true);
        clearErrors();
        trigger();
      }, 100);
    }
  }, [data, setValue, clearErrors, trigger]);

  const formatGroupName = (groupName: string) => {
    return groupName
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getSupportedApis = () => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.getSupportedApis, {
        params: {
          search_term: search || '',
          page_number: page ?? 1,
          page_size: 10,
        },
      });

      const options = Object.entries(response.data).map(
        ([groupName, apis]) => ({
          label: formatGroupName(groupName),
          options: (apis as any[]).map((api) => ({
            ...api,
            label:
              import.meta.env.VITE_API_URL?.at(-1) === '/'
                ? `${import.meta.env.VITE_API_URL.slice(0, -1)}${api.url}`
                : `${import.meta.env.VITE_API_URL}${api.url}`,
            value:
              import.meta.env.VITE_API_URL?.at(-1) === '/'
                ? `${import.meta.env.VITE_API_URL.slice(0, -1)}${api.url}`
                : `${import.meta.env.VITE_API_URL}${api.url}`,
          })),
        }),
      );

      return {
        options,
        hasMore: false,
      };
    };
  };

  const onSubmit = async (formData: FormDataProps) => {
    try {
      console.log('Form data (before transform)', formData);

      // Transform form data thành API data
      const transformedData = transformFormDataForSubmit(formData);

      if (!transformedData.is_active) {
        transformedData.http_method = 'POST';
      }

      switch (transformedData.http_method) {
        case 'GET':
          break;
        case 'POST':
          transformedData.api_params = {};
          break;
        case 'PUT':
          break;
        case 'PATCH':
          break;
        case 'DELETE':
          break;
        default:
          break;
      }
      console.log('API data (after transform)', transformedData);
      const response = await API.put(
        endpoint.operationSettingById(data?.id),
        transformedData,
      );
      if (response?.success) {
        if (response?.message) {
          ToastTopHelper.success(response?.message);
        }
        onClose();
        refreshData && refreshData();
        reset();
      }
    } catch (error: any) {
      error?.response?.data?.detail.map((err: any, index: number) => {
        return ToastTopHelper.error(err?.msg);
      });
    }
  };

  return (
    <OffCanvas
      show={open}
      title={t('Edit')}
      onHide={() => {
        onClose();
        reset();
      }}
      id="operation-setting"
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        }}
      >
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit(onSubmit)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
            }}
          >
            {/* Scrollable content */}
            <Box
              sx={{
                flex: 1,
                overflow: 'scroll',
                maxHeight: 'calc(100vh - 45px - 60px - 1rem)',
                display: 'flex',
                flexDirection: 'column',
                px: '1rem',
                gap: '1rem',
              }}
            >
              <CustomRadio
                name="is_active"
                control={control}
                options={[
                  { value: true, label: t('Yes') },
                  { value: false, label: t('No') },
                ]}
                label={t('Is Active')}
                row
                required
                customOnChange={handleIsActiveChange}
              />

              {isRoleSuperuser && (
                <PaginationSelect
                  required
                  label={t('Group')}
                  name="group"
                  control={
                    control as unknown as Control<Record<string, unknown>>
                  }
                  disabled={data?.group_id}
                  loadOptions={getOptionsByModel({
                    name_modal: 'usergroup',
                    search_field: 'name',
                    key: 'name',
                    value: 'id',
                  })}
                  placeholder={t('Select')}
                />
              )}
              {isActive ? (
                <>
                  <CustomInputHookForm
                    name="api_url"
                    control={control}
                    label={t('URL')}
                    placeholder={t('Enter URL')}
                    required
                  />
                  <CustomRadio
                    name="http_method"
                    control={control}
                    options={METHODS_OPTIONS as any}
                    label={t('Method')}
                    row
                    required
                  />
                  {displayFollowMethod(watch('http_method'))}
                </>
              ) : (
                <PaginationSelect
                  required
                  label={t('URL')}
                  name="api_url"
                  control={control}
                  loadOptions={getSupportedApis()}
                  placeholder={t('Select')}
                  onChange={(selectedOption) => {
                    if (selectedOption && !Array.isArray(selectedOption)) {
                      setValue('api_url', selectedOption.value);
                    } else {
                      setValue('api_url', '');
                    }
                    setTimeout(() => {
                      trigger('api_url');
                    }, 50);
                  }}
                  value={
                    watch('api_url')
                      ? {
                          value: watch('api_url'),
                          label: watch('api_url'),
                        }
                      : null
                  }
                />
              )}
            </Box>

            {/* Footer always visible */}
            <Box
              sx={{
                mt: '1rem',
                p: '1rem',
                borderTop:
                  theme === 'dark' ? '1px solid #444646' : '1px solid #E0E0E0',
                background: theme === 'dark' ? '#212529' : '#fff',
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '16px',
                }}
              >
                <CustomBtn
                  label={t('Save')}
                  actionType={ROLE_PERMISSION.UPDATE}
                  type="submit"
                  variant="contained"
                  color="primary"
                  size="lg"
                  loading={isSubmitting}
                  disabled={!isDirty || !isValid || isSubmitting}
                />
                <CustomBtn
                  label={t('Cancel')}
                  type="button"
                  onClick={() => {
                    onClose();
                    reset();
                  }}
                  variant="outline"
                  color="secondary"
                  size="lg"
                />
              </Box>
            </Box>
          </form>
        </FormProvider>
      </Box>
    </OffCanvas>
  );
});
