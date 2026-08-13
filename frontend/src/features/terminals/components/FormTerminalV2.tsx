import { yupResolver } from '@hookform/resolvers/yup';
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
  useTheme,
  useUserInfo,
} from 'rj-core';

import CustomDatePicker from '@/components/Form/CustomDatePicker';
import CustomFileInput from '@/components/Form/CustomFileInput';
import UnitInput from '@/components/Form/UnitInput';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import CustomSearchMapUnified from '@/components/search/CustomSearchMapUnified';
import PaginationSelect from '@/components/selects/PaginationSelect';
import {
  GridFullWidth,
  GridOneThree,
} from '@/features/dockingStation/components/FormDockingStation';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaTerminal } from '@/services/schemaForm';
import { useDebounce } from '@/utils/utils';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { formatKoreanStreetAddress } from '../hooks/utils';
import useAPI from '../useAPI/useAPI';
import type { FormData, FormTerminalsProps } from './FormTerminalV2.d';
import { useConfigSystem } from 'rj-core';
import OperatingTimeSection from '@/components/OperatingTimeSection';
import { OperatingTimeData } from '@/components/HelperCellOperatingTime';


const FormTerminalsV2 = ({
  initialData,
  onSubmit,
  loading,
  onCancel,
  breadcrumbItems,
  isDirtyEdit = true,
  editMode = false,
  setIsDirtyEdit = () => { },
}: FormTerminalsProps) => {
  const { t, i18n } = useTranslation();
  const { getListGroup } = useAPI();
  const {
    getAddressByLatLongSafe,
    fetchAddressDetail,
    getOptionsByModel,
    getFunctionTypes,
  } = useCommonAPI();
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);
  const [isManualLatLng, setIsManualLatLng] = useState(false);
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [theme] = useTheme();
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? 'YYYY/MM/DD';

  const [latManual, setLatManual] = useState(null);
  const [longManual, setLongManual] = useState(null);

  const defaultFormValues: FormData = {
    code: '',
    name: '',
    time_stops: {
      value: null,
      unit: 'mins',
    },
    address_type: 'geographic_coordinates',
    latitude: null,
    longitude: null,
    city_province: null,
    city_county_district: null,
    ward_town_township: null,
    street_address: '',
    full_address: '',
    postal_code: '',
    manufacturer: '',
    year_of_manufacture: '',
    url: '',
    note: '',
    manager_name: '',
    terminal_type_ids: [],
    function_ids: [],
    delete_avatar: false,
    terminal_purpose_id: null,
    purpose_type_id: null,
    exceptions: [],
    ...(isRoleSuperuser && { group: null }),
  };

  const resolver = useMemo(
    () => yupResolver(schemaTerminal(t, isRoleSuperuser)) as any,
    [t, isRoleSuperuser],
  );

  const methods = useForm<FormData>({
    defaultValues: initialData || defaultFormValues,
    resolver,
    mode: 'onChange',
  });

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
  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
  }, [initialData, reset]);

  console.log('errors_in_terminal', errors);
  console.log('watch_in_terminal', watch());




  const onError = () => {
    ToastTopHelper.error(t('Please fill in all required fields'));
  };

  // Watch form values
  const addressType = watch('address_type');
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
    setValue('city_province', data?.region_1depth_name || null);
    setValue('city_county_district', data?.region_2depth_name || null);
    setValue('ward_town_township', data?.region_3depth_name || null);
    setValue('street_address', formatKoreanStreetAddress(data || {}));
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
      (addressType === 'geographic_coordinates' &&
        debouncedLatitude &&
        debouncedLongitude &&
        (editMode ? isManualLatLng : true)) ||
      (addressType === 'geographic_coordinates' &&
        debouncedLatitude &&
        debouncedLongitude)
    ) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }
  }, [debouncedLatitude, debouncedLongitude, addressType, isManualLatLng]);

  const [operatingTimes, setOperatingTimes] = useState<OperatingTimeData[]>([]);
  const [operatingTimeErrors, setOperatingTimeErrors] = useState<any>({});

  const isOperatingTimesEdited = useMemo(() => {
    return JSON.stringify(operatingTimes) !==
      JSON.stringify(initialData?.operating_times);
  }, [operatingTimes, initialData?.operating_times]);

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && (isDirty || isOperatingTimesEdited),
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
  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    const formData = {
      ...data,
      operating_times: operatingTimes,
    }
    try {
      await onSubmit(formData);
      reset(formData, {
        keepDirty: false,
        keepValues: true,
      });
      // navigate(CustomRoutes.terminals.path);
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };

  const chooseInfrastructure = watch('terminal_type_ids')?.find(
    (item: any) => item.code === 'INFRASTRUCTURE',
  );
  useEffect(() => {
    if (!chooseInfrastructure) {
      setValue('terminal_purpose_id', null);
      setValue('purpose_type_id', null);
    }
  }, [chooseInfrastructure]);

  console.log('watch_form', watch());

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
    if (!editMode) {
      fetchDayOfWeek()
    }
  }, [editMode]);

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
              actionType={ROLE_PERMISSION.UPDATE}
              style={{ width: '6rem' }}
              disabled={
                !watch('full_address') ||
                !(watch('function_ids') && watch('function_ids')?.length > 0) ||
                (isRoleSuperuser && !watch('group')?.value) ||
                (chooseInfrastructure &&
                  !watch('terminal_purpose_id')?.value) ||
                (chooseInfrastructure && !watch('purpose_type_id')?.value) ||
                !isValid ||
                (!isDirty && !isOperatingTimesEdited) ||
                loading ||
                isSubmitting ||
                Object.keys(operatingTimeErrors).length > 0
              }
              label={t('Save')}
              loading={isSubmitting || loading}
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
                        loadOptions={getListGroup() as any}
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
                    label={t('Type')}
                    name="terminal_type_ids"
                    control={control}
                    disabled={isRoleSuperuser ? !watch('group')?.value : false}
                    isMulti
                    loadOptions={
                      getOptionsByModel({
                        name_modal: 'terminalType',
                        search_field: 'name',
                        key: 'name',
                        value: 'id',
                        code: 'code',
                      }) as any
                    }
                    onChange={(value) => {
                      setValue('function_ids', null);
                    }}
                    placeholder={t('Select')}
                  />
                  <PaginationSelect
                    key={
                      watch('terminal_type_ids')
                        ?.map((item) => item?.code)
                        .join()
                        .toLowerCase() || 'no-type'
                    }
                    required
                    label={t('Function')}
                    name="function_ids"
                    control={control}
                    isMulti
                    disabled={watch('terminal_type_ids')?.length === 0}
                    loadOptions={
                      getFunctionTypes({
                        function_type:
                          watch('terminal_type_ids')
                            ?.map((item) => item.code)
                            .join()
                            .toLowerCase() || '',
                      }) as any
                    }
                    placeholder={t('Select')}
                  />
                  {chooseInfrastructure && (
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
                  )}
                  {chooseInfrastructure && (
                    <PaginationSelect
                      required
                      label={t('Purpose')}
                      name="purpose_type_id"
                      control={control}
                      loadOptions={getOptionsByModel({
                        name_modal: 'purposeType',
                        search_field: 'name',
                      })}
                      placeholder={t('Select')}
                    />
                  )}
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
                            setIsManualLatLng(false);
                            setValue('latitude', option.lat, {
                              shouldDirty: true,
                            });
                            setValue('longitude', option.lng, {
                              shouldDirty: true,
                            });
                            setValue('city_province', option.province, {
                              shouldDirty: true,
                            });
                            setValue('city_county_district', option.district, {
                              shouldDirty: true,
                            });
                            setValue('ward_town_township', option.township, {
                              shouldDirty: true,
                            });
                            setValue(
                              'street_address',
                              option?.street_address
                                ? option?.street_address
                                : formatKoreanStreetAddress(option),
                              {
                                shouldDirty: true,
                              },
                            );
                            if (value) {
                              setValue('full_address', value, {
                                shouldDirty: true,
                              });
                              trigger('full_address');
                            }

                            if (option.zonecode) {
                              setValue('postal_code', option.zonecode, {
                                shouldDirty: true,
                              });
                            }
                          }}
                          onClear={() => {
                            setIsManualLatLng(false);
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
                            setValue('street_address', '', { shouldDirty: true });
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
                    name="latitude"
                    label={t('Latitude')}
                    type="decimal"
                    required
                    onChange={(e) => {
                      setIsDirtyEdit(true);
                      setIsManualLatLng(true);
                      setValue('latitude', e.target.value, { shouldDirty: true });
                      trigger('latitude');
                      setLatManual(e.target.value);
                      if (watch('latitude')) {
                        clearErrors('latitude');
                      }
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
                    disabled={!editMode}
                  />
                  <CustomInputHookForm
                    name="longitude"
                    label={t('Longitude')}
                    type="decimal"
                    required
                    onChange={(e) => {
                      console.log('e.target.value', e.target.value);
                      setIsDirtyEdit(true);
                      setIsManualLatLng(true);
                      setValue('longitude', e.target.value, {
                        shouldDirty: true,
                      });
                      trigger('longitude');
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
                    disabled={!editMode}
                  />
                  <UnitInput
                    name="time_stops.value"
                    label={t('Waiting Time')}
                    placeholder="0"
                    unit={watch('time_stops.unit')}
                    type="number"
                    isRequired
                  />
                  <CustomInputHookForm
                    name="manager_name"
                    label={t('Manager')}
                    placeholder={t('Manager')}
                  />
                  <CustomInputHookForm
                    name="manufacturer"
                    label={t('Manufacturer')}
                    placeholder={t('Manufacturer')}
                  />
                  <CustomDatePicker
                    label={t('Year of Manufacture')}
                    placeholder=""
                    name="year_of_manufacture"
                    control={control}
                    format="YYYY"
                    picker="year"
                  />
                  <CustomInputHookForm
                    name="url"
                    label={t('URL')}
                    placeholder={t('URL')}
                  />
                  <CustomInputHookForm
                    name="note"
                    label={t('Remarks')}
                    placeholder={t('Remarks')}
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
            <div
              className="form-grid"
              style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
            >
              <CustomFileInput
                name="avatar"
                control={control}
                label={t('docking_station.image')}
                onFileRemove={() => {
                  setValue('avatar', null);
                  setValue('delete_avatar', true);
                }}
                fullWidthPreview={true}
                showNoImage={true}
              />
              <Map
                operatingMarkers={markerData.length > 0 ? markerData : []}
                polylines={markerData.length > 0 ? [markerData] : []}
                // bounds={mapBounds || undefined}
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
              actionType={ROLE_PERMISSION.UPDATE}
              onClick={handleModalSave}
              label={t('Save')}
              disabled={isSubmitting || loading}
              loading={isSubmitting}
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
