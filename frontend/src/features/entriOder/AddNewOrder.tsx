import { yupResolver } from '@hookform/resolvers/yup';
import { Box, styled } from '@mui/material';
import { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  FormBlock,
  Main,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import PhoneNumberInputV2 from '@/components/Form/PhoneNumberInputV2';
import UnitInput from '@/components/Form/UnitInput';
import CustomSearchMap from '@/components/search/CustomSearchMap';
import CustomSearchMapUnified from '@/components/search/CustomSearchMapUnified';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import API, { CustomRoutes, endpoint } from '@/services/API';
import { addNewEtriOrderSchema } from '@/services/schemaForm';
import { convertOrderDataToForm } from '@/utils/addNewOrderDataConvert';
import { useDebounce } from '@/utils/utils';

import './assets/scss/AddNewOrder.scss';
import useAPI from './hooks/useAPI';

interface IFormData {
  data: Record<string, any>;
}

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
}>(({ mode, error }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
}));

export default function FormAddNewOrder() {
  const { id } = useParams();
  const [theme, _] = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { getDetailOrder } = useAPI();
  const [detailOrder, setDetailOrder] = useState<any>(null);

  const { getOptionsByModel } = useCommonAPI();
  const [isInternationalSender, setIsInternationalSender] = useState(false);
  const [isInternationalRecipient, setIsInternationalRecipient] =
    useState(false);

  const initialData = detailOrder ? convertOrderDataToForm(detailOrder) : null;
  const methods = useForm<IFormData>({
    defaultValues: initialData
      ? initialData
      : {
          data: {
            sender: {
              name: '',
              phone_number: '',
              address_type: 'geographic_coordinates',
              full_address: '',
              latitude: null,
              longitude: null,
              street_address: null,
              city_province: null,
              city_county_district: null,
              ward_town_township: null,
              postal_code: null,
              address_detail: '',
              location_id: {
                value: null,
                type: 'select',
              },
            },
            recipient: {
              name: '',
              phone_number: '',
              address_type: 'geographic_coordinates',
              full_address: '',
              latitude: 0,
              longitude: 0,
              street_address: null,
              city_province: null,
              city_county_district: null,
              ward_town_township: null,
              postal_code: null,
              note: '',
            },
            package: [
              {
                package_weight: {
                  value: null,
                  unit: 'kg',
                },
                dimensions: {
                  length: {
                    value: null,
                    unit: 'cm',
                  },
                  width: {
                    value: null,
                    unit: 'cm',
                  },
                  height: {
                    value: null,
                    unit: 'cm',
                  },
                },
                item_type: {
                  value: '',
                  type: 'select',
                },
              },
            ],
          },
        },
    mode: 'onChange',
    resolver: yupResolver(addNewEtriOrderSchema(t)),
  });

  const {
    handleSubmit,
    setValue,
    control,
    getValues,
    watch,
    formState: { isValid, errors, isSubmitting },
  } = methods;

  const { getEtriTerminals } = useAPI();

  useEffect(() => {
    if (id) {
      (async () => {
        const { success, message, data } = await getDetailOrder(Number(id));
        if (success) {
          setDetailOrder(data);
        }
        if (!success) {
          ToastTopHelper.error(message);
        }
      })();
    }
  }, [id]);

  useEffect(() => {
    getEtriTerminals();
  }, []);

  // Watch address form values with debouncing
  const addressFields = {
    recipient: {
      latitude: useDebounce(watch('data.recipient.latitude'), 500),
      longitude: useDebounce(watch('data.recipient.longitude'), 500),
    },
    sender: {
      latitude: useDebounce(watch('data.sender.latitude'), 500),
      longitude: useDebounce(watch('data.sender.longitude'), 500),
    },
  };

  const { getAddressByLatLongSafe } = useCommonAPI();

  // Helper function to clear address fields
  const clearAddressFields = (type: 'recipient' | 'sender'): void => {
    const basePath = type === 'recipient' ? 'data.recipient' : 'data.sender';
    const fieldsToClear = [
      'latitude',
      'longitude',
      'full_address',
      'city_province',
      'city_county_district',
      'ward_town_township',
      'street_address',
      'postal_code',
    ];

    fieldsToClear.forEach((field) => {
      const value =
        field === 'full_address' || field === 'street_address' ? '' : null;
      setValue(`${basePath}.${field}`, value);
    });
  };

  // Helper function to set address fields from API response
  const setAddressFields = (type: 'recipient' | 'sender', data: any): void => {
    const basePath = type === 'recipient' ? 'data.recipient' : 'data.sender';

    setValue(`${basePath}.full_address`, data?.address_name || '');
    setValue(`${basePath}.city_province`, {
      value: data?.region_1depth_name || '',
      label: data?.region_1depth_name || '',
    });
    setValue(`${basePath}.city_county_district`, {
      value: data?.region_2depth_name || '',
      label: data?.region_2depth_name || '',
    });
    setValue(`${basePath}.ward_town_township`, {
      value: data?.region_3depth_name || '',
      label: data?.region_3depth_name || '',
    });
    setValue(`${basePath}.street_address`, formatKoreanStreetAddress(data));
  };

  // Optimized address fetching function
  const fetchRegionByLatLong = async (
    lat: number,
    long: number,
    type: 'recipient' | 'sender',
  ): Promise<void> => {
    if (!lat || !long) return;

    try {
      const { data, status } = await getAddressByLatLongSafe(lat, long);

      if (!status) {
        clearAddressFields(type);
        return;
      }

      setAddressFields(type, data);
    } catch (error) {
      console.error(`Error fetching address for ${type}:`, error);
      clearAddressFields(type);
    }
  };

  // Combined useEffect for both recipient and sender address updates
  useEffect(() => {
    const updateAddress = async (type: 'recipient' | 'sender') => {
      const { latitude, longitude } = addressFields[type];
      const isInternational =
        type === 'recipient' ? isInternationalRecipient : isInternationalSender;

      if (latitude && longitude && !isInternational) {
        await fetchRegionByLatLong(latitude, longitude, type);
      }
    };

    // Update both addresses when coordinates change
    updateAddress('recipient');
    updateAddress('sender');
  }, [
    addressFields.recipient.latitude,
    addressFields.recipient.longitude,
    addressFields.sender.latitude,
    addressFields.sender.longitude,
    isInternationalRecipient,
    isInternationalSender,
  ]);

  const handleAddNewOrder = async (orderData: any) => {
    console.log('orderData', orderData.data.recipient);

    const transformData = {
      order_org: 'etri',
      sender_name: orderData.data.sender.name,
      sender_phone: orderData.data.sender.phone_number,
      recipient_name: orderData.data.recipient.name,
      recipient_phone: orderData.data.recipient.phone_number,
      recipient_note: orderData.data.recipient.note,
      pickup_location_id: orderData.data.sender.location_id.value.value,

      sender_address: {
        // city: orderData.data.sender.city_province.value,
        // district: orderData.data.sender.city_county_district.value,
        // street: orderData.data.sender.street_address,
        full_address: orderData.data.sender.full_address,
        lat: orderData.data.sender.latitude,
        lng: orderData.data.sender.longitude,
        postal_code: orderData.data.sender.postal_code,
      },
      recipient_address: {
        // city: orderData.data.recipient.city_province.value,
        // district: orderData.data.recipient.city_county_district.value,
        // street: orderData.data.recipient.street_address,
        full_address: orderData.data.recipient.full_address,
        lat: orderData.data.recipient.latitude,
        lng: orderData.data.recipient.longitude,
        postal_code: orderData.data.recipient.postal_code,
      },

      items: orderData.data.package.map((item: any) => ({
        item_type_id: item.item_type.value.value,
        weight: {
          value: item.package_weight.value,
          unit: item.package_weight.unit,
        },
        dimension_l: {
          value: item.dimensions.length.value,
          unit: 'cm',
        },
        dimension_w: {
          value: item.dimensions.width.value,
          unit: 'cm',
        },
        dimension_h: {
          value: item.dimensions.height.value,
          unit: 'cm',
        },
        is_waterproof: false,
        is_fragile: false,
        note: '',
      })),
      delivery_option_code: 'collect_at_location',
      payment_method_code: 'cash',
    };

    console.log('transformData', transformData);
    const response = await API.post(
      endpoint.deliveryInquiryOrder,
      transformData,
    );
    console.log('response', response);

    if (response.success) {
      ToastTopHelper.success(response.message);
      navigate(-1);
    } else {
      ToastTopHelper.error(response.message);
    }
  };

  console.log('values', getValues());

  const dimensionError = errors.data?.package?.map((item: any) => {
    if (!item || !item.dimensions) return false;
    return (
      !!item.dimensions.length?.value?.message ||
      !!item.dimensions.width?.value?.message ||
      !!item.dimensions.height?.value?.message
    );
  });

  const weightError = errors.data?.package?.map((item: any) => {
    if (!item || !item.package_weight) return false;
    return !!item.package_weight?.value?.message;
  });

  console.log('dimensionError', dimensionError);
  console.log('weightError', weightError);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleAddNewOrder)}
        className={`form-add-new-packaging ${theme}`}
      >
        <CustomBreadcrumb
          items={[
            {
              url: CustomRoutes.etriOrder.path,
            },
            { text: t('Add New Order') },
          ]}
          buttons={[
            <CustomBtn
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={() => navigate(-1)}
            />,
            <CustomBtn
              label={t('Confirm')}
              variant="contained"
              color="primary"
              size="md"
              style={{ width: '6rem' }}
              type={'submit'}
              onClick={handleSubmit(handleAddNewOrder)}
              disabled={
                !isValid ||
                watch('data.sender.full_address') === '' ||
                watch('data.recipient.full_address') === '' ||
                isSubmitting
              }
            />,
          ]}
        />
        <Main>
          <div className={`form-container ${theme}`}>
            <FormBlock>
              <div className="header-title">{t('Sender')}</div>
              <div className="form-grid">
                <CustomInputHookForm
                  required
                  name="data.sender.name"
                  label={t('Name')}
                  placeholder={t('Name')}
                />
                <PhoneNumberInputV2
                  isRequired
                  name="data.sender.phone_number"
                  label={t('Phone Number')}
                  placeholder={t('xxx-xxxx-xxxx')}
                />
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    width: '100%',
                    gap: '0.4rem',
                  }}
                >
                  <StyledLabel
                    mode={theme}
                    error={!!errors.data?.sender?.address}
                  >
                    {t('Address')}
                    <span style={{ color: Colors.Red }}>*</span>
                  </StyledLabel>
                  <Box sx={{ display: 'flex', gap: '0.25rem', width: '100%' }}>
                    <Box sx={{ flex: 1 }}>
                      <CustomSearchMapUnified
                        isRequired
                        value={watch('data.sender.full_address')}
                        onSelect={(value, option) => {
                          console.log('options_addresssss', option);
                          setValue('data.sender.full_address', value);
                          setValue('data.sender.latitude', option.lat);
                          setValue('data.sender.longitude', option.lng);

                          // Check if this is an international address (from Google Places)
                          const isInternational =
                            option.hasOwnProperty('country') ||
                            option.hasOwnProperty('formatted_address');
                          setIsInternationalSender(isInternational);

                          if (isInternational) {
                            // For international addresses, use Google Places data structure
                            setValue(
                              'data.sender.city_province',
                              option.administrative_area_level_1 || '',
                            );
                            setValue(
                              'data.sender.city_county_district',
                              option.administrative_area_level_2 || '',
                            );
                            setValue(
                              'data.sender.ward_town_township',
                              option.locality || option.sublocality || '',
                            );
                            setValue(
                              'data.sender.street_address',
                              option.formatted_address || value,
                            );
                            setValue(
                              'data.sender.postal_code',
                              option.postal_code || '',
                            );
                          } else {
                            // For Korean addresses, use Kakao data structure
                            setValue(
                              'data.sender.postal_code',
                              option?.zonecode,
                            );
                            setValue(
                              'data.sender.city_province',
                              option.province,
                            );
                            setValue(
                              'data.sender.city_county_district',
                              option.district,
                            );
                            setValue(
                              'data.sender.ward_town_township',
                              option.township,
                            );
                            setValue('data.sender.street_address', '');
                            setValue(
                              'data.sender.street_address',
                              formatKoreanStreetAddress(option),
                            );
                          }
                        }}
                        onClear={() => {
                          setValue('data.sender.full_address', '');
                          setValue('data.sender.latitude', null);
                          setValue('data.sender.longitude', null);
                          setValue('data.sender.city_province', null);
                          setValue('data.sender.city_county_district', null);
                          setValue('data.sender.ward_town_township', null);
                          setValue('data.sender.street_address', '');
                          setValue('data.sender.postal_code', null);
                          setIsInternationalSender(false);
                        }}
                        placeholder={t('Address')}
                        // disabled={addressType === "geographic_coordinates"}
                      />
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <CustomInputHookForm
                        name="data.sender.address_detail"
                        placeholder={t('Address Note')}
                      />
                    </Box>
                  </Box>
                </Box>
                <PaginationSelect
                  required
                  label={t('Shipping station')}
                  name="data.sender.location_id.value"
                  control={control}
                  loadOptions={getEtriTerminals()}
                  placeholder={t('Shipping station select')}
                  // description={t(
                  //   "Please bring the package to the terminal above to proceed with the shipment."
                  // )}
                />
              </div>
            </FormBlock>
            <FormBlock>
              <div className="header-title">{t('Recipient')}</div>
              <div className="form-grid">
                <CustomInputHookForm
                  required
                  name="data.recipient.name"
                  label={t('Name')}
                  placeholder={t('Name')}
                />
                <PhoneNumberInputV2
                  isRequired
                  name="data.recipient.phone_number"
                  label={t('Phone Number')}
                  placeholder={t('xxx-xxxx-xxxx')}
                />
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    width: '100%',
                    gap: '0.4rem',
                  }}
                >
                  <StyledLabel
                    mode={theme}
                    error={!!errors.data?.sender?.address}
                  >
                    {t('Address')}
                    <span style={{ color: Colors.Red }}>*</span>
                  </StyledLabel>
                  <Box sx={{ display: 'flex', gap: '0.25rem', width: '100%' }}>
                    <Box sx={{ flex: 1 }}>
                      <CustomSearchMapUnified
                        isRequired
                        value={watch('data.recipient.full_address')}
                        onSelect={(value, option) => {
                          console.log('options_addresssss', option);
                          setValue('data.recipient.full_address', value);
                          setValue('data.recipient.latitude', option.lat);
                          setValue('data.recipient.longitude', option.lng);

                          // Check if this is an international address (from Google Places)
                          const isInternational =
                            option.hasOwnProperty('country') ||
                            option.hasOwnProperty('formatted_address');
                          setIsInternationalRecipient(isInternational);

                          if (isInternational) {
                            // For international addresses, use Google Places data structure
                            setValue(
                              'data.recipient.city_province',
                              option.administrative_area_level_1 || '',
                            );
                            setValue(
                              'data.recipient.city_county_district',
                              option.administrative_area_level_2 || '',
                            );
                            setValue(
                              'data.recipient.ward_town_township',
                              option.locality || option.sublocality || '',
                            );
                            setValue(
                              'data.recipient.street_address',
                              option.formatted_address || value,
                            );
                            setValue(
                              'data.recipient.postal_code',
                              option.postal_code || '',
                            );
                          } else {
                            // For Korean addresses, use Kakao data structure
                            setValue(
                              'data.recipient.postal_code',
                              option?.zonecode,
                            );
                            setValue(
                              'data.recipient.city_province',
                              option.province,
                            );
                            setValue(
                              'data.recipient.city_county_district',
                              option.district,
                            );
                            setValue(
                              'data.recipient.ward_town_township',
                              option.township,
                            );
                            setValue('data.recipient.street_address', '');
                            setValue(
                              'data.recipient.street_address',
                              formatKoreanStreetAddress(option),
                            );
                          }
                        }}
                        onClear={() => {
                          setValue('data.recipient.full_address', '');
                          setValue('data.recipient.latitude', null);
                          setValue('data.recipient.longitude', null);
                          setValue('data.recipient.city_province', null);
                          setValue('data.recipient.city_county_district', null);
                          setValue('data.recipient.ward_town_township', null);
                          setValue('data.recipient.street_address', '');
                          setValue('data.recipient.postal_code', null);
                          setIsInternationalRecipient(false);
                        }}
                        placeholder={t('Address')}
                        // disabled={addressType === "geographic_coordinates"}
                        searchPopup={true}
                      />
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <CustomInputHookForm
                        name="data.recipient.address_detail"
                        placeholder={t('Address Note')}
                      />
                    </Box>
                  </Box>
                </Box>

                <div className="">
                  <CustomInputHookForm
                    name="data.recipient.note"
                    label={t('Note')}
                  />
                </div>
              </div>
            </FormBlock>
            <FormBlock>
              <div className="header-title">{t('Package')}</div>
              {watch('data.package').map((item: any, index: number) => (
                <div
                  className="form-grid"
                  key={`package-${index}`}
                >
                  <div>
                    <UnitInput
                      label={t('Weight')}
                      isRequired
                      name={`data.package.${index}.package_weight.value`}
                      unit={getValues(
                        `data.package.${index}.package_weight.unit`,
                      )}
                      hiddenErrorMessage={true}
                      placeholder="0"
                      onChange={(e) => {
                        setValue(
                          `data.package.${index}.package_weight.value`,
                          e,
                        );
                      }}
                    />
                    <div
                      style={{
                        color: weightError?.[0] ? Colors.Red : Colors.Gray5,
                        fontSize: '0.875rem',
                        paddingTop: '0.85rem',
                      }}
                    >
                      {t('Weight cannot exceed 40 kg')}
                    </div>
                  </div>
                  <PaginationSelect
                    label={t('Item Type')}
                    required
                    name={`data.package.${index}.item_type.value`}
                    control={control}
                    loadOptions={getOptionsByModel({
                      name_modal: 'OrderItemType',
                      search_field: 'name',
                    })}
                    placeholder={t('Select2')}
                  />
                  <Box className="device-size">
                    <div className="device-size__label">
                      {t('Dimensions')}{' '}
                      <span style={{ color: Colors.Red }}>*</span>
                    </div>
                    <div
                      className={`device-size__dimensions ${theme}`}
                      style={{ marginBottom: '0.5rem' }}
                    >
                      <UnitInput
                        name={`data.package.${index}.dimensions.width.value`}
                        unit={getValues(
                          `data.package.${index}.dimensions.width.unit`,
                        )}
                        iconDivider="x"
                        hiddenErrorMessage={true}
                        placeholder={''}
                        onChange={(e) => {
                          setValue(
                            `data.package.${index}.dimensions.width.value`,
                            e,
                          );
                        }}
                      />
                      <UnitInput
                        name={`data.package.${index}.dimensions.length.value`}
                        unit={getValues(
                          `data.package.${index}.dimensions.length.unit`,
                        )}
                        iconDivider="x"
                        hiddenErrorMessage={true}
                        placeholder={''}
                        onChange={(e) => {
                          setValue(
                            `data.package.${index}.dimensions.length.value`,
                            e,
                          );
                        }}
                      />
                      <UnitInput
                        name={`data.package.${index}.dimensions.height.value`}
                        unit={getValues(
                          `data.package.${index}.dimensions.height.unit`,
                        )}
                        hiddenErrorMessage={true}
                        placeholder={''}
                        onChange={(e) => {
                          setValue(
                            `data.package.${index}.dimensions.height.value`,
                            e,
                          );
                        }}
                      />
                    </div>
                    <div
                      style={{
                        color: dimensionError?.[0] ? Colors.Red : Colors.Gray5,
                        fontSize: '0.875rem',
                      }}
                    >
                      {t('entri_order.dimension_requirement')}
                    </div>
                  </Box>
                </div>
              ))}
            </FormBlock>
          </div>
        </Main>
      </form>
    </FormProvider>
  );
}
