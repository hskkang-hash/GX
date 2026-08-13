import { useEffect, useState, useMemo } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomInputHookForm,
  FormBlock,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import EnFlag from '@/assets/images/english-flag.svg';
import KrFlag from '@/assets/images/korea-flag.svg';
import ThFlag from '@/assets/images/thai-flag.svg';
import CustomRadio from '@/components/Form/CustomRadio';
import PhoneNumberInput from '@/components/Form/PhoneNumberInput';
import CustomSearchMapUnified from '@/components/search/CustomSearchMapUnified';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { validatePhoneByMask } from '@/services/schemaForm';
import {
  checkPhoneMaskType,
  getPhoneMaskTypeByLanguage,
  useDebounce,
} from '@/utils/utils';

import useAPI from '../../../../../deliveryInquiry/useAPI';

// Define types for better type safety
interface DeliveryOption {
  value: string;
  label: string;
}

interface TerminalOption {
  value: string | number;
  label: string;
  name: string;
  full_address: string;
}

const ShippingInfomation = () => {
  const { control, setValue, watch } = useFormContext();

  const [theme] = useTheme();
  const { t, i18n } = useTranslation();
  const { getTerminals, getDeliveryOption } = useAPI();
  const [deliveryOption, setDeliveryOption] = useState<DeliveryOption[]>([]);
  const [isInternationalAddress, setIsInternationalAddress] = useState(false);

  // Memoize getTerminals function to prevent multiple API calls
  const memoizedGetTerminals = useMemo(() => getTerminals(), [getTerminals]);

  useEffect(() => {
    const fetchDeliveryOption = async () => {
      const { success, data, message } = await getDeliveryOption();
      if (success) {
        const transformData = data.map(
          (item: { code: string; name: string }) => ({
            value: item.code,
            label: t(item.name),
          }),
        );
        setDeliveryOption(transformData);
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    };
    fetchDeliveryOption();
  }, []);

  // Watch form values
  const latitude = watch('data.recipient.latitude');
  const longitude = watch('data.recipient.longitude');
  const recipientAddress = watch('data.recipient.full_address');
  const debouncedLatitude = useDebounce(latitude, 500);
  const debouncedLongitude = useDebounce(longitude, 500);

  // Memoize getTerminals function with address dependency to reload when address changes
  const memoizedGetTerminalsWithAddress = useMemo(
    () => getTerminals({ address: recipientAddress }),
    [getTerminals, recipientAddress],
  );

  const { getAddressByLatLongSafe } = useCommonAPI();
  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    const { data, status } = await getAddressByLatLongSafe(lat, long);
    if (!status) {
      return;
    }

    setValue('data.recipient.full_address', data?.address_name);
    setValue('data.recipient.city_province', {
      value: data?.region_1depth_name,
      label: data?.region_1depth_name,
    });
    setValue('data.recipient.city_county_district', {
      value: data?.region_2depth_name,
      label: data?.region_2depth_name,
    });
    setValue('data.recipient.ward_town_township', {
      value: data?.region_3depth_name,
      label: data?.region_3depth_name,
    });
    setValue(
      'data.recipient.street_address',
      formatKoreanStreetAddress(data as any),
    );
  };

  useEffect(() => {
    if (debouncedLatitude && debouncedLongitude && !isInternationalAddress) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }
  }, [debouncedLatitude, debouncedLongitude, isInternationalAddress]);

  return (
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
          <PhoneNumberInput
            required
            type="tel"
            name="data.sender.phone_number"
            placeholder={t('Phone Number')}
            label={t('Phone Number')}
            maxLength={32}
            initialValues={watch('data.sender.phone_number')}
            initialMask={(() => {
              return getPhoneMaskTypeByLanguage(i18n.language);
            })()}
            validatePhoneByMask={validatePhoneByMask}
            maskOptions={[
              {
                value: 'Kr',
                pattern: [
                  '(',
                  '+',
                  '8',
                  '2',
                  ')',
                  ' ',
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'Korean',
                flag: KrFlag,
                type: 'img',
              },
              {
                value: 'En',
                pattern: [
                  '+',
                  '1',
                  ' ',
                  '(',
                  /[1-9]/,
                  /\d/,
                  /\d/,
                  ')',
                  ' ',
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'English',
                flag: EnFlag,
                type: 'img',
              },
              {
                value: 'Th',
                pattern: [
                  '(',
                  '+',
                  '6',
                  '6',
                  ')',
                  ' ',
                  /[689]/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'Thai',
                flag: ThFlag,
                type: 'img',
              },
            ]}
          />
          <PaginationSelect
            required
            label={t('Pickup Location')}
            name="data.sender.location_id.value"
            control={control}
            loadOptions={memoizedGetTerminals}
            placeholder={t('Select')}
            description={t(
              'Please bring the package to the terminal above to proceed with the shipment.',
            )}
            controlHeight="3.5rem"
            formatOptionLabel={(option: TerminalOption) => (
              <div>
                <div style={{ fontWeight: '500', fontSize: '1rem' }}>
                  {t('Address')}: {option.full_address}
                </div>
                <div style={{ fontSize: '0.875rem', marginTop: '2px' }}>
                  {t('Name')}: {option.name}
                </div>
              </div>
            )}
          />
          <CustomInputHookForm
            name="data.sender.note"
            placeholder={t('Note')}
            label={t('Note')}
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
          <PhoneNumberInput
            required
            type="tel"
            name="data.recipient.phone_number"
            placeholder={t('Phone Number')}
            label={t('Phone Number')}
            maxLength={32}
            initialValues={watch('data.recipient.phone_number')}
            initialMask={(() => {
              return getPhoneMaskTypeByLanguage(i18n.language);
            })()}
            validatePhoneByMask={validatePhoneByMask}
            maskOptions={[
              {
                value: 'Kr',
                pattern: [
                  '(',
                  '+',
                  '8',
                  '2',
                  ')',
                  ' ',
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'Korean',
                flag: KrFlag,
                type: 'img',
              },
              {
                value: 'En',
                pattern: [
                  '+',
                  '1',
                  ' ',
                  '(',
                  /[1-9]/,
                  /\d/,
                  /\d/,
                  ')',
                  ' ',
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'English',
                flag: EnFlag,
                type: 'img',
              },
              {
                value: 'Th',
                pattern: [
                  '(',
                  '+',
                  '6',
                  '6',
                  ')',
                  ' ',
                  /[689]/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  '-',
                  /\d/,
                  /\d/,
                  /\d/,
                  /\d/,
                ],
                label: 'Thai',
                flag: ThFlag,
                type: 'img',
              },
            ]}
          />
          <CustomSearchMapUnified
            label={t('Address')}
            isRequired
            value={watch('data.recipient.full_address')}
            onSelect={(value, option) => {
              console.log('options_addresssss123', option);
              setValue('data.recipient.full_address', value);
              setValue('data.recipient.latitude', option.lat);
              setValue('data.recipient.longitude', option.lng);

              setValue('data.recipient.city_province', option.province);
              setValue('data.recipient.city_county_district', option.district);
              setValue('data.recipient.ward_town_township', option.township);
              setValue(
                'data.recipient.street_address',
                option?.street_address
                  ? option?.street_address
                  : formatKoreanStreetAddress(option),
              );
            }}
            onClear={() => {
              setValue('data.recipient.full_address', '');
              setValue('data.recipient.latitude', null);
              setValue('data.recipient.longitude', null);
              setValue('data.recipient.city_province', null);
              setValue('data.recipient.city_county_district', null);
              setValue('data.recipient.ward_town_township', null);
              setValue('data.recipient.street_address', '');
              setIsInternationalAddress(false);
            }}
            placeholder={t('Address')}
            // disabled={addressType === "geographic_coordinates"}
          />

          <div className="">
            <CustomInputHookForm
              name="data.recipient.note"
              label={t('Note')}
            />
          </div>
        </div>
      </FormBlock>
      <FormBlock>
        <div
          className="header-title"
          style={{ paddingBottom: '3px' }}
        >
          {t('Delivery Option')}
        </div>
        <CustomRadio
          name="data.delivery_option"
          control={control}
          // label={t("Barometric Altimeter")}
          options={deliveryOption}
          row={true}
          minWidthStyle="unset"
        />
        {watch('data.delivery_option') === 'collect_at_location' && (
          <PaginationSelect
            required
            name="data.delivery_location_id.value"
            control={control}
            loadOptions={memoizedGetTerminalsWithAddress}
            cacheUniqs={[recipientAddress]}
            disabled={!recipientAddress}
            placeholder={t('Select Location')}
            description={t(
              'Your package will be delivered to the pickup location you selected.',
            )}
            controlHeight="3.5rem"
            formatOptionLabel={(option: TerminalOption) => (
              <div>
                <div style={{ fontWeight: '500', fontSize: '1rem' }}>
                  {t('Address')}: {option.full_address}
                </div>
                <div style={{ fontSize: '0.875rem', marginTop: '2px' }}>
                  {t('Name')}: {option.name}
                </div>
              </div>
            )}
          />
        )}
      </FormBlock>
    </div>
  );
};

export default ShippingInfomation;
