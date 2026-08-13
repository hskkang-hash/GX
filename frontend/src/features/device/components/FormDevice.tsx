import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useRef, useState } from 'react';
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
  useConfigSystem,
  useLoadingContext,
  useUserInfo,
} from 'rj-core';
import { v4 as uuidv4 } from 'uuid';

import PickColorInput from '@/components/Form/PickColorInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import {
  schemaDeviceWhenAddNew,
  schemaDeviceWhenEdit,
} from '@/services/schemaForm';
import { convertDeviceDataForEditHaveLibrary } from '@/utils/deviceDataConverter';

import CustomFileInput from '../../../components/Form/CustomFileInput';
import CustomRadio from '../../../components/Form/CustomRadio';
import { Tabs } from '../../../components/Form/Tabs';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import '../formAddNewDevice/FormAddNewDevice.scss';
import Attachments from '../formAddNewDevice/listTabDevice/Attachments';
import PayloadAndSensorSystems from '../formAddNewDevice/listTabDevice/PayloadAndSensorSystems';
import RegulatoryAndOperationalInformation from '../formAddNewDevice/listTabDevice/RegulatoryAndOperationalInformation';
import TechnicalSpecifications from '../formAddNewDevice/listTabDevice/TechnicalSpecifications';
import useAPI from '../useAPI/useAPI';

// Define types for form data
interface FormData {
  data: Record<string, any>;
  avatar: any;
  files: any[];
  dronesData: any;
  remove_files: any;
  delete_avatar: boolean;
  status_id: any;
}

interface FormDeviceProps {
  initialData?: FormData;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  title: string;
  breadcrumbItems: { url?: string; text?: string }[];
  loading: boolean;
  activeTabs?: boolean;
  isEdit?: boolean;
}

