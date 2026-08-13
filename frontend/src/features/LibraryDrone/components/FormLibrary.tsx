import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useRef, useState } from 'react';
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
  useConfigSystem,
  useLoadingContext,
} from 'rj-core';
import CustomCheckBox from '@/components/Form/CustomCheckBox';
import LoadingModal from '@/components/modal/LoadingModal';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaLibrary } from '@/services/schemaForm';

import CustomFileInput from '../../../components/Form/CustomFileInput';
import CustomRadio from '../../../components/Form/CustomRadio';
import { Tabs } from '../../../components/Form/Tabs';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import '../add/FormAddNewLibrary.scss';
import { FormData, FormLibraryProps } from '../type';
import Attachments from './listTabDevice/Attachments';
import PayloadAndSensorSystems from './listTabDevice/PayloadAndSensorSystems';
import RegulatoryAndOperationalInformation from './listTabDevice/RegulatoryAndOperationalInformation';
import TechnicalSpecifications from './listTabDevice/TechnicalSpecifications';

const FormLibrary = ({
  initialData,
  onSubmit,
  onCancel,
  loading,
  breadcrumbItems,
}: FormLibraryProps) => {
  const { t } = useTranslation();
  const { getMainType, getOptionsByModel } = useCommonAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [mainTypeOptions, setMainTypeOptions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<number | undefined>(0);
  const formRef = useRef<HTMLDivElement>(null);

  const [configSystem] = useConfigSystem();
  const unitPreferences =
    (configSystem &&
      configSystem['Unit Config']) ?
      configSystem['Unit Config']['unit_preferences'] : null;

  console.log('unitPreferences', unitPreferences);


  const methods = useForm<FormData>({
    defaultValues: initialData
      ? initialData
      : {
        data: {
          name: '',
          main_type_id: null,
          group: null,
          description: '',
          active: true,
          dimensions: {
            frame_size: {
              length: {
                value: null,
                unit:
                  unitPreferences?.DimensionsAndWeight?.frame_size ||
                  unitPreferences?.default?.frame_size ||
                  'mm',
              },
              width: {
                value: null,
                unit:
                  unitPreferences?.DimensionsAndWeight?.frame_size ||
                  unitPreferences?.default?.frame_size ||
                  'mm',
              },
              height: {
                value: null,
                unit:
                  unitPreferences?.DimensionsAndWeight?.frame_size ||
                  unitPreferences?.default?.frame_size ||
                  'mm',
              },
              icon_device: 'x',
            },
            frame_class_id: {
              value: null,
              type: 'select',
            },
            frame_type_id: {
              value: null,
              type: 'select',
            },
            maximum_takeoff_weight: {
              value: null,
              unit:
                unitPreferences?.DimensionsAndWeight
                  ?.maximum_takeoff_weight ||
                unitPreferences?.default?.maximum_takeoff_weight ||
                'kg',
            },
            payload_capacity: {
              value: null,
              unit:
                unitPreferences?.DimensionsAndWeight?.payload_capacity ||
                unitPreferences?.default?.payload_capacity ||
                'kg',
            },
            empty_weight: {
              value: null,
              unit:
                unitPreferences?.DimensionsAndWeight?.empty_weight ||
                unitPreferences?.default?.empty_weight ||
                'kg',
            },
          },
          propulsion_system: {
            number_of_motors: null,
            motor_type_id: {
              value: null,
              type: 'select',
            },
            battery_type_id: {
              value: null,
              type: 'select',
            },
            flight_time: {
              value: null,
              unit:
                unitPreferences?.PropulsionSystem?.flight_time ||
                unitPreferences?.default?.flight_time ||
                'minutes',
            },
            charging_time: {
              value: null,
              unit:
                unitPreferences?.PropulsionSystem?.charging_time ||
                unitPreferences?.default?.charging_time ||
                'minutes',
            },
            motor_power: {
              value: null,
              unit:
                unitPreferences?.PropulsionSystem?.motor_power ||
                unitPreferences?.default?.motor_power ||
                'kW',
            },
            propeller_size: {
              value: null,
              unit:
                unitPreferences?.PropulsionSystem?.propeller_size ||
                unitPreferences?.default?.propeller_size ||
                'inch',
            },
            battery_capacity: {
              value: null,
              unit:
                unitPreferences?.PropulsionSystem?.battery_capacity ||
                unitPreferences?.default?.battery_capacity ||
                'mAh',
            },
          },
          flight_performance: {
            maximum_speed: {
              value: null,
              unit:
                unitPreferences?.FlightPerformance?.maximum_speed ||
                unitPreferences?.default?.maximum_speed ||
                'km/h',
            },
            cruise_speed: {
              value: null,
              unit:
                unitPreferences?.FlightPerformance?.cruise_speed ||
                unitPreferences?.default?.cruise_speed ||
                'km/h',
            },
            maximum_altitude: {
              value: null,
              unit:
                unitPreferences?.FlightPerformance?.maximum_altitude ||
                unitPreferences?.default?.maximum_altitude ||
                'm',
            },
            operating_altitude: {
              from: {
                value: null,
                unit:
                  unitPreferences?.FlightPerformance?.operating_altitude ||
                  unitPreferences?.default?.operating_altitude ||
                  'm',
              },
              to: {
                value: null,
                unit:
                  unitPreferences?.FlightPerformance?.operating_altitude ||
                  unitPreferences?.default?.operating_altitude ||
                  'm',
              },
              icon_device: '-',
              unit:
                unitPreferences?.FlightPerformance?.operating_altitude ||
                unitPreferences?.default?.operating_altitude ||
                'm',
            },
            maximum_range: {
              value: null,
              unit:
                unitPreferences?.FlightPerformance?.maximum_range ||
                unitPreferences?.default?.maximum_range ||
                'km',
            },
            wind_resistance: {
              value: null,
              unit:
                unitPreferences?.FlightPerformance?.wind_resistance ||
                unitPreferences?.default?.wind_resistance ||
                'km/h',
            },
          },
          navigation_control: {
            barometric_altimeter: true,
            imu: null,
            gps_accuracy: {
              value: null,
              unit:
                unitPreferences?.NavigationControl?.gps_accuracy ||
                unitPreferences?.default?.gps_accuracy ||
                'm',
              icon_device: '±',
            },
          },
          radio_communication: {
            frequency: {
              value: null,
              unit:
                unitPreferences?.RadioCommunication?.frequency ||
                unitPreferences?.default?.frequency ||
                'GHz',
            },
            range: {
              value: null,
              unit:
                unitPreferences?.RadioCommunication?.range ||
                unitPreferences?.default?.range ||
                'km',
            },
          },
          telemetry: {
            realtime_flight_data: true,
            video_streaming: true,
            battery_status_monitoring: true,
            gps_position_tracking: true,
            system_health_monitoring: true,
          },
          sensor_suite: {
            gnss: {
              value: null,
              type: 'select',
            },
            optical_flow_sensor: true,
            ultrasonic_sensors: true,
            lidar: true,
            ais: true,
            ads_b_receiver: true,
            rf_signal_detector: true,
            chemical_sensor_array: true,
            radiation_detector: true,
            weather_sensors: true,
          },
          manufacturer_information: {
            manufacturer: '',
            country_of_origin_id: {
              value: null,
              type: 'select',
            },
            contact_information: '',
            insurance_type: '',
            insurance_provider: '',
            policy_number: '',
            validity_period_from: '',
            validity_period_to: '',
            current_status: 'active',
            serial_number: '',
            model_number: '',
            production_date: null,
            insurance_status: false,
            registration_number: '',
          },
          environmental_specification: {
            temperature_range: {
              length: {
                value: null,
                unit:
                  unitPreferences?.EnvironmentalSpecification
                    ?.temperature_range ||
                  unitPreferences?.default?.temperature_range ||
                  '°C',
              },
              width: {
                value: null,
                unit:
                  unitPreferences?.EnvironmentalSpecification
                    ?.temperature_range ||
                  unitPreferences?.default?.temperature_range ||
                  '°C',
              },
              icon_device: 'to',
            },
            humidity: {
              value: [0, 0],
              unit:
                unitPreferences?.EnvironmentalSpecification?.humidity ||
                unitPreferences?.default?.humidity ||
                '%',
            },
            precipitation: '',
            wind_speed: {
              value: null,
              unit:
                unitPreferences?.EnvironmentalSpecification?.wind_speed ||
                unitPreferences?.default?.wind_speed ||
                'km/h',
            },
            noise_takeoff: {
              value: null,
              unit:
                unitPreferences?.EnvironmentalSpecification?.noise_takeoff ||
                unitPreferences?.default?.noise_takeoff ||
                'dB',
            },
            noise_cruise: {
              value: null,
              unit:
                unitPreferences?.EnvironmentalSpecification?.noise_cruise ||
                unitPreferences?.default?.noise_cruise ||
                'dB',
            },
            noise_landing: {
              value: null,
              unit:
                unitPreferences?.EnvironmentalSpecification?.noise_landing ||
                unitPreferences?.default?.noise_landing ||
                'dB',
            },
          },
          safety_feature: {
            dual_imu: true,
            dual_gps: true,
            dual_battery: true,
            emergency_parachute: true,
            return_to_home: true,
            obstacle_detection_360: true,
            stereo_cameras: true,
            lidar_mapping: true,
            emergency_braking: true,
          },
          cargo_compartments: {
            secure_locking: true,
            quick_release: true,
            temperature_control: true,
            dimensions: {
              length: {
                value: null,
                unit:
                  unitPreferences?.SafetyFeature?.dimensions ||
                  unitPreferences?.default?.dimensions ||
                  'mm',
              },
              width: {
                value: null,
                unit:
                  unitPreferences?.SafetyFeature?.dimensions ||
                  unitPreferences?.default?.dimensions ||
                  'mm',
              },
              height: {
                value: null,
                unit:
                  unitPreferences?.SafetyFeature?.dimensions ||
                  unitPreferences?.default?.dimensions ||
                  'mm',
              },
              icon_device: 'x',
            },
            weight_capacity: {
              value: null,
              unit:
                unitPreferences?.SafetyFeature?.weight_capacity ||
                unitPreferences?.default?.weight_capacity ||
                'kg',
            },
          },
          device_protocols: [
            {
              type_of_protocol: {
                value: null,
                type: 'select',
              },
              protocol: {
                value: null,
                type: 'select',
              },
            },
          ],
          packaging_specifications: [
            {
              specifications: [{ value: null, type: 'select' }],
              name: `Option 1`,
              order: 0,
            },
          ],
          surveillance_systems: [
            {
              value: null,
              type: 'select',
            },
          ],
        },
      },
    resolver: yupResolver(schemaLibrary(isRoleSuperuser)) as any,
  });
  const {
    handleSubmit,
    control,
    setValue,
    reset,
    watch,
    formState: { isSubmitting, isValid, isDirty, errors },
  } = methods;

  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
  }, [initialData, reset]);

  const [clickSave, setClickSave] = useState(false);
  const [loadingForm, setLoadingForm] = useState(false);

  // Function to check which tab contains errors and navigate to it
  const navigateToTabWithErrors = (errors: Record<string, any>) => {
    const errorFields = Object.keys(errors?.data || errors || {});
    // Map error fields to tab indices
    if (
      errorFields.some((field) =>
        [
          'main_type_id',
          'dimensions',
          'propulsion_system',
          'flight_performance',
          'navigation_control',
          'radio_communication',
        ].includes(field),
      )
    ) {
      setActiveTab(0); // Technical Specifications
    } else if (
      errorFields.some((field) =>
        [
          'telemetry',
          'sensor_suite',
          'cargo_compartments',
          'packaging_specifications',
        ].includes(field),
      )
    ) {
      setActiveTab(1); // Payload and Sensor Systems
    } else if (
      errorFields.some((field) =>
        [
          'environmental_specification',
          'safety_feature',
          'manufacturer_information',
        ].includes(field),
      )
    ) {
      setActiveTab(2); // Regulatory and Operational Information
    } else if (
      errorFields.some((field) => ['avatar', 'files'].includes(field))
    ) {
      setActiveTab(3); // Attachments
    }

    // Scroll to form
    setTimeout(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const onError = (errors: Record<string, any>) => {
    // Navigate to the tab with errors
    navigateToTabWithErrors(errors);
    ToastTopHelper.error(t('Please fill in all required fields'));
    return true;
  };

  const listTabs = [
    {
      label: t('Technical Specifications'),
      content: <TechnicalSpecifications />,
    },
    {
      label: t('Payload and Sensor Systems'),
      content: <PayloadAndSensorSystems />,
    },
    {
      label: t('Regulatory and Operational Information'),
      content: <RegulatoryAndOperationalInformation />,
    },
    {
      label: t('Attachments'),
      content: <Attachments />,
    },
  ];
  const handleAvatarRemove = (type: any) => {
    setValue('remove_avatar', type);
  };

  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    setLoadingForm(true);
    console.log('form_library_dataaaaaaaaaaaaaaaaaaaaaaa', data);
    try {
      const res = await onSubmit(data);
      console.log('res_324', res);
      reset(data, {
        keepDirty: false,
        keepValues: true,
      });
    } catch (error) {
      console.error('Error saving form:', error);
    } finally {
      setLoadingForm(false);
    }
  };

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
      onError,
      onCancel,
      handleSubmit,
    });

  const handleGetDataForForm = async () => {
    if (mainTypeOptions.length === 0) {
      const { data: dataMainType } = await getMainType();
      setMainTypeOptions(dataMainType);
      if (dataMainType.length > 0 && !initialData) {
        setValue('data.main_type_id', dataMainType[0]?.value);
      }
    }
  };
  useEffect(() => {
    handleGetDataForForm();
  }, []);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        className="form-add-new-device"
      >
        <CustomBreadcrumb
          items={breadcrumbItems || []}
          buttons={[
            <CustomBtn
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={onCancel}
            />,
            <CustomBtn
              size="md"
              style={{ width: '6rem' }}
              label={t('Save')}
              actionType={
                location.pathname.includes('edit')
                  ? ROLE_PERMISSION.UPDATE
                  : ROLE_PERMISSION.CREATE
              }
              type="submit"
              loading={isSubmitting}
              disabled={loading || !isValid || !isDirty}
            />,
          ]}
        />
        <Main>
          <div
            className="form-container"
            ref={formRef}
          >
            <FormBlock className="d-flex flex-column gap-3">
              <div className="form-grid">
                <CustomInputHookForm
                  name="data.name"
                  label={t('Name')}
                  placeholder={t('Name')}
                  required
                />
                <div className={isRoleSuperuser ? 'form-grid' : 'd-flex'}>
                  {isRoleSuperuser && (
                    <div>
                      <PaginationSelect
                        label={t('Group')}
                        name="data.group"
                        placeholder={t('Select')}
                        control={control}
                        loadOptions={getOptionsByModel({
                          name_modal: 'usergroup',
                          search_field: 'name',
                          key: 'name',
                          value: 'id',
                        })}
                        required
                      />
                    </div>
                  )}
                  <div
                    className={` ${isRoleSuperuser ? 'form-grid-8-2' : 'form-grid-full'}`}
                  >
                    <CustomRadio
                      required
                      name="data.main_type_id"
                      control={control}
                      label={t('Type')}
                      options={mainTypeOptions}
                      row={true}
                    />
                    <CustomCheckBox
                      name={'data.active'}
                      label={t('Active')}
                      subLabel={t('Yes')}
                      control={control}
                    />
                  </div>
                </div>
                {/* <PaginationSelect
                  label={t("Group")}
                  name="data.group"
                  placeholder={t("Select")}
                  control={control}
                  isMulti={true}
                  loadOptions={getOptionsByModel({
                    name_modal: "usergroup",
                  })}
                  required
                /> */}
                <CustomFileInput
                  name="avatar"
                  control={control}
                  label={t('Image')}
                  onFileRemove={handleAvatarRemove}
                  showNoImage={true}
                />
                <CustomInputHookForm
                  name="data.note"
                  placeholder={t('Note')}
                  label={t('Note')}
                />
              </div>
            </FormBlock>
            <Tabs
              items={listTabs}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />
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
              type="submit"
              color="primary"
              size="lg"
              onClick={handleModalSave}
              label={t('Save')}
              loading={isSubmitting}
              disabled={loading}
            />,
          ]}
          rightButtons={[
            <CustomBtn
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

export default FormLibrary;
