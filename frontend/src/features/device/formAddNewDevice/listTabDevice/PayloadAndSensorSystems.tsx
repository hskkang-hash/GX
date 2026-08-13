import { useFieldArray, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { AiFillCloseCircle } from 'react-icons/ai';
import { GoPlus } from 'react-icons/go';
import { IoTrashOutline } from 'react-icons/io5';
import { CustomBtn, useTheme } from 'rj-core';

import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';

import CustomTableRadio from '../../../../components/Form/CustomTableRadio';
import ExpanDropDown from '../../../../components/Form/ExpanDropDown';
import UnitInput from '../../../../components/Form/UnitInput';
import Colors from '../../../../configs/Colors';
import './PayloadAndSensorSystems.scss';

const PayloadAndSensorSystems = () => {
  const {
    control,
    watch,
    setValue,
    getValues,
    formState: { errors },
  } = useFormContext();

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'data.packaging_specifications',
  });

  const { getOptionsByModel } = useCommonAPI();

  const {
    fields: surveillanceFields,
    append: appendSurveillance,
    remove: removeSurveillance,
  } = useFieldArray({
    control,
    name: 'data.surveillance_systems',
  });

  console.log(
    "watch('data.packaging_specifications')",
    watch('data.packaging_specifications'),
  );

  const handleAddMoreOption = (indexOption: number) => {
    if (fields.length < 5) {
      append({
        specifications: [{ value: null, type: 'select' }],
        name: `Option ${indexOption + 1}`,
        order: indexOption,
      });
    }
  };

  const updateOptionOrder = () => {
    const currentFields = getValues('data.packaging_specifications');
    const updatedFields = currentFields.map((field: any, index: number) => ({
      ...field,
      name: `Option ${index + 1}`,
      order: index,
    }));
    setValue('data.packaging_specifications', updatedFields);
  };

  const handleRemoveOption = (index: number) => {
    remove(index);
    updateOptionOrder();
  };

  const handleAddMorePacking = (indexOption: number) => {
    const currentPacking =
      watch(`data.packaging_specifications[${indexOption}].specifications`) ||
      [];
    setValue(`data.packaging_specifications[${indexOption}].specifications`, [
      ...currentPacking,
      { value: null, type: 'select' },
    ]);
  };

  const handleAddMoreSurveillance = () => {
    if (surveillanceFields.length < 6) {
      appendSurveillance({
        value: null,
        type: 'select',
      });
    }
  };

  const { t } = useTranslation();
  const [theme, _] = useTheme();

  const payloadSystemOptions = [
    {
      name: 'data.cargo_compartments.temperature_control',
      value: 'Temperature Control',
      label: t('Temperature Control'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.cargo_compartments.secure_locking',
      value: 'Secure locking mechanism',
      label: t('Secure locking mechanism'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.cargo_compartments.quick_release',
      value: 'Quick-release system',
      label: t('Quick-release system'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
  ];

  const sensorSuiteOptions = [
    {
      name: 'data.sensor_suite.optical_flow_sensor',
      value: 'Optical Flow Sensor',
      label: t('Optical Flow Sensor'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.ultrasonic_sensors',
      value: 'Ultrasonic Sensors',
      label: t('Ultrasonic Sensors'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.lidar',
      value: 'LIDAR for obstacle detection',
      label: t('LIDAR for obstacle detection'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.ais',
      value: 'AIS (Automatic Identification System)',
      label: t('AIS (Automatic Identification System)'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.ads_b_receiver',
      value: 'ADS-B receiver',
      label: t('ADS-B receiver'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.rf_signal_detector',
      value: 'RF signal detector',
      label: t('RF signal detector'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.chemical_sensor_array',
      value: 'Chemical sensor array',
      label: t('Chemical sensor array'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.radiation_detector',
      value: 'Radiation detector',
      label: t('Radiation detector'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
    {
      name: 'data.sensor_suite.weather_sensors',
      value: 'Weather sensors',
      label: t('Weather sensors'),
      option: [
        { value: true, label: 'Yes' },
        { value: false, label: 'No' },
      ],
    },
  ];

  console.log(
    'data.sensor_suite.gnss.value',
    watch('data.sensor_suite.gnss.value'),
  );

  return (
    <div className={`payload-and-sensor-systems ${theme}`}>
      <ExpanDropDown label={t('Payload Systems')}>
        <div className="grid-container">
          <div className="device-size">
            <div className="device-size__label">
              {t('Dimensions')} <span style={{ color: Colors.Red }}>*</span>
            </div>
            <div className={`device-size__dimensions ${theme}`}>
              <UnitInput
                name="data.cargo_compartments.dimensions.length.value"
                unit={getValues(
                  'data.cargo_compartments.dimensions.length.unit',
                )}
                iconDivider="x"
                placeholder={t('Length')}
                paddingError={errors.data?.cargo_compartments?.dimensions}
                isPadding
              />
              <UnitInput
                name="data.cargo_compartments.dimensions.width.value"
                unit={getValues(
                  'data.cargo_compartments.dimensions.width.unit',
                )}
                iconDivider="x"
                placeholder={t('Width')}
                paddingError={errors.data?.cargo_compartments?.dimensions}
                isPadding
              />
              <UnitInput
                name="data.cargo_compartments.dimensions.height.value"
                unit={getValues(
                  'data.cargo_compartments.dimensions.height.unit',
                )}
                placeholder={t('Height')}
                paddingError={errors.data?.cargo_compartments?.dimensions}
                isPadding
              />
            </div>
          </div>
          <UnitInput
            label={t('Weight Capacity')}
            isRequired
            name="data.cargo_compartments.weight_capacity.value"
            unit={getValues('data.cargo_compartments.weight_capacity.unit')}
            placeholder="0"
          />
        </div>
        <div className="flex flex-col gap-4">
          <CustomTableRadio
            control={control}
            listItem={payloadSystemOptions}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown label={t('Packaging Specifications')}>
        <div className="packaging-specifications">
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="option-container d-flex"
            >
              <ExpanDropDown
                label={`Option ${index + 1}`}
                backgroundColor={
                  theme === 'dark'
                    ? 'var(--ga-dark-bg-accordion)'
                    : 'var(--ga-light-bg-accordion)'
                }
                lableSize={'1rem'}
              >
                <div className="relative">
                  {index > 0 && (
                    <div
                      className="remove-icon-option mt-1 ms-auto"
                      onClick={() => handleRemoveOption(index)}
                    >
                      <IoTrashOutline
                        color={`${
                          theme === 'dark'
                            ? 'var(--ga-dark-theme-font-color)'
                            : 'var( --ga-light-theme-font-color)'
                        }`}
                        size={16}
                      />
                    </div>
                  )}
                  <div className="packaging-specifications__layout">
                    {watch(
                      `data.packaging_specifications[${index}].specifications`,
                    )?.map((_, packingIndex) => (
                      <div
                        key={packingIndex}
                        className="packing-item"
                      >
                        <div className="packing-input">
                          <PaginationSelect
                            label={t('Packaging')}
                            name={`data.packaging_specifications[${index}].specifications[${packingIndex}].value`}
                            placeholder={t('Select')}
                            control={control}
                            required
                            maxValue={5}
                            loadOptions={getOptionsByModel({
                              name_modal: 'packagingspecification',
                              search_field: 'name',
                            })}
                          />
                        </div>
                        {packingIndex > 0 && (
                          <div
                            className="remove-icon"
                            onClick={() => {
                              const currentPacking = watch(
                                `data.packaging_specifications[${index}].specifications`,
                              );
                              const newPacking = currentPacking.filter(
                                (_, i) => i !== packingIndex,
                              );
                              setValue(
                                `data.packaging_specifications[${index}].specifications`,
                                newPacking,
                              );
                            }}
                          >
                            <AiFillCloseCircle size={16} />
                          </div>
                        )}
                      </div>
                    ))}

                    <CustomBtn
                      label={t('Add More')}
                      type="button"
                      variant="outline"
                      style={{ color: 'var(--ga-primary)' }}
                      icon={<GoPlus size={18} />}
                      className="add-more-button"
                      onClick={() => handleAddMorePacking(index)}
                    />
                  </div>
                </div>
              </ExpanDropDown>
            </div>
          ))}
          <CustomBtn
            label={t('Add More')}
            type="button"
            variant="outline"
            style={{ color: 'var(--ga-primary)' }}
            icon={<GoPlus size={18} />}
            className="add-more-button"
            onClick={() => handleAddMoreOption(fields.length)}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown label={t('Surveillance Systems')}>
        <div className="surveillance-systems">
          {surveillanceFields.map((field, index) => (
            <div
              key={field.id}
              className="surveillance-item"
            >
              <div className="surveillance-input">
                <PaginationSelect
                  label={t('Camera')}
                  name={`data.surveillance_systems[${index}].value`}
                  placeholder={t('Select type')}
                  control={control}
                  loadOptions={getOptionsByModel({
                    name_modal: 'cameraType',
                  })}
                />
              </div>
              {index > 0 && (
                <div
                  className="remove-icon"
                  onClick={() => removeSurveillance(index)}
                >
                  <AiFillCloseCircle size={16} />
                </div>
              )}
            </div>
          ))}
          <CustomBtn
            label={t('Add More')}
            type="button"
            variant="outline"
            style={{
              color: 'var(--ga-primary)',
              display: surveillanceFields.length == 5 ? 'none' : 'flex',
            }}
            icon={<GoPlus size={18} />}
            className="add-more-button"
            onClick={handleAddMoreSurveillance}
          />
        </div>
      </ExpanDropDown>
      <ExpanDropDown
        label={t('Sensor Suite')}
        className="sensor-suite-form"
      >
        <div className="sensor-suite">
          <PaginationSelect
            label={t('GNSS')}
            name="data.sensor_suite.gnss.value"
            placeholder={t('Select')}
            control={control}
            isMulti
            maxValue={5}
            loadOptions={getOptionsByModel({
              name_modal: 'gnsssystem',
              key: 'name',
              search_field: 'name',
            })}
            description={t('You can select up to 5 items only.')}
          />

          <CustomTableRadio
            label={t('Sensor')}
            control={control}
            listItem={sensorSuiteOptions}
          />
        </div>
      </ExpanDropDown>
    </div>
  );
};

export default PayloadAndSensorSystems;
