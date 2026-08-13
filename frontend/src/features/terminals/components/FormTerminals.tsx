import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useMemo, useState } from 'react';
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
} from 'rj-core';

// import "./FormTerminals.scss";
import CustomRadio from '@/components/Form/CustomRadio';
import UnitInput from '@/components/Form/UnitInput';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import CustomSelect from '@/components/selects/CustomSelect';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { koreaProvinces } from '@/data/dataMapKorean';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { schemaTerminal } from '@/services/schemaForm';
import { useDebounce } from '@/utils/utils';

// Define types for form data and select options
interface SelectOption {
  value: string;
  label: string;
}

interface FormData {
  code: string;
  name: string;
  terminal_type_id: SelectOption | null;
  time_stops: {
    value: number | null;
    unit: string;
  };
  address_type: 'geographic_coordinates' | 'address';
  latitude: number | null;
  longitude: number | null;
  city_province: SelectOption | null;
  city_county_district: SelectOption | null;
  ward_town_township: SelectOption | null;
  street_address: string;
  note: string;
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
}

const FormTerminals = ({
  initialData,
  onSubmit,
  loading,
  onCancel,
  breadcrumbItems,
  isDirtyEdit = true,
  setIsDirtyEdit = () => {},
}: FormTerminalsProps) => {
  const { getOptionsByModel } = useCommonAPI();
  const { t, i18n } = useTranslation();
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);
  const defaultFormValues: FormData = {
    code: 'T-' + new Date().getTime().toString(),
    name: '',
    terminal_type_id: null,
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
    note: '',
  };

  const methods = useForm<FormData>({
    defaultValues: initialData || defaultFormValues,
    resolver: yupResolver(schemaTerminal) as any,
  });

  const { getAddressByLatLongSafe, getLatLongFromAddress } = useCommonAPI();
  const {
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    formState: { isValid, isDirty },
  } = methods;

  // Reset form when initialData changes
  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
  }, [initialData, reset]);

  const onError = () => {
    ToastTopHelper.error(t('Please fill in all required fields'));
  };

  // Watch form values
  const addressType = watch('address_type');
  const latitude = watch('latitude');
  const longitude = watch('longitude');
  const address = watch('street_address');
  const selectedProvince = watch('city_province')?.value;
  const selectedDistrict = watch('city_county_district')?.value;
  const ward = watch('ward_town_township')?.value;
  const district = watch('city_county_district')?.value;
  const province = watch('city_province')?.value;

  // Apply debounce to form values
  const debouncedLatitude = useDebounce(latitude, 800);
  const debouncedLongitude = useDebounce(longitude, 800);
  const debouncedAddress = useDebounce(address, 800);
  const debouncedWard = useDebounce(ward, 800);
  const debouncedDistrict = useDebounce(district, 800);
  const debouncedProvince = useDebounce(province, 800);

  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    const { data, status } = await getAddressByLatLongSafe(lat, long);
    if (!status) {
      setValue('latitude', null);
      setValue('longitude', null);
      return;
    }

    setValue('city_province', {
      value: data.region_1depth_name,
      label: data.region_1depth_name,
    });
    setValue('city_county_district', {
      value: data.region_2depth_name,
      label: data.region_2depth_name,
    });
    setValue('ward_town_township', {
      value: data.region_3depth_name,
      label: data.region_3depth_name,
    });
    setValue('street_address', data.region_4depth_name);
  };

  const fetchLatLongFromAddress = async ({
    street,
    ward,
    district,
    province,
  }: {
    street: string;
    ward: string;
    district: string;
    province: string;
  }) => {
    if (!ward || !district || !province) return;

    const fullAddress = street
      ? `${province} ${district} ${ward} ${street}`
      : `${province} ${district} ${ward}`;
    const regionInfo = await getLatLongFromAddress(fullAddress);
    if (!regionInfo.status) {
      setValue('street_address', '');
      return;
    }
    setValue('latitude', regionInfo.data.y);
    setValue('longitude', regionInfo.data.x);
  };

  // Update geographic information based on coordinates
  useEffect(() => {
    if (
      addressType === 'geographic_coordinates' &&
      debouncedLatitude &&
      debouncedLongitude &&
      isDirtyEdit
    ) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }

    if (debouncedLatitude && debouncedLongitude) {
      setMarkerData([
        {
          lat: debouncedLatitude,
          lng: debouncedLongitude,
          name: watch('name'),
        },
      ]);
    } else {
      setMarkerData([]);
    }
  }, [debouncedLatitude, debouncedLongitude, addressType]);

  // Update coordinates based on address
  useEffect(() => {
    if (
      addressType === 'address' &&
      debouncedWard &&
      debouncedDistrict &&
      debouncedProvince &&
      isDirtyEdit
    ) {
      fetchLatLongFromAddress({
        street: debouncedAddress,
        ward: debouncedWard,
        district: debouncedDistrict,
        province: debouncedProvince,
      }).then((res) => {
        if (!res.status) {
          setValue('latitude', null);
          setValue('longitude', null);
          setValue('city_province', null);
          setValue('city_county_district', null);
          setValue('ward_town_township', null);
          setValue('street_address', '');
        }
      });
    }
  }, [
    addressType,
    debouncedAddress,
    debouncedWard,
    debouncedDistrict,
    debouncedProvince,
  ]);

  // Generate district options based on selected province
  const districtOptions = useMemo(() => {
    if (!selectedProvince) return [];

    const province = koreaProvinces.find(
      (p) => p.korean_name === selectedProvince,
    );

    if (!province) return [];

    return province.districts.map((district) => ({
      value: district.korean_name,
      label: i18n.language === 'en' ? district.name : district.korean_name,
    }));
  }, [selectedProvince, i18n.language]);

  // Generate sub-district options based on selected province and district
  const subDistrictOptions = useMemo(() => {
    if (!selectedProvince || !selectedDistrict) return [];

    const province = koreaProvinces.find(
      (p) => p.korean_name === selectedProvince,
    );

    if (!province) return [];

    const district = province.districts.find(
      (d) => d.korean_name === selectedDistrict,
    );

    if (!district || !district.sub_districts) return [];

    return district.sub_districts.map((subDistrict) => ({
      value: subDistrict.korean_name,
      label:
        i18n.language === 'en' ? subDistrict.name : subDistrict.korean_name,
    }));
  }, [selectedProvince, selectedDistrict, i18n.language]);

  // Reset dependent fields when province changes
  const handleProvinceChange = () => {
    setIsDirtyEdit(true);
    setValue('city_county_district', null);
    setValue('ward_town_township', null);
    setValue('street_address', '');
    setValue('latitude', 0);
    setValue('longitude', 0);
  };

  // Reset dependent fields when district changes
  const handleDistrictChange = () => {
    setIsDirtyEdit(true);
    setValue('ward_town_township', null);
    setValue('street_address', '');
    setValue('latitude', 0);
    setValue('longitude', 0);
  };

  // Reset coordinate fields when ward changes
  const handleWardChange = () => {
    setIsDirtyEdit(true);
    setValue('street_address', '');
    setValue('latitude', 0);
    setValue('longitude', 0);
  };

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
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
  const navigate = useNavigate();

  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    try {
      await onSubmit(data);
      reset(data, {
        keepDirty: false,
        keepValues: true,
      });
      navigate(CustomRoutes.terminals.path);
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };
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
              disabled={!isValid}
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
            <FormBlock>
              <div className="form-grid">
                <CustomInputHookForm
                  name="code"
                  label="ID"
                  disabled
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
                  name="terminal_type_id"
                  control={control as any}
                  loadOptions={
                    getOptionsByModel({
                      name_modal: 'terminalType',
                    }) as any
                  }
                  placeholder={t('Select')}
                />
                <UnitInput
                  name="time_stops.value"
                  label={t('Time Stops')}
                  placeholder="0"
                  unit={watch('time_stops.unit')}
                  type="number"
                  isRequired
                />
                <CustomRadio
                  name="address_type"
                  control={control}
                  label={t('Address Type')}
                  options={[
                    {
                      value: 'geographic_coordinates',
                      label: t('Geographic Coordinates'),
                    },
                    {
                      value: 'address',
                      label: t('Address'),
                    },
                  ]}
                  row={true}
                />
                <div></div>
                <CustomInputHookForm
                  required
                  name="latitude"
                  label={t('Latitude')}
                  placeholder={t('Latitude')}
                  type="number"
                  disabled={addressType === 'address'}
                />
                <CustomInputHookForm
                  required
                  name="longitude"
                  label={t('Longitude')}
                  placeholder={t('Longitude')}
                  type="number"
                  disabled={addressType === 'address'}
                />
                <CustomSelect
                  required
                  label={t('City / Province')}
                  name="city_province"
                  control={control as any}
                  options={koreaProvinces.map((province) => ({
                    value: province.korean_name,
                    label:
                      i18n.language === 'en'
                        ? province.name
                        : province.korean_name,
                  }))}
                  placeholder={t('Select')}
                  setValue={handleProvinceChange}
                  disabled={addressType === 'geographic_coordinates'}
                />
                <CustomSelect
                  required
                  label={t('City / County / District')}
                  name="city_county_district"
                  control={control as any}
                  options={districtOptions}
                  placeholder={t('Select')}
                  disabled={
                    addressType === 'geographic_coordinates' ||
                    !selectedProvince
                  }
                  setValue={handleDistrictChange}
                />
                <CustomSelect
                  required
                  label={t('Ward / Town / Township')}
                  name="ward_town_township"
                  control={control as any}
                  options={subDistrictOptions}
                  placeholder={t('Select')}
                  disabled={
                    addressType === 'geographic_coordinates' ||
                    !selectedDistrict
                  }
                  setValue={handleWardChange}
                />
                <CustomInputHookForm
                  // required
                  name="street_address"
                  label={t('Street Address')}
                  placeholder={t(
                    'Detailed address (house number, street name)',
                  )}
                  disabled={
                    addressType === 'geographic_coordinates' ||
                    !selectedDistrict
                  }
                />
              </div>
              <div className="mt-3">
                <CustomInputHookForm
                  name="note"
                  label={t('Note')}
                  placeholder={t('Note')}
                />
              </div>
            </FormBlock>
            <Map
              operatingMarkers={markerData}
              style={{ height: 650 }}
            />
            {/* <MapKakao
              center={markerData.length > 0 ? { lat: markerData[0].lat, lng: markerData[0].lng } : undefined}
              operatingMarkers={markerData.length > 0 ? markerData : []}
              polylines={markerData.length > 0 ? [markerData] : []}
              // bounds={mapBounds || undefined}
              style={{ height: 350 }}
            /> */}
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
              disabled={loading}
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

export default FormTerminals;
