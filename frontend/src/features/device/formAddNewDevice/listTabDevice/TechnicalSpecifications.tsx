import { useEffect } from 'react';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { AiFillCloseCircle } from 'react-icons/ai';
import { GoPlus } from 'react-icons/go';
import { CustomInputHookForm, useTheme } from 'rj-core';

import CustomBtn from '@/components/buttons/CustomBtn';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';

import CustomRadio from '../../../../components/Form/CustomRadio';
import CustomTableRadio from '../../../../components/Form/CustomTableRadio';
import ExpanDropDown from '../../../../components/Form/ExpanDropDown';
import UnitInput from '../../../../components/Form/UnitInput';
import useAPIInfoDevice from '../../useAPI/useAPIInfoDevice';
import './TechnicalSpecifications.scss';

const TechnicalSpecifications = () => {
  const {
    control,
    setValue,
    getValues,
    clearErrors,
    watch,
    trigger,
    formState: { errors },
  } = useFormContext();
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'data.device_protocols',
  });
  const [theme, _] = useTheme();

  const { getOptionsByModel } = useCommonAPI();
  const { getOptionsByModelWithPortal } = useAPIInfoDevice();
  const dataFromDeviceId = watch('data.device_id.value')?.value;

  const handleAddMore = () => {
    if (fields.length < 10) {
      append({
        type_of_protocol: {
          value: null,
          type: 'select',
        },
        protocol: {
          value: null,
          type: 'select',
        },
      });
    }
  };

  const { t } = useTranslation();
  const telemetryOptions = [
    {
      name: 'data.telemetry.realtime_flight_data',
      value: 'Real-time flight data transmission',
      label: t('Real-time flight data transmission'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.telemetry.video_streaming',
      value: 'Video streaming (1080p)',
      label: t('Video streaming (1080p)'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.telemetry.battery_status_monitoring',
      value: 'Battery status monitoring',
      label: t('Battery status monitoring'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.telemetry.gps_position_tracking',
      value: 'GPS position tracking',
      label: t('GPS position tracking'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.telemetry.system_health_monitoring',
      value: 'System health monitoring',
      label: t('System health monitoring'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
  ];

  const barometricAltimeterTypeOptions = [
    { value: true, label: t('Yes') },
    { value: false, label: t('No') },
  ];

  const watchedOperatingAltitudeFrom = watch(
    'data.flight_performance.operating_altitude.from.value',
  );
  const watchedOperatingAltitudeTo = watch(
    'data.flight_performance.operating_altitude.to.value',
  );
  useEffect(() => {
    const handleValidation = async () => {
      if (
        watchedOperatingAltitudeFrom != null &&
        watchedOperatingAltitudeTo != null
      ) {
        const minNum = Number(watchedOperatingAltitudeFrom);
        const maxNum = Number(watchedOperatingAltitudeTo);
        if (minNum < maxNum) {
          clearErrors([
            'data.flight_performance.operating_altitude.from.value',
            'data.flight_performance.operating_altitude.to.value',
          ]);
        } else if (minNum == maxNum) {
          await trigger([
            'data.flight_performance.operating_altitude.from.value',
            'data.flight_performance.operating_altitude.to.value',
          ]);
        } else if (minNum > maxNum) {
          await trigger([
            'data.flight_performance.operating_altitude.from.value',
          ]);
        }
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [
    watchedOperatingAltitudeFrom,
    watchedOperatingAltitudeTo,
    clearErrors,
    trigger,
  ]);

  const watchedMaximumTakeoffWeight = watch(
    'data.dimensions.maximum_takeoff_weight.value',
  );
  const watchedEmptyWeight = watch('data.dimensions.empty_weight.value');
  useEffect(() => {
    const handleValidation = async () => {
      if (watchedMaximumTakeoffWeight != null && watchedEmptyWeight != null) {
        const maxNum = Number(watchedMaximumTakeoffWeight);
        const emptyNum = Number(watchedEmptyWeight);
        if (maxNum > emptyNum) {
          clearErrors([
            'data.dimensions.maximum_takeoff_weight.value',
            'data.dimensions.empty_weight.value',
          ]);
        } else if (maxNum == emptyNum) {
          await trigger([
            'data.dimensions.maximum_takeoff_weight.value',
            'data.dimensions.empty_weight.value',
          ]);
        } else if (maxNum < emptyNum) {
          await trigger(['data.dimensions.maximum_takeoff_weight.value']);
        }
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [watchedMaximumTakeoffWeight, watchedEmptyWeight, clearErrors, trigger]);

  return (
    <div className={`technical-specifications ${theme}`}>
      <ExpanDropDown label={t('Physical Specifications')}>
        <div className="technical-specifications__grid-layout">
          <div className="device-size">
            <div className="device-size__label">{t('Frame Size')}</div>
            <div className={`device-size__dimensions ${theme}`}>
              <UnitInput
                name="data.dimensions.frame_size.length.value"
                unit={getValues('data.dimensions.frame_size.length.unit')}
                iconDivider="x"
                placeholder={t('Length')}
                onChange={(e) => {
                  setValue(
                    'data.dimensions.frame_size.length.value',
                    e.target.value,
                  );
                }}
              />
              <UnitInput
                name="data.dimensions.frame_size.width.value"
                unit={getValues('data.dimensions.frame_size.width.unit')}
                iconDivider="x"
                placeholder={t('Width')}
                onChange={(e) => {
                  setValue(
                    'data.dimensions.frame_size.width.value',
                    e.target.value,
                  );
                }}
              />
              <UnitInput
                name="data.dimensions.frame_size.height.value"
                unit={getValues('data.dimensions.frame_size.height.unit')}
                placeholder={t('Height')}
                onChange={(e) => {
                  setValue(
                    'data.dimensions.frame_size.height.value',
                    e.target.value,
                  );
                }}
              />
            </div>
          </div>
          <div>
            <UnitInput
              label={t('Maximum Takeoff Weight (MTOW)')}
              name="data.dimensions.maximum_takeoff_weight.value"
              unit={getValues('data.dimensions.maximum_takeoff_weight.unit')}
              placeholder="0"
              onChange={(e) => {
                setValue(
                  'data.dimensions.maximum_takeoff_weight.value',
                  e.target.value,
                );
              }}
            // value={weight}
            // disabled={isValidWeight}
            />

            {errors?.dimensions?.maximum_takeoff_weight?.value && (
              <div
                style={{
                  color: '#ff4d4f',
                  fontSize: '0.875rem',
                }}
              >
                {errors.dimensions.maximum_takeoff_weight.value.message}
              </div>
            )}
          </div>

          <UnitInput
            label={t('Payload Capacity')}
            name="data.dimensions.payload_capacity.value"
            unit={getValues('data.dimensions.payload_capacity.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.dimensions.payload_capacity.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Empty Weight')}
            type="number"
            name="data.dimensions.empty_weight.value"
            unit={getValues('data.dimensions.empty_weight.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue('data.dimensions.empty_weight.value', e.target.value);
            }}
          />
          <CustomInputHookForm
            label={t('Number of Motors')}
            type="number"
            placeholder="0"
            name="data.propulsion_system.number_of_motors"
          />
          <PaginationSelect
            label={t('Motor Type')}
            name="data.propulsion_system.motor_type_id.value"
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'motortype',
              search_field: 'name',
            })}
            placeholder={t('Select')}
          />
          <UnitInput
            label={t('Motor Power (each)')}
            name="data.propulsion_system.motor_power.value"
            unit={getValues('data.propulsion_system.motor_power.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.propulsion_system.motor_power.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Propeller Size')}
            name="data.propulsion_system.propeller_size.value"
            unit={getValues('data.propulsion_system.propeller_size.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.propulsion_system.propeller_size.value',
                e.target.value,
              );
            }}
          />

          <PaginationSelect
            label={t('Battery Type')}
            name="data.propulsion_system.battery_type_id.value"
            placeholder={t('Select')}
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'batterytype',
              search_field: 'name',
            })}
          />
          <UnitInput
            label={t('Battery Capacity')}
            name="data.propulsion_system.battery_capacity.value"
            unit={getValues('data.propulsion_system.battery_capacity.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.propulsion_system.battery_capacity.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Flight Time')}
            name="data.propulsion_system.flight_time.value"
            unit={getValues('data.propulsion_system.flight_time.unit')}
            placeholder="0"
            isRequired
            preventDecimal
            value={dataFromDeviceId?.drone_max_flight_time}
            onChange={(e) => {
              setValue(
                'data.propulsion_system.flight_time.value',
                e.target.value,
              );
            }}
            disabled={!!dataFromDeviceId?.drone_max_flight_time}
          />
          <UnitInput
            label={t('Charging Time')}
            name="data.propulsion_system.charging_time.value"
            unit={getValues('data.propulsion_system.charging_time.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.propulsion_system.charging_time.value',
                e.target.value,
              );
            }}
          />
          <PaginationSelect
            label={t('Frame Class')}
            name="data.dimensions.frame_class_id.value"
            placeholder={t('Select')}
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'frameclass',
              search_field: 'name',
            })}
          />
          <PaginationSelect
            label={t('Frame Type')}
            name="data.dimensions.frame_type_id.value"
            placeholder={t('Select')}
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'frametype',
              search_field: 'name',
            })}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown label={t('Performance Specifications')}>
        <div className={`performance-grid ${theme}`}>
          <UnitInput
            label={t('Maximum Speed')}
            name="data.flight_performance.maximum_speed.value"
            unit={getValues('data.flight_performance.maximum_speed.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.flight_performance.maximum_speed.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Cruise Speed')}
            name="data.flight_performance.cruise_speed.value"
            unit={getValues('data.flight_performance.cruise_speed.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.flight_performance.cruise_speed.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Maximum Altitude')}
            name="data.flight_performance.maximum_altitude.value"
            unit={getValues('data.flight_performance.maximum_altitude.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.flight_performance.maximum_altitude.value',
                e.target.value,
              );
            }}
          />
          <div className="device-size">
            <div className="device-size__label">{t('Operating Altitude')}</div>
            <div className="d-flex">
              <UnitInput
                name="data.flight_performance.operating_altitude.from.value"
                unit={getValues(
                  'data.flight_performance.operating_altitude.from.unit',
                )}
                placeholder="0"
                onChange={(e) => {
                  setValue(
                    'data.flight_performance.operating_altitude.from.value',
                    e.target.value,
                  );
                }}
                iconDivider={getValues(
                  'data.flight_performance.operating_altitude.icon_device',
                )}
              />
              <UnitInput
                name="data.flight_performance.operating_altitude.to.value"
                unit={getValues(
                  'data.flight_performance.operating_altitude.to.unit',
                )}
                placeholder="0"
                onChange={(e) => {
                  setValue(
                    'data.flight_performance.operating_altitude.to.value',
                    e.target.value,
                  );
                }}
              />
            </div>
          </div>

          <UnitInput
            label={t('Maximum Range')}
            name="data.flight_performance.maximum_range.value"
            unit={getValues('data.flight_performance.maximum_range.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.flight_performance.maximum_range.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Wind Resistance (Up to)')}
            name="data.flight_performance.wind_resistance.value"
            unit={getValues('data.flight_performance.wind_resistance.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.flight_performance.wind_resistance.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('GPS Accuracy (±)')}
            name="data.navigation_control.gps_accuracy.value"
            unit={getValues('data.navigation_control.gps_accuracy.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.navigation_control.gps_accuracy.value',
                e.target.value,
              );
            }}
          />
          <CustomInputHookForm
            label={t('IMU (Inertial Measurement Unit)')}
            placeholder="IMU"
            name="data.navigation_control.imu.value"
            type="number"
          />
          <CustomRadio
            name="data.navigation_control.barometric_altimeter"
            control={control}
            label={t('Barometric Altimeter')}
            options={barometricAltimeterTypeOptions}
            row={true}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown label={t('Communication Systems')}>
        <div className="communication-grid">
          <UnitInput
            label={t('Frequency')}
            name="data.radio_communication.frequency.value"
            unit={getValues('data.radio_communication.frequency.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue(
                'data.radio_communication.frequency.value',
                e.target.value,
              );
            }}
          />
          <UnitInput
            label={t('Range')}
            name="data.radio_communication.range.value"
            unit={getValues('data.radio_communication.range.unit')}
            placeholder="0"
            onChange={(e) => {
              setValue('data.radio_communication.range.value', e.target.value);
            }}
          />
        </div>
        <div className="telemetry-section">
          <CustomTableRadio
            label={t('Telemetry')}
            control={control}
            listItem={telemetryOptions}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown
        label={t('Communication Protocols')}
        className="communication-protocols-form"
      >
        <div className="communication-protocols">
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="protocol-item"
            >
              <div className="protocol-fields">
                <PaginationSelect
                  label={t('Type of Protocol')}
                  name={`data.device_protocols[${index}].type_of_protocol.value`}
                  placeholder={t('Select')}
                  control={control}
                  loadOptions={getOptionsByModel({
                    name_modal: 'protocol',
                    key: 'type',
                    value: 'type',
                    search_field: 'type',
                  })}
                  onChange={(value) => {
                    setValue(
                      `data.device_protocols[${index}].protocol.value`,
                      null,
                    );
                    console.log(
                      'protocal when reset',
                      watch(`data.device_protocols[${index}].protocol.value`),
                    );
                  }}
                />
                <PaginationSelect
                  key={watch(
                    `data.device_protocols[${index}].type_of_protocol.value.value`,
                  )}
                  label={t('Protocol')}
                  name={`data.device_protocols[${index}].protocol.value`}
                  placeholder={t('Select')}
                  control={control}
                  // disabled={
                  //   !watch(
                  //     `data.device_protocols[${index}].type_of_protocol.value`
                  //   )
                  // }
                  disabled={
                    watch(
                      `data.device_protocols[${index}].type_of_protocol.value`,
                    ) === null
                  }
                  loadOptions={getOptionsByModelWithPortal({
                    search_field:
                      watch(
                        `data.device_protocols[${index}].type_of_protocol.value.value`,
                      ) || '',
                    key: 'name',
                    value: 'id',
                  })}
                />
              </div>
              {index > 0 && (
                <div
                  className="remove-button"
                  onClick={() => remove(index)}
                >
                  <AiFillCloseCircle size={16} />
                </div>
              )}
            </div>
          ))}
        </div>
        <CustomBtn
          label={t('Add More')}
          type="button"
          icon={<GoPlus size={18} />}
          className="add-more-button"
          onClick={handleAddMore}
          style={{ display: fields.length >= 10 ? 'none' : 'flex' }}
        />
      </ExpanDropDown>
    </div>
  );
};

export default TechnicalSpecifications;
