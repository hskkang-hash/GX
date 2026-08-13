import { yupResolver } from '@hookform/resolvers/yup';
import { styled } from '@mui/material/styles';
import { useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
} from 'rj-core';

// import "./FormTerminals.scss";
import CustomDatePicker from '@/components/Form/CustomDatePicker';
import CustomFileInput from '@/components/Form/CustomFileInput';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import CustomSearchMapUnified from '@/components/search/CustomSearchMapUnified';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaInfrastructure } from '@/services/schemaForm';
import { useDebounce } from '@/utils/utils';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import OperatingTimeSection from '@/components/OperatingTimeSection';
import { ExceptionData, OperatingTimeData } from '@/components/HelperCellOperatingTime';

const GridFullWidth = styled('div')`
  grid-column: 1 / -1;
  & > div {
    margin-bottom: 0 !important;
  }
`;

const GridOneThree = styled('div')`
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 1rem;
  width: 100%;
  & > div > div {
    margin-bottom: 0 !important;
  }
`;

// Define types for form data and select options
interface SelectOption {
  value: string;
  label: string;
}

export interface FormData {
  group: SelectOption | null;
  name: string;
  terminal_type_id: SelectOption | null;
  terminal_purpose_id: SelectOption | null;
  infrastructure_type_id: SelectOption | null;
  manufacturer: string | null;
  year_of_manufacture: number | null;
  latitude: number | null;
  longitude: number | null;
  street_address: string;
  full_address: string;
  city_province: string | null;
  city_county_district: string | null;
  ward_town_township: string | null;
  postal_code: string;
  purpose_type_id: SelectOption | null;
  manager_name: string | null;
  url: string | null;
  address_note: string;
  note: string;
  avatar: any | null;
  delete_avatar: boolean;
  terminal_type_ids: SelectOption[] | null;
  function_ids: any;
  code: any;
  exceptions?: ExceptionData[];
  operating_times?: OperatingTimeData[];
}

interface FormTerminalsProps {
  initialData?: FormData;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  title?: string;
  breadcrumbItems?: { url?: string; text?: string }[];
  isDirtyEdit?: boolean;
  setIsDirtyEdit?: (isDirtyEdit: boolean) => void;
  isEdit?: boolean;
}

