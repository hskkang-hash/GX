import { styled } from '@mui/material/styles';
import React, { useEffect, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, FormBlock, ToastTopHelper } from 'rj-core';
import CustomCheckBox from '@/components/Form/CustomCheckBox';
import CustomFileInput from '@/components/Form/CustomFileInput';
import CustomSearchMapUnified from '@/components/search/CustomSearchMapUnified';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useDebounce } from '@/utils/utils';

import { Map } from '../../../components/maps';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { Marker } from '../types/IDeliveryHubs';
import OperatingTimeSection from '@/components/OperatingTimeSection';
import { OperatingTimeData } from '@/components/HelperCellOperatingTime';

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

const FormRegister = ({ editMode,
  setOperatingTimes,
  setOperatingTimeErrors,
  operatingTimes,
  operatingTimeErrors }:
  { editMode: boolean, setOperatingTimes: (operatingTimes: OperatingTimeData[]) => void, setOperatingTimeErrors: (operatingTimeErrors: any) => void, operatingTimes: OperatingTimeData[], operatingTimeErrors: any }) => {
  const { t } = useTranslation();
  const {
    control,
    watch,
    setValue,
    trigger,
    formState: { errors },
    clearErrors,
  } = useFormContext();
  console.log('form_hub_errors', errors);
  console.log('form_hub_watch', watch());
  const {
    getOptionsByModel,
    getAddressByLatLongSafe,
    fetchAddressDetail,
    getFunctionTypes,
  } = useCommonAPI();
  const [markerData, setMarkerData] = useState<Marker[]>([]);
  const latitude = watch('latitude');
  const longitude = watch('longitude');
  const [initialDockingStationValue, setInitialDockingStationValue] = useState<
    boolean | null
  >(null);
  const addressType = watch('address_type');
  const [isManualLatLng, setIsManualLatLng] = useState(false);
  // Apply debounce to form values
  const debouncedLatitude = useDebounce(latitude, 800);
  const debouncedLongitude = useDebounce(longitude, 800);
  const [latManual, setLatManual] = useState(null);
  const [longManual, setLongManual] = useState(null);

  const isRoleSuperuser = CheckRoleAccount('superuser');

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
      (debouncedLatitude &&
        debouncedLongitude &&
        (editMode ? isManualLatLng : true)) ||
      (debouncedLatitude && debouncedLongitude)
    ) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }
  }, [debouncedLatitude, debouncedLongitude, addressType, isManualLatLng]);

  useEffect(() => {
    const getTerminalCodeIdForFunction = async () => {
      try {
        const loadOptions = getOptionsByModel({
          name_modal: 'terminalType',
        });
        const result = await loadOptions('', [], { page: 1 });
        setValue('terminal_type_ids', [
          result.options.find((item: any) => item.code === 'DELIVERY_HUB'),
        ]);
        setValue('terminal_type_ids_docking', [
          result.options.find((item: any) => item.code === 'DOCKING_STATION'),
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

  const isEditMode =
    watch('temp_function_ids') && watch('temp_function_ids').length > 0;

  useEffect(() => {
    if (isEditMode && initialDockingStationValue === null) {
      setInitialDockingStationValue(watch('is_docking_station') || false);
    }
  }, [isEditMode, initialDockingStationValue]);

  console.log('errror', errors);

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


  return (
    <>
      <div className="form-grid"
        style={{
          gridTemplateColumns: '3fr 2fr',
        }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }} >
          <FormBlock>
            <div className="form-grid">
              {isRoleSuperuser ? (
                <>
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
                  <CustomInputHookForm
                    required
                    name="code"
                    label={t('ID')}
                    placeholder={t('ID')}
                  />
                </>
              ) : (
                <GridFullWidth>
                  <CustomInputHookForm
                    required
                    name="code"
                    label={t('ID')}
                    placeholder={t('ID')}
                  />
                </GridFullWidth>
              )}

              <GridFullWidth style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <CustomInputHookForm
                    required
                    name="name"
                    label={t('hubs_delivery.name')}
                    placeholder={t('hubs_delivery.name')}
                  />
                </div>
                <CustomCheckBox
                  name="is_docking_station"
                  control={control}
                  label={t('Is Docking')}
                  subLabel={t('Yes')}
                />
              </GridFullWidth>
              <PaginationSelect
                label={t('Type')}
                required
                name="function_ids"
                control={control}
                disabled={!watch('terminal_type_ids')}
                loadOptions={getFunctionTypes({
                  function_type: terminalCodeForFunction,
                })}
                placeholder={t('Select')}
              />
              <CustomInputHookForm
                name="manager"
                label={t('hubs_delivery.manager')}
                placeholder={t('hubs_delivery.manager')}
              />
              <GridFullWidth>
                <GridOneThree>
                  <div>
                    <CustomInputHookForm
                      name="postal_code"
                      label={t('hubs_delivery.postal_code')}
                      disabled
                    />
                  </div>
                  <div>
                    <CustomSearchMapUnified
                      label={t('hubs_delivery.address')}
                      isRequired
                      value={watch('address')}
                      style={{ gridColumn: 'span 2' }}
                      onSelect={(value, option) => {
                        setIsManualLatLng(false);
                        console.log('123', option);
                        setValue('latitude', option.lat, { shouldDirty: true });
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
                          setValue('address', value, { shouldDirty: true });
                          trigger('address');
                        }

                        if (option.zonecode) {
                          setValue('postal_code', option.zonecode, {
                            shouldDirty: true,
                          });
                        }
                      }}
                      onClear={() => {
                        setIsManualLatLng(false);
                        setValue('address', '', { shouldDirty: true });
                        setValue('latitude', null, { shouldDirty: true });
                        setValue('longitude', null, { shouldDirty: true });
                        setValue('postal_code', '', { shouldDirty: true });
                        setValue('city_province', null, { shouldDirty: true });
                        setValue('city_county_district', null, {
                          shouldDirty: true,
                        });
                        setValue('ward_town_township', null, {
                          shouldDirty: true,
                        });
                        setValue('street_address', null, { shouldDirty: true });
                        // trigger('address');
                        setMarkerData([]);
                      }}
                      placeholder={t('hubs_delivery.address')}
                      onError={errors.address?.message as string}
                    />
                  </div>
                </GridOneThree>
              </GridFullWidth>
              <GridFullWidth>
                <CustomInputHookForm
                  name="address_note"
                  label={t('hubs_delivery.address_note')}
                  placeholder={t('hubs_delivery.address_note')}
                />
              </GridFullWidth>

              <CustomInputHookForm
                disabled={!editMode}
                name="latitude"
                required
                label={t('hubs_delivery.latitude')}
                onChange={(e) => {
                  setIsManualLatLng(true);
                  setValue('latitude', e.target.value, { shouldDirty: true });
                  trigger('latitude');
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
                disabled={!editMode}
                name="longitude"
                required
                label={t('hubs_delivery.longitude')}
                onChange={(e) => {
                  setIsManualLatLng(true);
                  setValue('longitude', e.target.value, { shouldDirty: true });
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
              />
              <CustomInputHookForm
                name="url"
                label={t('URL')}
                placeholder={t('URL')}
              />
              <CustomInputHookForm
                name="note"
                label={t('hubs_delivery.remarks')}
                placeholder={t('hubs_delivery.remarks')}
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
            label={t('hubs_delivery.image')}
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
    </>
  );
};

export default React.memo(FormRegister);