export const FormDevice = ({
  initialData,
  activeTabs,
  isEdit,
  onSubmit,
  onCancel,
  loading,
  title,
  breadcrumbItems,
}: FormDeviceProps) => {
  const { t } = useTranslation();
  const usetInfo = useUserInfo();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const isGroupEtri =
    (usetInfo as any)?.profile__group__code === 'group_etri' ? true : false;
  const unitId = uuidv4();

  const { getMainType, getOptionsByModel } = useCommonAPI();
  const [mainTypeOptions, setMainTypeOptions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<number | undefined>(0);
  const formRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { getListTerminalsOptions } = useAPI();
  const [dataDeviceTemplate, setDataDeviceTemplate] = useState<any>(null);

  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem &&
    configSystem['Unit Config'] &&
    configSystem['Unit Config']['unit_preferences'];

  const methods = useForm({
    defaultValues: activeTabs
      ? initialData
        ? initialData
        : {
          data: {
            status_id: null,
            serial_number: 'D-' + new Date().getTime().toString(),
            name: 'D01',
            main_type_id: null,
            color: '#1F2A80',
            note: '',
            group: {
              value: null,
              type: 'select',
            },
            terminal_id: {
              value: null,
              type: 'select',
            },
            unit_id: {
              value: null,
              type: 'select',
            },
            library_id: {
              value: null,
              type: 'select',
            },
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
              frame_class_id: {
                value: null,
                type: 'select',
              },
              frame_type_id: {
                value: null,
                type: 'select',
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
                  unitPreferences?.EnvironmentalSpecification
                    ?.noise_takeoff ||
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
                  unitPreferences?.EnvironmentalSpecification
                    ?.noise_landing ||
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
                    unitPreferences?.CargoCompartments?.dimensions ||
                    unitPreferences?.default?.dimensions ||
                    'mm',
                },
                width: {
                  value: null,
                  unit:
                    unitPreferences?.CargoCompartments?.dimensions ||
                    unitPreferences?.default?.dimensions ||
                    'mm',
                },
                height: {
                  value: null,
                  unit:
                    unitPreferences?.CargoCompartments?.dimensions ||
                    unitPreferences?.default?.dimensions ||
                    'mm',
                },
                icon_device: 'x',
              },
              weight_capacity: {
                value: null,
                unit:
                  unitPreferences?.CargoCompartments?.weight_capacity ||
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
          avatar: null,
          files: [],
          dronesData: null,
          remove_files: null,
          delete_avatar: false,
        }
      : dataDeviceTemplate,
    resolver: yupResolver(
      activeTabs
        ? schemaDeviceWhenEdit(isRoleSuperuser)
        : schemaDeviceWhenAddNew(isRoleSuperuser),
    ),
  });

  const {
    handleSubmit,
    control,
    setValue,
    reset,
    watch,
    trigger,
    formState: { isDirty, isValid, isSubmitting, errors },
  } = methods;
  console.log('watch_data', activeTabs, initialData, watch('data'));

  useEffect(() => {
    if (isGroupEtri && !isEdit) {
      setValue('data.unit_id.value', { value: unitId, label: unitId });
    }
  }, [isGroupEtri]); // eslint-disable-line react-hooks/exhaustive-deps

  const mainTypeId = watch('data.main_type_id');
  useEffect(() => {
    if (mainTypeId && !activeTabs && !isGroupEtri) {
      setValue('data.library_id.value', null);
      setValue('data.unit_id.value', null);
    }
  }, [mainTypeId, setValue, activeTabs, isGroupEtri]);

  // Log when initialData changes
  useEffect(() => {
    console.log('initialData changed:', initialData);
    if (initialData && activeTabs) {
      showLoading();
      console.log('Resetting form with initialData');

      // Lưu status_id hiện tại trước khi reset
      const currentStatusId = watch('data.status_id');
      console.log('Current status_id before reset:', currentStatusId);

      // Reset form
      reset(initialData);

      // Đảm bảo status_id được giữ nguyên hoặc set từ initialData
      let finalStatusId = currentStatusId; // Giữ giá trị hiện tại

      if (initialData?.status_id !== undefined) {
        finalStatusId = initialData.status_id;
        console.log('Using status_id from initialData:', finalStatusId);
      } else if (initialData?.data?.status_id !== undefined) {
        finalStatusId = initialData.data.status_id;
        console.log('Using status_id from initialData.data:', finalStatusId);
      }

      // Set status_id sau khi reset
      if (finalStatusId !== undefined) {
        console.log('Setting final status_id:', finalStatusId);
        setValue('data.status_id', finalStatusId);
      }

      hideLoading();
    }
  }, [initialData, activeTabs, reset, setValue, watch]);

  useEffect(() => {
    console.log('methods_error', methods.formState.errors);
    console.log('Form values:', methods.getValues());
  }, [methods]);

  useEffect(() => {
    if (dataDeviceTemplate && !activeTabs) {
      console.log('Resetting with template data:', dataDeviceTemplate);
      reset(dataDeviceTemplate);
      setIsTemplateLoaded(true);
      setTimeout(() => {
        const currentData = watch();
        setValue('data.name', currentData.data.name, { shouldDirty: true });
      }, 100);
    }
  }, [dataDeviceTemplate, activeTabs, reset, setValue, watch]);

  useEffect(() => {
    const currentColor = watch('data.color');
    if (!currentColor && !activeTabs) {
      setValue('data.color', '#1F2A80');
    }
  }, [watch('data.color'), activeTabs, setValue]);

  // Đảm bảo status_id không bị mất sau khi form được reset
  useEffect(() => {
    const currentStatusId = watch('data.status_id');
    console.log('status_id changed to:', currentStatusId);

    // Nếu status_id bị undefined và chúng ta đang ở edit mode
    if (currentStatusId === undefined && activeTabs && initialData) {
      console.log('status_id became undefined, restoring from initialData');

      let restoreStatusId = null;
      if (initialData?.status_id !== undefined) {
        restoreStatusId = initialData.status_id;
      } else if (initialData?.data?.status_id !== undefined) {
        restoreStatusId = initialData.data.status_id;
      }

      if (restoreStatusId !== null) {
        console.log('Restoring status_id to:', restoreStatusId);
        setValue('data.status_id', restoreStatusId);
      }
    }
  }, [watch('data.status_id'), activeTabs, initialData, setValue]);

  console.log('data_getDataDeviceTemplateById_@', dataDeviceTemplate);

  const [clickSave, setClickSave] = useState(false);
  const [isTemplateLoaded, setIsTemplateLoaded] = useState(false);
  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    try {
      await onSubmit(data);
      // reset(data, {
      //   keepDirty: false,
      //   keepValues: false,
      // });
      setIsTemplateLoaded(false);
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };

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

  // Function to check which tab contains errors and navigate to it
  const navigateToTabWithErrors = (errors: Record<string, any>) => {
    const errorFields = Object.keys(errors?.data || errors || {});
    console.log('errorFields234234', errorFields);
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
    ...(!isGroupEtri
      ? [
        {
          label: t('Regulatory and Operational Information'),
          content: <RegulatoryAndOperationalInformation />,
        },
      ]
      : []),
    {
      label: t('Attachments'),
      content: <Attachments />,
    },
  ];
  const handleAvatarRemove = () => {
    setValue('avatar', null);
    setValue('delete_avatar', true);
  };
  const { getDrones, getDataDeviceTemplateById } = useAPI();

  const deviceTemplateId = watch('data.library_id.value')?.value;

  console.log('deviceTemplateId', deviceTemplateId);
  const currentData = watch();
  console.log({ currentData });
  const LibararyName = watch('data.library_id.value')?.label;
  console.log('LibararyName', LibararyName);
  const primaryData = {
    serial_number: 'D-' + new Date().getTime().toString(),
    name: 'D01',
    active: currentData?.data?.active || true,
    main_type_id: currentData?.data?.main_type_id,
    sub_type: currentData?.data?.sub_type || '',
    note: currentData?.data?.note || '',
    color: currentData?.data?.color || '#1F2A80',
    unit_id: currentData?.data?.unit_id?.value?.value,
    library_id: currentData?.data?.library_id?.value?.value,
    library_name: LibararyName,
    avatar: currentData?.avatar || null,
    group: currentData?.data?.group?.value || null,
  };
  console.log('primaryData', primaryData);

  // setInitialData(convertDeviceDataForEdit(data));
  console.log({ primaryData });

  const { showLoading, hideLoading } = useLoadingContext();
  useEffect(() => {
    if (primaryData && deviceTemplateId && !isEdit) {
      // setLoadingDrone(true);
      const getDetailDron = async () => {
        showLoading();
        const { data, success, message } =
          await getDataDeviceTemplateById(deviceTemplateId);
        if (success) {
          hideLoading();
          console.log('data_getDataDeviceTemplateById', data);
          setDataDeviceTemplate(
            convertDeviceDataForEditHaveLibrary(
              data,
              primaryData,
              isRoleSuperuser,
            ),
          );
        } else {
          hideLoading();
          ToastTopHelper.error(message);
        }
      };
      getDetailDron();
    }

    getDrones();
  }, [deviceTemplateId]);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty:
        (clickSave == false && isDirty) || (isTemplateLoaded && !clickSave),
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
        setIsTemplateLoaded(false);
      },
      onError,
      onCancel: () => { },
      handleSubmit,
    });

  console.log('form_data', watch());
  console.log('form_errors', errors);
  console.log('form_isDirty', isDirty);
  console.log('form_isSubmitting', isSubmitting);
  console.log('form_isValid', isValid);

  console.log('form_errors_device_id', errors?.data?.unit_id?.value?.message);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        className="form-add-new-device"
      >
        <CustomBreadcrumb
          items={breadcrumbItems}
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
              loading={isSubmitting}
              type="submit"
              disabled={
                loading ||
                !watch('data.library_id.value') ||
                !watch('data.unit_id.value')?.value ||
                !watch('data.color') ||
                !watch('data.terminal_id')?.value?.value ||
                !watch('data.name') ||
                (isRoleSuperuser && !watch('data.group.value')?.value) ||
                (activeTabs &&
                  (!isValid ||
                    !isDirty ||
                    !watch('data.library_id.value') ||
                    !watch('data.unit_id')?.value))
              }
            />,
          ]}
        />
        <Main>
          <div
            className="form-container"
            ref={formRef}
          >
            <FormBlock>
              <div className="form-grid">
                {isRoleSuperuser && (
                  <div className="grid-span-full">
                    <PaginationSelect
                      name="data.group.value"
                      label={t('Group')}
                      required
                      control={control}
                      placeholder={t('Select')}
                      loadOptions={getOptionsByModel({
                        name_modal: 'usergroup',
                        search_field: 'name',
                        key: 'name',
                        value: 'id',
                      })}
                      className="flex-fill"
                    />
                  </div>
                )}
                <CustomInputHookForm
                  required
                  name="data.name"
                  label="Name"
                />
                <CustomFileInput
                  name="avatar"
                  control={control}
                  label={t('Image')}
                  onFileRemove={handleAvatarRemove}
                />
                <div className="form-actions">
                  <CustomRadio
                    required
                    name="data.main_type_id"
                    control={control}
                    label={t('Type')}
                    options={mainTypeOptions}
                    row={true}
                    disabled={initialData?.data?.main_type_id}
                  />
                </div>
                <PaginationSelect
                  label={t('Device Template')}
                  name="data.library_id.value"
                  placeholder={t('Select')}
                  required
                  disabled={initialData?.data?.library_id?.value?.value}
                  control={control}
                  loadOptions={
                    getOptionsByModel({
                      name_modal: 'Library',
                      search_field: 'name',
                      key: 'name',
                      value: 'id',
                    }) as any
                  }
                />
                <PaginationSelect
                  label={t('Device ID')}
                  name="data.unit_id.value"
                  placeholder={t('Select')}
                  required
                  disabled={
                    isGroupEtri || initialData?.data?.unit_id?.value?.value
                  }
                  control={control}
                  loadOptions={getDrones()}
                />
                <PickColorInput
                  name="data.color"
                  value={watch('data.color')}
                  label={t('Color')}
                  isRequired
                />
                <PaginationSelect
                  label={t('Linked Terminal')}
                  name="data.terminal_id.value"
                  required
                  placeholder={t('Select')}
                  // disabled={initialData?.data?.terminal_id?.value?.value}
                  control={control}
                  loadOptions={getListTerminalsOptions()}
                />
                <CustomInputHookForm
                  name="data.note"
                  placeholder={t('Note')}
                  label={t('Note')}
                />
              </div>
            </FormBlock>
            {activeTabs && (
              <Tabs
                items={listTabs}
                activeTab={activeTab}
                onTabChange={setActiveTab}
              />
            )}
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
              disabled={loading}
              loading={isSubmitting}
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

export default FormDevice;