const FormTerminalsV2 = ({
  initialData,
  onSubmit,
  loading,
  onCancel,
  breadcrumbItems,
  isDirtyEdit = true,
  setIsDirtyEdit = () => { },
  isEdit = false,
}: FormTerminalsProps) => {
  const { getOptionsByModel, getFunctionTypes } = useCommonAPI();
  const { t } = useTranslation();
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);
  const [isManualLatLng, setIsManualLatLng] = useState(false);
  const [latManual, setLatManual] = useState(null);
  const [longManual, setLongManual] = useState(null);
  const isRoleSuperuser = CheckRoleAccount('superuser');

  const [operatingTimes, setOperatingTimes] = useState<OperatingTimeData[]>([]);
  const [operatingTimeErrors, setOperatingTimeErrors] = useState<any>({});

  const isOperatingTimesEdited = useMemo(() => {
    return JSON.stringify(operatingTimes) !==
      JSON.stringify(initialData?.operating_times);
  }, [operatingTimes, initialData?.operating_times]);

  const defaultFormValues: FormData = {
    name: '',
    terminal_type_id: null,
    terminal_purpose_id: null,
    infrastructure_type_id: null,
    latitude: null,
    longitude: null,
    city_province: null,
    city_county_district: null,
    ward_town_township: null,
    street_address: '',
    full_address: '',
    note: '',
    postal_code: '',
    address_note: '',
    manufacturer: null,
    year_of_manufacture: null,
    purpose_type_id: null,
    manager_name: null,
    url: null,
    avatar: null,
    delete_avatar: false,
    terminal_type_ids: null,
    function_ids: null,
    code: '',
    group: null,
  };

  const methods = useForm<FormData>({
    defaultValues: initialData || defaultFormValues,
    resolver: yupResolver(schemaInfrastructure(t, isRoleSuperuser)) as any,
  });

  const { getAddressByLatLongSafe, fetchAddressDetail } = useCommonAPI();
  const {
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    clearErrors,
    formState: { isValid, errors, isDirty, isSubmitting },
    trigger,
  } = methods;

  console.log('form_infrastructure_errors', errors);
  console.log('form_infrastructure_watch', watch());

  // Reset form when initialData changes
  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
  }, [initialData, reset]);

  const onError = () => {
    console.log('onError', methods.formState.errors);

    ToastTopHelper.error(t('Please fill in all required fields'));
  };

  // Watch form values
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  // Apply debounce to form values
  const debouncedLatitude = useDebounce(latitude, 800);
  const debouncedLongitude = useDebounce(longitude, 800);

  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    const { data, status } = await getAddressByLatLongSafe(lat, long);
    if (!status) {
      setMarkerData([
        {
          lat: lat,
          lng: long,
        },
      ]);
      return;
    }

    // Get zone code from address search
    const addressDetail = await fetchAddressDetail(data?.address_name || '');

    setValue('full_address', data?.address_name || '');
    setValue('city_province', data?.region_1depth_name || '');
    setValue('city_county_district', data?.region_2depth_name || '');
    setValue('ward_town_township', data?.region_3depth_name || '');
    setValue('street_address', formatKoreanStreetAddress(data || {}));
    setValue('postal_code', addressDetail?.zonecode || '');
    if (latManual || longManual) {
      null;
    } else {
      setValue('postal_code', addressDetail?.zonecode || '');
    }
    setMarkerData([
      {
        lat: lat,
        lng: long,
      },
    ]);
  };
  useEffect(() => {
    if (
      (debouncedLatitude &&
        debouncedLongitude &&
        (isEdit ? isManualLatLng : true)) ||
      (debouncedLatitude && debouncedLongitude)
    ) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }
  }, [debouncedLatitude, debouncedLongitude, isManualLatLng]);

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && (isDirty || isOperatingTimesEdited),
      onSave: async () => {
        const formData = watch();
        const formDataSubmit = {
          ...formData,
          operating_times: operatingTimes,
        };
        await onSubmit(formDataSubmit);
        reset(formDataSubmit, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    try {
      const formDataSubmit = {
        ...data,
        operating_times: operatingTimes,
      };
      await onSubmit(formDataSubmit);
      reset(data, {
        keepDirty: false,
        keepValues: true,
      });
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };

  useEffect(() => {
    const getTerminalCodeIdForFunction = async () => {
      try {
        const loadOptions = getOptionsByModel({
          name_modal: 'terminalType',
        });
        const result = await loadOptions('', [], { page: 1 });
        setValue('terminal_type_ids', [
          result.options.find((item: any) => item.code === 'INFRASTRUCTURE'),
        ]);
      } catch (error) {
        console.error('Failed to fetch options:', error);
      }
    };
    getTerminalCodeIdForFunction();
  }, []);
  const terminalCodeForFunction =
    watch('terminal_type_ids')
      ?.map((item: any) => item.code)
      .join()
      .toLowerCase() || '';

  useEffect(() => {
    if (watch('latitude')) {
      clearErrors('latitude');
    }
    if (watch('longitude')) {
      clearErrors('longitude');
    }
  }, [watch('latitude'), watch('longitude')]); // eslint-disable-line react-hooks/exhaustive-deps

  const { getDayOfWeek } = useCommonAPI();
  useEffect(() => {
    const fetchDayOfWeek = async () => {
      const { data, status, message } = await getDayOfWeek();
      console.log('data_day_of_week', data);
      if (status) {
        setOperatingTimes(data);
      } else {
        ToastTopHelper.error(message);
      }
    }
    if (!isEdit) {
      fetchDayOfWeek()
    }
  }, [isEdit]);

  useEffect(() => {
    if (initialData?.operating_times) {
      setOperatingTimes(initialData?.operating_times as OperatingTimeData[]);
    }
  }, [initialData?.operating_times]);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        className="form-add-new-terminals"
      >
        <CustomBreadcrumb
          items={breadcrumbItems}
          buttons={[
            <CustomBtn
              key="cancel-btn"
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={onCancel}
            />,
            <CustomBtn
              key="save-btn"
              size="md"
              style={{ width: '6rem' }}
              actionType={
                isEdit ? ROLE_PERMISSION.UPDATE : ROLE_PERMISSION.CREATE
              }
              disabled={
                isSubmitting || !isValid || !watch('full_address') ||
                (!isDirty && !isOperatingTimesEdited) ||
                Object.keys(operatingTimeErrors).length > 0
              }
              loading={isSubmitting || loading}
              label={t('Save')}
              type="submit"
            />,
          ]}
        />
        <Main>
          <div
            className="form-grid"
            style={{
              gridTemplateColumns: '3fr 2fr',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }} >
              <FormBlock>
                <div className="form-grid">
                  {isRoleSuperuser && (
                    <GridFullWidth>
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
                    </GridFullWidth>
                  )}
                  <CustomInputHookForm
                    required
                    name="code"
                    label={t('ID')}
                    placeholder={t('ID')}
                  />
                  <CustomInputHookForm
                    required
                    name="name"
                    label={t('Name')}
                    placeholder={t('Name')}
                  />
                  <PaginationSelect
                    required
                    label={t('Major Category')}
                    name="terminal_purpose_id"
                    control={control}
                    loadOptions={getOptionsByModel({
                      name_modal: 'TerminalPurpose',
                    })}
                    placeholder={t('Select')}
                  />
                  <PaginationSelect
                    required
                    label={t('Minor Category')}
                    name="function_ids"
                    control={control}
                    disabled={!watch('terminal_type_ids')}
                    loadOptions={getFunctionTypes({
                      function_type: terminalCodeForFunction,
                    })}
                    placeholder={t('Select')}
                  />
                  <CustomInputHookForm
                    name="manufacturer"
                    label={t('infrastructure.manufacturer')}
                    placeholder={t('infrastructure.manufacturer')}
                  />
                  <CustomDatePicker
                    label={t('infrastructure.year_of_manufacture')}
                    placeholder={t('infrastructure.year_of_manufacture')}
                    name="year_of_manufacture"
                    control={control}
                    format="YYYY"
                    picker="year"
                  />
                  <GridFullWidth>
                    <GridOneThree>
                      <div>
                        <CustomInputHookForm
                          name="postal_code"
                          label={t('Postal Code')}
                          type="text"
                          disabled
                        />
                      </div>
                      <div>
                        <CustomSearchMapUnified
                          label={t('Address')}
                          className="grid-span-full"
                          isRequired
                          value={watch('full_address')}
                          onSelect={(value, option) => {
                            setValue('postal_code', option.zonecode);
                            setValue('latitude', option.lat, {
                              shouldDirty: true,
                            });
                            setValue('longitude', option.lng, {
                              shouldDirty: true,
                            });
                            setValue('city_province', option.province);
                            setValue('city_county_district', option.district);
                            setValue('ward_town_township', option.township);
                            setValue(
                              'street_address',
                              option?.street_address
                                ? option?.street_address
                                : formatKoreanStreetAddress(option),
                            );
                            if (value) {
                              setValue('full_address', value, {
                                shouldDirty: true,
                              });
                              trigger('full_address');
                            }
                            setIsDirtyEdit(true);
                            setMarkerData([
                              {
                                lat: option.lat,
                                lng: option.lng,
                              },
                            ]);
                          }}
                          onClear={() => {
                            setValue('full_address', '', { shouldDirty: true });
                            setValue('latitude', null, { shouldDirty: true });
                            setValue('longitude', null, { shouldDirty: true });
                            setValue('city_province', null, {
                              shouldDirty: true,
                            });
                            setValue('city_county_district', null, {
                              shouldDirty: true,
                            });
                            setValue('ward_town_township', null, {
                              shouldDirty: true,
                            });
                            setValue('street_address', '', {
                              shouldDirty: true,
                            });
                            setMarkerData([]);
                          }}
                          onError={errors.full_address?.message}
                        />
                      </div>
                    </GridOneThree>
                  </GridFullWidth>
                  <GridFullWidth>
                    <CustomInputHookForm
                      name="address_note"
                      label={t('Address Detail​')}
                      placeholder={t('Address Detail​')}
                      type="text"
                    />
                  </GridFullWidth>
                  <CustomInputHookForm
                    required
                    disabled={!isEdit}
                    name="latitude"
                    label={t('Latitude')}
                    type="decimal"
                    onChange={(e) => {
                      setIsDirtyEdit(true);
                      setValue('latitude', e.target.value, {
                        shouldDirty: true,
                      });
                      trigger('latitude');
                      setIsManualLatLng(true);
                      setLatManual(e.target.value);
                    }}
                    onKeyDown={(e) => {
                      const allowedKeys = [
                        'Backspace',
                        'Delete',
                        'ArrowLeft',
                        'ArrowRight',
                        'Tab',
                      ];
                      if (e.ctrlKey || e.metaKey) {
                        return;
                      }

                      const value = e.currentTarget.value;
                      const hasDot = value.includes('.');

                      if (
                        (e.key >= '0' && e.key <= '9') ||
                        (e.key === '.' && !hasDot) ||
                        allowedKeys.includes(e.key)
                      ) {
                        return;
                      }

                      e.preventDefault();
                    }}
                  />
                  <CustomInputHookForm
                    required
                    disabled={!isEdit}
                    name="longitude"
                    label={t('Longitude')}
                    type="decimal"
                    onChange={(e) => {
                      setIsDirtyEdit(true);
                      setValue('longitude', e.target.value, {
                        shouldDirty: true,
                      });
                      trigger('longitude');
                      setIsManualLatLng(true);
                      setLongManual(e.target.value);
                    }}
                    onKeyDown={(e) => {
                      const allowedKeys = [
                        'Backspace',
                        'Delete',
                        'ArrowLeft',
                        'ArrowRight',
                        'Tab',
                      ];
                      if (e.ctrlKey || e.metaKey) {
                        return;
                      }

                      const value = e.currentTarget.value;
                      const hasDot = value.includes('.');

                      if (
                        (e.key >= '0' && e.key <= '9') ||
                        (e.key === '.' && !hasDot) ||
                        allowedKeys.includes(e.key)
                      ) {
                        return;
                      }

                      e.preventDefault();
                    }}
                  // disabled
                  />
                  <PaginationSelect
                    required
                    label={t('Purpose_Infra')}
                    name="purpose_type_id"
                    control={control}
                    loadOptions={getOptionsByModel({
                      name_modal: 'purposeType',
                      search_field: 'name',
                    })}
                    placeholder={t('Select')}
                  />
                  <CustomInputHookForm
                    name="manager_name"
                    label={t('infrastructure.manager')}
                    placeholder={t('infrastructure.manager')}
                  />
                  <CustomInputHookForm
                    name="url"
                    label={t('URL')}
                    placeholder={t('URL')}
                  />
                  <CustomInputHookForm
                    name="note"
                    label={t('infrastructure.remarks')}
                    placeholder={t('infrastructure.remarks')}
                  />
                </div>
              </FormBlock>
              <OperatingTimeSection
                operatingTimes={operatingTimes}
                setOperatingTimes={setOperatingTimes}
                operatingTimeErrors={operatingTimeErrors}
                setOperatingTimeErrors={setOperatingTimeErrors}
              />
            </div>
            {/* <MapForRoute markerData={markerData} height="650px" /> */}
            <div
              className="form-grid"
              style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
            >
              <CustomFileInput
                name="avatar"
                control={control}
                label={t('infrastructure.image')}
                onFileRemove={() => {
                  setValue('avatar', null);
                  setValue('delete_avatar', true);
                }}
                fullWidthPreview={true}
                showNoImage={true}
              />
              <Map
                center={
                  markerData.length > 0
                    ? { lat: markerData[0].lat, lng: markerData[0].lng }
                    : undefined
                }
                operatingMarkers={markerData.length > 0 ? markerData : []}
                polylines={markerData.length > 0 ? [markerData] : []}
                style={{ height: 350 }}
              />
            </div>
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
              key="modal-save-btn"
              type="submit"
              color="primary"
              size="lg"
              onClick={handleModalSave}
              label={t('Save')}
              disabled={isSubmitting || loading}
              loading={isSubmitting || loading}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              key="modal-cancel-btn"
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

export default FormTerminalsV2;
