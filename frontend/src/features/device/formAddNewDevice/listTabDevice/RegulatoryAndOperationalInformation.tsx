import { useEffect, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, useConfigSystem, useTheme, useUserInfo } from 'rj-core';

import CustomDateRangePicker from '@/components/Form/CustomDateRangePicker';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';

import CustomDatePicker from '../../../../components/Form/CustomDatePicker';
import CustomRadio from '../../../../components/Form/CustomRadio';
import CustomSlider from '../../../../components/Form/CustomSlider';
import CustomTableRadio from '../../../../components/Form/CustomTableRadio';
import ExpanDropDown from '../../../../components/Form/ExpanDropDown';
import UnitInput from '../../../../components/Form/UnitInput';
import './RegulatoryAndOperationalInformation.scss';
import { getDateFormatStringForDayjs } from '@/features/Dashboard/utils/formatDateTime';

const RegulatoryAndOperationalInformation = () => {
  const { control, watch, getValues, trigger, setValue, clearErrors } =
    useFormContext();
  const { getOptionsByModel } = useCommonAPI();
  const [isExpandedEnvironmental, setIsExpandedEnvironmental] = useState(true);
  const [theme, _] = useTheme();
  const { t } = useTranslation();
  const insuranceStatusOptions = [
    { value: true, label: t('Yes') },
    { value: false, label: t('No') },
  ];

  const [configSystem] = useConfigSystem();
  const userInfo = useUserInfo();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = getDateFormatStringForDayjs(userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? 'YYYY/MM/DD');

  const safetyFeaturesOptions = [
    {
      name: 'data.safety_feature.dual_imu',
      value: 'Dual IMU',
      label: t('Dual IMU'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.dual_gps',
      value: 'Dual GPS',
      label: t('Dual GPS'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.dual_battery',
      value: 'Dual battery system',
      label: t('Dual battery system'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.emergency_parachute',
      value: 'Emergency parachute system',
      label: t('Emergency parachute system'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.return_to_home',
      value: 'Return-to-home (RTH) capability',
      label: t('Return-to-home (RTH) capability'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.obstacle_detection_360',
      value: '360° obstacle detection',
      label: t('360° obstacle detection'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.stereo_cameras',
      value: 'Forward-facing stereo cameras',
      label: t('Forward-facing stereo cameras'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.lidar_mapping',
      value: 'LIDAR-based obstacle mapping',
      label: t('LIDAR-based obstacle mapping'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.safety_feature.emergency_braking',
      value: 'Automatic emergency braking',
      label: t('Automatic emergency braking'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
  ];
  const currentStatusOptions = [
    { value: 'active', label: t('Active') },
    { value: 'expired', label: t('Expired') },
    { value: 'suspended', label: t('Suspended') },
  ];

  const watchedTemperatureRangeLength = watch(
    'data.environmental_specification.temperature_range.length.value',
  );
  const watchedTemperatureRangeWidth = watch(
    'data.environmental_specification.temperature_range.width.value',
  );
  useEffect(() => {
    const handleValidation = async () => {
      if (
        watchedTemperatureRangeLength != null &&
        watchedTemperatureRangeWidth != null
      ) {
        const minNum = Number(watchedTemperatureRangeLength);
        const maxNum = Number(watchedTemperatureRangeWidth);
        if (minNum < maxNum) {
          clearErrors([
            'data.environmental_specification.temperature_range.length.value',
            'data.environmental_specification.temperature_range.width.value',
          ]);
        } else if (minNum == maxNum) {
          await trigger([
            'data.environmental_specification.temperature_range.length.value',
            'data.environmental_specification.temperature_range.width.value',
          ]);
        } else if (minNum > maxNum) {
          await trigger([
            'data.environmental_specification.temperature_range.length.value',
          ]);
        }
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [
    watchedTemperatureRangeLength,
    watchedTemperatureRangeWidth,
    clearErrors,
    trigger,
  ]);

  return (
    <div className={`regulatory-form ${theme}`}>
      <ExpanDropDown label={t('Manufacturers')}>
        <div className="form-grid">
          <CustomInputHookForm
            label={t('Manufacturer')}
            placeholder={t('Manufacturer')}
            name="data.manufacturer_information.manufacturer"
          />
          <PaginationSelect
            label={t('Country of Origin')}
            name="data.manufacturer_information.country_of_origin_id.value"
            placeholder={t('Country of Origin')}
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'country',
              key: 'name',
              value: 'id',
              search_field: 'name',
            })}
          />
          <CustomInputHookForm
            label={t('Model / Product Code')}
            placeholder={t('Model / Product Code')}
            name="data.manufacturer_information.model_number"
          />

          <CustomInputHookForm
            label={t('Serial Number')}
            placeholder={t('Serial Number')}
            name="data.manufacturer_information.serial_number"
            type="number"
          />
          <CustomDatePicker
            name="data.manufacturer_information.production_date"
            label={t('Production Date')}
            format={dateFormat}
            control={control}
          />
          <CustomInputHookForm
            label={t('Registration Number')}
            placeholder={t('C4CM2841574')}
            name="data.manufacturer_information.registration_number"
          />
          <CustomRadio
            name="data.manufacturer_information.insurance_status"
            control={control}
            label={t('Insurance Status')}
            options={insuranceStatusOptions}
            row={true}
          />
          {Boolean(
            watch('data.manufacturer_information.insurance_status') == 'true' ||
            watch('data.manufacturer_information.insurance_status') == true,
          ) && (
              <>
                <CustomInputHookForm
                  label={t('Insurance Type')}
                  placeholder={t('Insurance Type')}
                  name="data.manufacturer_information.insurance_type"
                />
                <CustomInputHookForm
                  label={t('Insurance Provider')}
                  placeholder={t('Insurance Provider')}
                  name="data.manufacturer_information.insurance_provider"
                />
                <CustomInputHookForm
                  type="tel"
                  label={t('Policy Number')}
                  placeholder={t('Policy Number')}
                  name="data.manufacturer_information.policy_number"
                />
                <CustomDateRangePicker
                  fromName="data.manufacturer_information.validity_period_from"
                  toName="data.manufacturer_information.validity_period_to"
                  label={t('Validity Period')}
                  control={control}
                  format={dateFormat}
                />
                <CustomRadio
                  required
                  name="data.manufacturer_information.current_status"
                  control={control}
                  label={t('Current Status')}
                  options={currentStatusOptions}
                  row={true}
                />
              </>
            )}
        </div>
      </ExpanDropDown>
      <ExpanDropDown
        label={t('Environmental Specifications')}
        expanded={isExpandedEnvironmental}
        onChange={setIsExpandedEnvironmental}
      >
        <div className="form-grid">
          <div className="device-size">
            <div className="device-size__label">{t('Temperature Range')}</div>
            <div className={`device-size__dimensions ${theme}`}>
              <UnitInput
                name="data.environmental_specification.temperature_range.length.value"
                unit={getValues(
                  'data.environmental_specification.temperature_range.length.unit',
                )}
                negative
                iconDivider={getValues(
                  'data.environmental_specification.temperature_range.icon_device',
                )}
                placeholder={t('0')}
              />
              <UnitInput
                name="data.environmental_specification.temperature_range.width.value"
                unit={getValues(
                  'data.environmental_specification.temperature_range.width.unit',
                )}
                negative
                placeholder={t('0')}
              />
            </div>
          </div>
          <CustomSlider
            name="data.environmental_specification.humidity.value"
            label={t('Humidity (%)')}
            control={control}
            range={true}
            min={0}
            max={100}
            step={1}
            isTooltip={isExpandedEnvironmental}
          />
          <CustomInputHookForm
            label={t('Precipitation')}
            placeholder="0"
            name="data.environmental_specification.precipitation"
          />
          <UnitInput
            label={t('Wind Speed (Up to)')}
            name="data.environmental_specification.wind_speed.value"
            unit={getValues('data.environmental_specification.wind_speed.unit')}
            placeholder="0"
          />
          <UnitInput
            label={t('Noise Level Takeoff')}
            name="data.environmental_specification.noise_takeoff.value"
            unit={getValues(
              'data.environmental_specification.noise_takeoff.unit',
            )}
            placeholder="0"
          />
          <UnitInput
            label={t('Noise Level Cruise')}
            name="data.environmental_specification.noise_cruise.value"
            unit={getValues(
              'data.environmental_specification.noise_cruise.unit',
            )}
            placeholder="0"
          />
          <UnitInput
            label={t('Noise Level Landing')}
            name="data.environmental_specification.noise_landing.value"
            unit={getValues(
              'data.environmental_specification.noise_landing.unit',
            )}
            placeholder="0"
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown label={t('Safety Features')}>
        <CustomTableRadio
          control={control}
          listItem={safetyFeaturesOptions}
        />
      </ExpanDropDown>
    </div>
  );
};

export default RegulatoryAndOperationalInformation;
