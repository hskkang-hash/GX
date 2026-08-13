import { yupResolver } from '@hookform/resolvers/yup';
import { styled } from '@mui/material';
import { useEffect, useState } from 'react';
import context from 'react-bootstrap/esm/AccordionContext';
import { FormProvider, useForm, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useConfigGroupSystem,
} from 'rj-core';

// import "./FormTerminals.scss";
import CustomDatePicker from '@/components/Form/CustomDatePicker';
import CustomFileInput from '@/components/Form/CustomFileInput';
import { Tabs } from '@/components/Form/Tabs';
import UnitInput from '@/components/Form/UnitInput';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaDockingStation } from '@/services/schemaForm';
import { useDebounce } from '@/utils/utils';

import CustomSearchMapUnified from '../../../components/search/CustomSearchMapUnified';
import { checkCodeValid } from '../../../utils/CheckCodeValid';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import OperatingTimeSection from '@/components/OperatingTimeSection';
import { OperatingTimeData } from '@/features/terminals/components/HelperCell';

export const GridFullWidth = styled('div')`
  grid-column: 1 / -1;
  & > div {
    margin-bottom: 0 !important;
  }
`;

export const GridOneThree = styled('div')`
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 1rem;
  width: 100%;
  & > div > div {
    margin-bottom: 0 !important;
  }
`;

interface IpropInformation {
  isEdit?: boolean;
  setIsDirtyEdit?: (isDirtyEdit: boolean) => void;
  operatingTimes: OperatingTimeData[];
  setOperatingTimes: (operatingTimes: OperatingTimeData[]) => void;
  operatingTimeErrors: any;
  setOperatingTimeErrors: (operatingTimeErrors: any) => void;
}

const Information = ({
  isEdit,
  setIsDirtyEdit = () => { },
  operatingTimes,
  setOperatingTimes,
  operatingTimeErrors,
  setOperatingTimeErrors,
}: IpropInformation) => {
  const { t } = useTranslation();
  const { getOptionsByModel, getFunctionTypes } = useCommonAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const {
    control,
    watch,
    setValue,
    trigger,
    formState: { errors },
  } = useFormContext();

  const terminalCodeForFunction =
    watch('terminal_type_ids')
      ?.filter((item: any) => item.code === 'DOCKING_STATION')
      .map((item: any) => item.code)
      .join()
      .toLowerCase() || '';

  const { getAddressByLatLongSafe, fetchAddressDetail } = useCommonAPI();

  // Watch form values
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  // Apply debounce to form values
  const debouncedLatitude = useDebounce(latitude, 800);
  const debouncedLongitude = useDebounce(longitude, 800);
  const [isManualLatLng, setIsManualLatLng] = useState(false);
  const [latManual, setLatManual] = useState(null);
  const [longManual, setLongManual] = useState(null);
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);
  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    try {
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
    } catch (error) {
      console.error('Error fetching address by lat/long:', error);
      // Just set the marker without address details
      setMarkerData([
        {
          lat: lat,
          lng: long,
        },
      ]);
    }
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

  useEffect(() => {
    const getTerminalCodeIdForFunction = async () => {
      try {
        const loadOptions = getOptionsByModel({
          name_modal: 'terminalType',
        });
        const result = await loadOptions('', [], { page: 1 });
        setValue('terminal_type_ids', [
          result.options.find((item: any) => item.code === 'DOCKING_STATION'),
        ]);
      } catch (error) {
        console.error('Failed to fetch options:', error);
      }
    };
    getTerminalCodeIdForFunction();
  }, []);

  return (
    <div
      className="form-grid"
      style={{
        gridTemplateColumns: '3fr 2fr',
      }}
    >
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
            <CustomInputHookForm
              required
              name="name"
              label={t('Name')}
              placeholder={t('Name')}
            />
            <UnitInput
              name="time_stops.value"
              label={t('docking_station.waiting_time')}
              placeholder="0"
              unit={watch('time_stops.unit')}
              type="number"
              isRequired
            />
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
              name="manager_name"
              label={t('docking_station.manager')}
              placeholder={t('docking_station.manager')}
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
                    key="address-search"
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
                        setValue('full_address', value, { shouldDirty: true });
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
                      setValue('city_province', null, { shouldDirty: true });
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
              disabled={!isEdit}
              name="latitude"
              label={t('Latitude')}
              type="decimal"
              required
              onChange={(e) => {
                setIsDirtyEdit(true);
                setIsManualLatLng(true); // Reset when manually changing coordinates
                setValue('latitude', e.target.value, {
                  shouldDirty: true,
                });
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
            // disabled
            />
            <CustomInputHookForm
              disabled={!isEdit}
              name="longitude"
              label={t('Longitude')}
              required
              type="decimal"
              onChange={(e) => {
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
            // disabled
            />
            <CustomInputHookForm
              // required
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
          control={control}
          errors={errors}
          watch={watch}
          trigger={trigger}
          setValue={setValue}
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
  );
};

export default Information;
