import dayjs from 'dayjs';

const removeNullAndEmptyValuesDeep = (obj: any): any => {
  if (Array.isArray(obj)) {
    return obj
      .map(removeNullAndEmptyValuesDeep)
      .filter(
        (item) =>
          item !== null &&
          item !== '' &&
          (typeof item !== 'object' || Object.keys(item).length > 0),
      );
  }

  if (typeof obj === 'object' && obj !== null) {
    return Object.entries(obj).reduce((acc, [key, value]) => {
      const cleanedValue = removeNullAndEmptyValuesDeep(value);
      if (
        cleanedValue !== null &&
        cleanedValue !== '' &&
        (typeof cleanedValue !== 'object' ||
          Object.keys(cleanedValue).length > 0)
      ) {
        acc[key] = cleanedValue;
      }
      return acc;
    }, {} as any);
  }

  return obj === null || obj === '' ? null : obj;
};


export const convertLibraryData = (
  sourceData: any,
  isRoleSuperuser: boolean = false,
  convertDateFormatToYYYYMMDD: any,
  convertDateToUTCStartOfDay: any,
  convertDateToUTCEndOfDay: any,
) => {
  if (!sourceData || !sourceData.data) return null;
  const data = sourceData.data;

  // Helper function to format value with unit
  const formatWithUnit = (obj: any) => {
    if (!obj) return null;
    return obj.value != null && obj.unit != null
      ? `${obj.value} ${obj.unit}`
      : null;
  };

  // Helper function to get ID value from select object
  const getSelectValue = (selectObj: any) => {
    return selectObj?.value?.value || null;
  };

  // Convert dimensions
  const dimensions = {
    frame_size:
      data.dimensions.frame_size.length?.value &&
        data.dimensions.frame_size.width?.value &&
        data.dimensions.frame_size.height?.value
        ? `${data.dimensions.frame_size.length?.value} ${data.dimensions.frame_size.icon_device} ${data.dimensions.frame_size.width?.value
        } ${data.dimensions.frame_size.icon_device} ${data.dimensions.frame_size.height?.value} ${data.dimensions.frame_size.length?.unit}`
        : null,
    maximum_takeoff_weight:
      data.dimensions?.maximum_takeoff_weight?.value != null
        ? formatWithUnit(data.dimensions.maximum_takeoff_weight)
        : null,
    payload_capacity: data.dimensions?.payload_capacity.value
      ? formatWithUnit(data.dimensions?.payload_capacity)
      : null,
    empty_weight: data.dimensions?.empty_weight.value
      ? formatWithUnit(data.dimensions?.empty_weight)
      : null,
    frame_class_id: data.dimensions?.frame_class_id
      ? getSelectValue(data.dimensions?.frame_class_id)
      : null,
    frame_type_id: data.dimensions?.frame_type_id
      ? getSelectValue(data.dimensions?.frame_type_id)
      : null,
  };

  // Convert propulsion system
  const propulsion_system = {
    number_of_motors:
      parseInt(data.propulsion_system?.number_of_motors) || null,
    motor_type_id: data.propulsion_system?.motor_type_id
      ? getSelectValue(data.propulsion_system?.motor_type_id)
      : null,
    battery_type_id: data.propulsion_system?.battery_type_id
      ? getSelectValue(data.propulsion_system?.battery_type_id)
      : null,
    flight_time: data.propulsion_system?.flight_time.value
      ? formatWithUnit(data.propulsion_system?.flight_time)
      : null,
    charging_time: data.propulsion_system?.charging_time.value
      ? formatWithUnit(data.propulsion_system?.charging_time)
      : null,
    motor_power: data.propulsion_system?.motor_power.value
      ? formatWithUnit(data.propulsion_system?.motor_power)
      : null,
    propeller_size: data.propulsion_system?.propeller_size.value
      ? formatWithUnit(data.propulsion_system?.propeller_size)
      : null,
    battery_capacity: data.propulsion_system?.battery_capacity.value
      ? formatWithUnit(data.propulsion_system?.battery_capacity)
      : null,
  };

  // Convert flight performance
  const flight_performance = {
    maximum_speed: data.flight_performance?.maximum_speed.value
      ? formatWithUnit(data.flight_performance?.maximum_speed)
      : null,
    cruise_speed: data.flight_performance?.cruise_speed.value
      ? formatWithUnit(data.flight_performance?.cruise_speed)
      : null,
    maximum_altitude: data.flight_performance?.maximum_altitude.value
      ? formatWithUnit(data.flight_performance?.maximum_altitude)
      : null,
    operating_altitude:
      data.flight_performance?.operating_altitude?.from?.value &&
        data.flight_performance?.operating_altitude?.to?.value
        ? `${data.flight_performance?.operating_altitude?.from?.value} ${data.flight_performance?.operating_altitude?.from?.unit} to ${data.flight_performance?.operating_altitude?.to?.value} ${data.flight_performance?.operating_altitude?.to?.unit}`
        : null,
    maximum_range: data.flight_performance?.maximum_range.value
      ? formatWithUnit(data.flight_performance?.maximum_range)
      : null,
    wind_resistance: data.flight_performance?.wind_resistance.value
      ? formatWithUnit(data.flight_performance?.wind_resistance)
      : null,
  };

  // Convert navigation and control
  const navigation_control = {
    barometric_altimeter:
      data.navigation_control?.barometric_altimeter || false,
    imu: data.navigation_control?.imu?.value || null,
    gps_accuracy: data.navigation_control?.gps_accuracy?.value
      ? `${data.navigation_control?.gps_accuracy?.icon_device}${formatWithUnit(data.navigation_control?.gps_accuracy)}`
      : null,
  };

  // Convert radio communication
  const radio_communication = {
    frequency: data.radio_communication?.frequency.value
      ? formatWithUnit(data.radio_communication?.frequency)
      : null,
    range: data.radio_communication?.range.value
      ? formatWithUnit(data.radio_communication?.range)
      : null,
  };

  // Convert telemetry (copy as is)
  const telemetry = { ...data.telemetry };

  // Convert sensor suite
  const sensor_suite = {
    ...data.sensor_suite,
    id: data.sensor_suite?.id || null,
    gnss:
      data.sensor_suite?.gnss?.value?.length > 0
        ? data.sensor_suite?.gnss?.value?.map((item: any) => item.value)
        : null,
  };

  // Convert environmental specification
  const environmental_specification = {
    temperature_range:
      (data.environmental_specification.temperature_range.length?.value || data.environmental_specification.temperature_range.length?.value == 0) &&
        (data.environmental_specification.temperature_range.width?.value || data.environmental_specification.temperature_range.width?.value == 0)
        ? `${data.environmental_specification.temperature_range.length?.value} to ${data.environmental_specification.temperature_range.width?.value
        } ${data.environmental_specification.temperature_range.length?.unit}`
        : null,
    humidity: data.environmental_specification?.humidity?.value
      ? `${data.environmental_specification.humidity.value[0]}-${data.environmental_specification.humidity.value[1]}${data.environmental_specification.humidity.unit}`
      : null,
    precipitation: data.environmental_specification?.precipitation
      ? data.environmental_specification?.precipitation
      : null,
    wind_speed: data.environmental_specification?.wind_speed.value
      ? 'Up to ' + formatWithUnit(data.environmental_specification?.wind_speed)
      : null,
    noise_takeoff: data.environmental_specification?.noise_takeoff.value
      ? formatWithUnit(data.environmental_specification?.noise_takeoff)
      : null,
    noise_cruise: data.environmental_specification?.noise_cruise.value
      ? formatWithUnit(data.environmental_specification?.noise_cruise)
      : null,
    noise_landing: data.environmental_specification?.noise_landing.value
      ? formatWithUnit(data.environmental_specification?.noise_landing)
      : null,
  };

  // Convert manufacturer information
  const manufacturer_information = {
    ...data.manufacturer_information,
    country_of_origin_id: data.manufacturer_information?.country_of_origin_id
      ? getSelectValue(data.manufacturer_information?.country_of_origin_id)
      : null,
    production_date: convertDateFormatToYYYYMMDD(data.manufacturer_information?.production_date,),
    validity_period_from: convertDateFormatToYYYYMMDD(data.manufacturer_information?.validity_period_from),
    validity_period_to: convertDateFormatToYYYYMMDD(data.manufacturer_information?.validity_period_to),
    id: data.manufacturer_information?.id || null,
    registration_number: data.manufacturer_information?.registration_number || '',
  };

  if (!data.manufacturer_information?.country_of_origin_id) {
    delete data.manufacturer_information.country_of_origin;
  }

  // Convert safety features (copy as is)
  const safety_feature = { ...data.safety_feature };

  // Convert cargo compartments
  const cargo_compartments = {
    id: data.cargo_compartments?.id || null,
    secure_locking: data.cargo_compartments?.secure_locking || false,
    quick_release: data.cargo_compartments?.quick_release || false,
    temperature_control: data.cargo_compartments?.temperature_control || false,
    dimensions:
      data.cargo_compartments.dimensions.length?.value &&
        data.cargo_compartments.dimensions.width?.value &&
        data.cargo_compartments.dimensions.height?.value
        ? `${data.cargo_compartments.dimensions.length?.value || ''} x ${data.cargo_compartments.dimensions.width?.value || ''
        } x ${data.cargo_compartments.dimensions.height?.value || ''} ${data.cargo_compartments.dimensions.length?.unit || ''
        }`
        : null,
    weight_capacity: data.cargo_compartments?.weight_capacity.value
      ? formatWithUnit(data.cargo_compartments?.weight_capacity)
      : null,
    // Add missing required fields with default values
    compartment_number: data.cargo_compartments?.compartment_number || 1,
    name: data.cargo_compartments?.name || 'Default Compartment',
    status: data.cargo_compartments?.status || 'active',
  };

  // Convert device protocols
  const device_protocols =
    data.device_protocols && data.device_protocols.length > 0
      ? data.device_protocols
        .map((protocol: any) => getSelectValue(protocol?.protocol))
        .filter((v: any) => v !== null)
      : null;

  const packaging_specifications =
    data.packaging_specifications && data.packaging_specifications.length > 0
      ? data.packaging_specifications.map((packaging: any) => ({
        ...packaging,
        specifications:
          packaging.specifications && packaging.specifications.length > 0
            ? packaging.specifications
              .map((specification: any) => getSelectValue(specification))
              .filter((v: any) => v !== null)
            : [],
      }))
      : null;

  const surveillance_systems =
    data.surveillance_systems && data.surveillance_systems.length > 0
      ? data.surveillance_systems
        .map((surveillance: any) => getSelectValue(surveillance))
        .filter((v: any) => v !== null)
      : null;

  // Build the final converted object
  const convertedData = isRoleSuperuser
    ? {
      name: data.name || '',
      group_id: data.group?.value || null,
      active: data.active ? true : false,
      main_type_id: data.main_type_id || null,
      // group: data.group.map((group: { label: string, value: number }) => group.value) || [],
      note: data.note || '',
      dimensions: Object.values(dimensions).some((v) => v !== null)
        ? dimensions
        : null,
      propulsion_system: Object.values(propulsion_system).some(
        (v) => v !== null,
      )
        ? propulsion_system
        : null,
      flight_performance: Object.values(flight_performance).some(
        (v) => v !== null,
      )
        ? flight_performance
        : null,
      navigation_control: Object.values(navigation_control).some(
        (v) => v !== null,
      )
        ? navigation_control
        : null,
      radio_communication: Object.values(radio_communication).some(
        (v) => v !== null,
      )
        ? radio_communication
        : null,
      telemetry: Object.keys(telemetry || {}).length > 0 ? telemetry : null,
      sensor_suite:
        Object.keys(sensor_suite || {}).length > 0 ? sensor_suite : null,
      manufacturer_information:
        Object.keys(manufacturer_information || {}).length > 0
          ? manufacturer_information
          : null,
      environmental_specification: Object.values(
        environmental_specification,
      ).some((v) => v !== null)
        ? environmental_specification
        : null,
      safety_feature:
        Object.keys(safety_feature || {}).length > 0 ? safety_feature : null,

      cargo_compartments: Object.values(cargo_compartments).some(
        (v) => v !== null && v !== false,
      )
        ? cargo_compartments
        : null,

      device_protocols: device_protocols,
      packaging_options: packaging_specifications,
      surveillance_systems: surveillance_systems,
    }
    : {
      name: data.name || '',
      active: data.active ? true : false,
      main_type_id: data.main_type_id || null,
      // group: data.group.map((group: { label: string, value: number }) => group.value) || [],
      note: data.note || '',
      dimensions: Object.values(dimensions).some((v) => v !== null)
        ? dimensions
        : null,
      propulsion_system: Object.values(propulsion_system).some(
        (v) => v !== null,
      )
        ? propulsion_system
        : null,
      flight_performance: Object.values(flight_performance).some(
        (v) => v !== null,
      )
        ? flight_performance
        : null,
      navigation_control: Object.values(navigation_control).some(
        (v) => v !== null,
      )
        ? navigation_control
        : null,
      radio_communication: Object.values(radio_communication).some(
        (v) => v !== null,
      )
        ? radio_communication
        : null,
      telemetry: Object.keys(telemetry || {}).length > 0 ? telemetry : null,
      sensor_suite:
        Object.keys(sensor_suite || {}).length > 0 ? sensor_suite : null,
      manufacturer_information:
        Object.keys(manufacturer_information || {}).length > 0
          ? manufacturer_information
          : null,
      environmental_specification: Object.values(
        environmental_specification,
      ).some((v) => v !== null)
        ? environmental_specification
        : null,
      safety_feature:
        Object.keys(safety_feature || {}).length > 0 ? safety_feature : null,

      cargo_compartments: Object.values(cargo_compartments).some(
        (v) => v !== null && v !== false,
      )
        ? cargo_compartments
        : null,

      device_protocols: device_protocols,
      packaging_options: packaging_specifications,
      surveillance_systems: surveillance_systems,
    };

  // Remove null fields for cleaner output
  Object.entries(convertedData).forEach(([key, value]) => {
    if (value === null) {
      delete convertedData[key as keyof typeof convertedData];
    }
  });

  return removeNullAndEmptyValuesDeep(convertedData);
};

export const convertLibraryDataForEdit = (
  { sourceData, unitPreferences, converRawDateToDateFormat }: { sourceData: any, unitPreferences: any, converRawDateToDateFormat: any },
) => {
  if (Object.keys(sourceData).length === 0) return null;
  const resultData = {
    data: {
      name: sourceData?.name || '',
      main_type_id: sourceData?.main_type_id || null,
      group: sourceData?.group__id
        ? {
          label: sourceData?.group__name || null,
          value: sourceData?.group__id || null,
        }
        : null,
      note: sourceData?.note || '',
      active: sourceData?.active,
      dimensions: {
        // Kích thước và trọng lượng (không bắt buộc)
        frame_size: {
          length: {
            value: sourceData?.dimensions?.frame_size?.length || null,
            unit:
              sourceData?.dimensions?.frame_size?.unit ||
              unitPreferences?.DimensionsAndWeight?.frame_size ||
              unitPreferences?.default?.frame_size ||
              'mm',
          },
          width: {
            value: sourceData?.dimensions?.frame_size?.width || null,
            unit:
              sourceData?.dimensions?.frame_size?.unit ||
              unitPreferences?.DimensionsAndWeight?.frame_size ||
              unitPreferences?.default?.frame_size ||
              'mm',
          },
          height: {
            value: sourceData?.dimensions?.frame_size?.height || null,
            unit:
              sourceData?.dimensions?.frame_size?.unit ||
              unitPreferences?.DimensionsAndWeight?.frame_size ||
              unitPreferences?.default?.frame_size ||
              'mm',
          },
          icon_device: sourceData?.dimensions?.frame_size?.icon_device || 'x',
        }, // Kích thước khung
        maximum_takeoff_weight: {
          value: sourceData?.dimensions?.maximum_takeoff_weight?.value || null,
          unit:
            sourceData?.dimensions?.maximum_takeoff_weight?.unit ||
            unitPreferences?.DimensionsAndWeight?.maximum_takeoff_weight ||
            unitPreferences?.default?.maximum_takeoff_weight ||
            'kg',
        }, // Trọng lượng cất cánh tối đa
        payload_capacity: {
          value: sourceData?.dimensions?.payload_capacity?.value || null,
          unit:
            sourceData?.dimensions?.payload_capacity?.unit ||
            unitPreferences?.DimensionsAndWeight?.payload_capacity ||
            unitPreferences?.default?.payload_capacity ||
            'kg',
        }, // Khả năng chở hàng
        empty_weight: {
          value: sourceData?.dimensions?.empty_weight?.value || null,
          unit:
            sourceData?.dimensions?.empty_weight?.unit ||
            unitPreferences?.DimensionsAndWeight?.empty_weight ||
            unitPreferences?.default?.empty_weight ||
            'kg',
        }, // Trọng lượng rỗng
        frame_class_id: {
          value: {
            label: sourceData?.dimensions?.frame_class || null,
            value: sourceData?.dimensions?.frame_class_id || null,
          },
          type: 'select',
        },
        frame_type_id: {
          value: {
            label: sourceData?.dimensions?.frame_type || null,
            value: sourceData?.dimensions?.frame_type_id || null,
          },
          type: 'select',
        },
      },
      propulsion_system: {
        number_of_motors:
          sourceData?.propulsion_system?.number_of_motors || null, // Số lượng động cơ
        motor_type_id: {
          value: {
            label: sourceData?.propulsion_system?.motor_type__name || null,
            value: sourceData?.propulsion_system?.motor_type__id || null,
          },
          type: 'select',
        }, // ID loại động cơ
        battery_type_id: {
          value: {
            label: sourceData?.propulsion_system?.battery_type__name || null,
            value: sourceData?.propulsion_system?.battery_type__id || null,
          },
          type: 'select',
        }, // ID loại pin
        flight_time: {
          value: sourceData?.propulsion_system?.flight_time?.value || null,
          unit:
            sourceData?.propulsion_system?.flight_time?.unit ||
            unitPreferences?.PropulsionSystem?.flight_time ||
            unitPreferences?.default?.flight_time ||
            'minutes',
        }, // Thời gian bay
        charging_time: {
          value: sourceData?.propulsion_system?.charging_time?.value || null,
          unit:
            sourceData?.propulsion_system?.charging_time?.unit ||
            unitPreferences?.PropulsionSystem?.charging_time ||
            unitPreferences?.default?.charging_time ||
            'minutes',
        }, // Thời gian sạc
        motor_power: {
          value: sourceData?.propulsion_system?.motor_power?.value || null,
          unit:
            sourceData?.propulsion_system?.motor_power?.unit ||
            unitPreferences?.PropulsionSystem?.motor_power ||
            unitPreferences?.default?.motor_power ||
            'kW',
        }, // Công suất động cơ
        propeller_size: {
          value: sourceData?.propulsion_system?.propeller_size?.value || null,
          unit:
            sourceData?.propulsion_system?.propeller_size?.unit ||
            unitPreferences?.PropulsionSystem?.propeller_size ||
            unitPreferences?.default?.propeller_size ||
            'inch',
        }, // Kích thước cánh quạt
        battery_capacity: {
          value: sourceData?.propulsion_system?.battery_capacity?.value || null,
          unit:
            sourceData?.propulsion_system?.battery_capacity?.unit ||
            unitPreferences?.PropulsionSystem?.battery_capacity ||
            unitPreferences?.default?.battery_capacity ||
            'mAh',
        }, // Dung lượng pin
      },

      flight_performance: {
        // Hiệu suất bay (không bắt buộc)
        maximum_speed: {
          value: sourceData?.flight_performance?.maximum_speed?.value || null,
          unit:
            sourceData?.flight_performance?.maximum_speed?.unit ||
            unitPreferences?.FlightPerformance?.maximum_speed ||
            unitPreferences?.default?.maximum_speed ||
            'km/h',
        }, // Tốc độ tối đa
        cruise_speed: {
          value: sourceData?.flight_performance?.cruise_speed?.value || null,
          unit:
            sourceData?.flight_performance?.cruise_speed?.unit ||
            unitPreferences?.FlightPerformance?.cruise_speed ||
            unitPreferences?.default?.cruise_speed ||
            'km/h',
        }, // Tốc độ hành trình
        maximum_altitude: {
          value:
            sourceData?.flight_performance?.maximum_altitude?.value || null,
          unit:
            sourceData?.flight_performance?.maximum_altitude?.unit ||
            unitPreferences?.FlightPerformance?.maximum_altitude ||
            unitPreferences?.default?.maximum_altitude ||
            'm',
        }, // Độ cao tối đa
        operating_altitude: {
          from: {
            value:
              sourceData?.flight_performance?.operating_altitude?.min || null,
            unit:
              sourceData?.flight_performance?.operating_altitude?.unit ||
              unitPreferences?.FlightPerformance?.operating_altitude ||
              unitPreferences?.default?.operating_altitude ||
              'm',
          },
          to: {
            value:
              sourceData?.flight_performance?.operating_altitude?.max || null,
            unit:
              sourceData?.flight_performance?.operating_altitude?.to?.unit ||
              unitPreferences?.FlightPerformance?.operating_altitude ||
              unitPreferences?.default?.operating_altitude ||
              'm',
          },
          icon_device:
            sourceData?.flight_performance?.operating_altitude?.icon_device ||
            '-',
        }, // Độ cao hoạt động
        maximum_range: {
          value: sourceData?.flight_performance?.maximum_range?.value || null,
          unit:
            sourceData?.flight_performance?.maximum_range?.unit ||
            unitPreferences?.FlightPerformance?.maximum_range ||
            unitPreferences?.default?.maximum_range ||
            'km',
        }, // Phạm vi tối đa
        wind_resistance: {
          value: sourceData?.flight_performance?.wind_resistance?.value || null,
          unit:
            sourceData?.flight_performance?.wind_resistance?.unit ||
            unitPreferences?.FlightPerformance?.wind_resistance ||
            unitPreferences?.default?.wind_resistance ||
            'km/h',
        }, // Khả năng chống gió
      },

      navigation_control: {
        // Điều hướng và kiểm soát (không bắt buộc)
        barometric_altimeter:
          sourceData?.navigation_control?.barometric_altimeter, // Có đo độ cao khí áp
        imu: {
          value: sourceData?.navigation_control?.imu?.value || null,
          type: sourceData?.navigation_control?.imu?.type || 'string',
        },
        gps_accuracy: {
          // Độ chính xác GPS
          value: sourceData?.navigation_control?.gps_accuracy?.margin || null,
          unit:
            sourceData?.navigation_control?.gps_accuracy?.unit ||
            unitPreferences?.default?.gps_accuracy ||
            'm',
          icon_device:
            sourceData?.navigation_control?.gps_accuracy?.icon_device || '±',
        },
      },

      radio_communication: {
        // Liên lạc vô tuyến (không bắt buộc)
        frequency: {
          value: sourceData?.radio_communication?.frequency?.value || null,
          unit:
            sourceData?.radio_communication?.frequency?.unit ||
            unitPreferences?.default?.frequency ||
            'GHz',
        }, // Tần số
        range: {
          value: sourceData?.radio_communication?.range?.value || null,
          unit:
            sourceData?.radio_communication?.range?.unit ||
            unitPreferences?.default?.range ||
            'km',
        }, // Phạm vi
      },

      telemetry: {
        // Telemetry (không bắt buộc)
        realtime_flight_data: sourceData?.telemetry?.realtime_flight_data, // Theo dõi thời gian thực
        video_streaming: sourceData?.telemetry?.video_streaming, // Streaming video
        battery_status_monitoring:
          sourceData?.telemetry?.battery_status_monitoring, // Theo dõi trạng thái pin
        gps_position_tracking: sourceData?.telemetry?.gps_position_tracking, // Theo dõi vị trí GPS
        system_health_monitoring:
          sourceData?.telemetry?.system_health_monitoring, // Theo dõi trạng thái hệ thống
      },

      sensor_suite: {
        // Bộ cảm biến (không bắt buộc)
        id: sourceData?.sensor_suite?.id || null,
        gnss: {
          value: sourceData?.sensor_suite?.gnss.map((item: any) => ({
            label: item.name,
            value: item.id,
          })),
        },
        optical_flow_sensor: sourceData?.sensor_suite?.optical_flow_sensor, // Phát hiện chướng ngại vật
        ultrasonic_sensors: sourceData?.sensor_suite?.ultrasonic_sensors, // Tránh va chạm
        lidar: sourceData?.sensor_suite?.lidar, // Định vị hình ảnh
        ais: sourceData?.sensor_suite?.ais,
        ads_b_receiver: sourceData?.sensor_suite?.ads_b_receiver,
        rf_signal_detector: sourceData?.sensor_suite?.rf_signal_detector,
        chemical_sensor_array: sourceData?.sensor_suite?.chemical_sensor_array,
        radiation_detector: sourceData?.sensor_suite?.radiation_detector,
        weather_sensors: sourceData?.sensor_suite?.weather_sensors,
      },

      manufacturer_information: {
        // Thông tin nhà sản xuất (không bắt buộc)
        id: sourceData?.manufacturer_information?.id || null,
        manufacturer: sourceData?.manufacturer_information?.manufacturer || '', // Tên nhà sản xuất
        country_of_origin_id: {
          value: {
            label:
              sourceData?.manufacturer_information?.country_of_origin__name ||
              null,
            value:
              sourceData?.manufacturer_information?.country_of_origin__id ||
              null,
          },
          type:
            sourceData?.manufacturer_information?.country_of_origin_id?.type ||
            'select',
        }, // Quốc gia xuất xứ
        contact_information:
          sourceData?.manufacturer_information?.contact_information || '',
        insurance_type:
          sourceData?.manufacturer_information?.insurance_type || '',
        insurance_provider:
          sourceData?.manufacturer_information?.insurance_provider || '',
        policy_number:
          sourceData?.manufacturer_information?.policy_number || '',
        validity_period_from: sourceData?.manufacturer_information?.validity_period_from
          ? converRawDateToDateFormat(sourceData?.manufacturer_information?.validity_period_from) : '',
        validity_period_to: sourceData?.manufacturer_information?.validity_period_to
          ? converRawDateToDateFormat(sourceData?.manufacturer_information?.validity_period_to) : '',
        current_status:
          sourceData?.manufacturer_information?.current_status || 'active',
        serial_number:
          sourceData?.manufacturer_information?.serial_number || '',
        model_number: sourceData?.manufacturer_information?.model_number || '',
        production_date: sourceData?.manufacturer_information?.production_date
          ? converRawDateToDateFormat(sourceData?.manufacturer_information?.production_date) : null,
        insurance_status:
          sourceData?.manufacturer_information?.insurance_status || false,
        registration_number: sourceData?.manufacturer_information?.registration_number || '',
      },

      // insurance_information: {
      //   // Thông tin bảo hiểm (không bắt buộc)
      //   insurer: sourceData?.insurance_information?.insurer, // Công ty bảo hiểm
      //   policy_number: sourceData?.insurance_information?.policy_number, // Số hợp đồng
      //   coverage_amount: sourceData?.insurance_information?.coverage_amount, // Số tiền bảo hiểm
      //   valid_from: sourceData?.insurance_information?.valid_from, // Có hiệu lực từ
      //   valid_until: sourceData?.insurance_information?.valid_until, // Có hiệu lực đến
      // },

      environmental_specification: {
        // Thông số môi trường (không bắt buộc)
        temperature_range: {
          length: {
            value:
              sourceData?.environmental_specification?.temperature_range?.min ??
              null,
            unit:
              sourceData?.environmental_specification?.temperature_range
                ?.unit ||
              unitPreferences?.EnvironmentalSpecification?.temperature_range ||
              unitPreferences?.default?.temperature_range ||
              '°C',
          },
          width: {
            value:
              sourceData?.environmental_specification?.temperature_range?.max ??
              null,
            unit:
              sourceData?.environmental_specification?.temperature_range
                ?.unit ||
              unitPreferences?.EnvironmentalSpecification?.temperature_range ||
              unitPreferences?.default?.temperature_range ||
              '°C',
          },
          icon_device:
            sourceData?.environmental_specification?.temperature_range
              ?.icon_device || '-',
        }, // Phạm vi nhiệt độ
        humidity: {
          value: [
            sourceData?.environmental_specification?.humidity?.min || 0,
            sourceData?.environmental_specification?.humidity?.max || 0,
          ],
          unit:
            sourceData?.environmental_specification?.humidity?.unit ||
            unitPreferences?.EnvironmentalSpecification?.humidity ||
            unitPreferences?.default?.humidity ||
            '%',
        }, // Độ ẩm
        precipitation:
          sourceData?.environmental_specification?.precipitation?.value || '', // Lượng mưa
        wind_speed: {
          value:
            sourceData?.environmental_specification?.wind_speed?.max || null,
          unit:
            sourceData?.environmental_specification?.wind_speed?.unit ||
            unitPreferences?.EnvironmentalSpecification?.wind_speed ||
            unitPreferences?.default?.wind_speed ||
            'km/h',
        }, // Tốc độ gió
        noise_takeoff: {
          value:
            sourceData?.environmental_specification?.noise_takeoff?.value ||
            null,
          unit:
            sourceData?.environmental_specification?.noise_takeoff?.unit ||
            unitPreferences?.EnvironmentalSpecification?.noise_takeoff ||
            unitPreferences?.default?.noise_takeoff ||
            'dB',
        }, // Tiếng ồn khi cất cánh
        noise_cruise: {
          value:
            sourceData?.environmental_specification?.noise_cruise?.value ||
            null,
          unit:
            sourceData?.environmental_specification?.noise_cruise?.unit ||
            unitPreferences?.EnvironmentalSpecification?.noise_cruise ||
            unitPreferences?.default?.noise_cruise ||
            'dB',
        }, // Tiếng ồn khi bay
        noise_landing: {
          value:
            sourceData?.environmental_specification?.noise_landing?.value ||
            null,
          unit:
            sourceData?.environmental_specification?.noise_landing?.unit ||
            unitPreferences?.EnvironmentalSpecification?.noise_landing ||
            unitPreferences?.default?.noise_landing ||
            'dB',
        }, // Tiếng ồn khi hạ cánh
      },

      safety_feature: {
        // Tính năng an toàn (không bắt buộc)
        dual_imu: sourceData?.safety_feature?.dual_imu, //
        dual_gps: sourceData?.safety_feature?.dual_gps, //
        dual_battery: sourceData?.safety_feature?.dual_battery, //
        emergency_parachute: sourceData?.safety_feature?.emergency_parachute, //
        return_to_home: sourceData?.safety_feature?.return_to_home, //
        obstacle_detection_360:
          sourceData?.safety_feature?.obstacle_detection_360, //
        stereo_cameras: sourceData?.safety_feature?.stereo_cameras, //
        lidar_mapping: sourceData?.safety_feature?.lidar_mapping, //
        emergency_braking: sourceData?.safety_feature?.emergency_braking, //
      },

      cargo_compartments: {
        // Khoang hàng (không bắt buộc)
        // compartment_number: 1, // Số khoang
        // name: "Main Cargo", // Tên khoang
        id: sourceData?.cargo_compartments?.id || null,
        secure_locking: sourceData?.cargo_compartments?.secure_locking, // Khóa an toàn
        quick_release: sourceData?.cargo_compartments?.quick_release, // Nhả nhanh
        temperature_control:
          sourceData?.cargo_compartments?.temperature_control, // Kiểm soát nhiệt độ
        // status: "operational", // Trạng thái
        dimensions: {
          length: {
            value: sourceData?.cargo_compartments?.dimensions?.length || null,
            unit:
              sourceData?.cargo_compartments?.dimensions?.unit ||
              unitPreferences?.CargoCompartments?.dimensions ||
              unitPreferences?.default?.dimensions ||
              'mm',
          },
          width: {
            value: sourceData?.cargo_compartments?.dimensions?.width || null,
            unit:
              sourceData?.cargo_compartments?.dimensions?.unit ||
              unitPreferences?.CargoCompartments?.dimensions ||
              unitPreferences?.default?.dimensions ||
              'mm',
          },
          height: {
            value: sourceData?.cargo_compartments?.dimensions?.height || null,
            unit:
              sourceData?.cargo_compartments?.dimensions?.unit ||
              unitPreferences?.CargoCompartments?.dimensions ||
              unitPreferences?.default?.dimensions ||
              'mm',
          },
          icon_device:
            sourceData?.cargo_compartments?.dimensions?.icon_device || 'x',
        }, // Kích thước
        weight_capacity: {
          value: sourceData?.cargo_compartments?.weight_capacity?.value || null,
          unit:
            sourceData?.cargo_compartments?.weight_capacity?.unit ||
            unitPreferences?.CargoCompartments?.weight_capacity ||
            unitPreferences?.default?.weight_capacity ||
            'kg',
        }, // Khả năng chịu trọng lượng
      },
      device_protocols: (sourceData?.device_protocols || []).map(
        (spec: any) => ({
          protocol: {
            value: {
              label: spec.name,
              value: spec.id,
            },
            type: 'select',
          },
          type_of_protocol: {
            value: {
              label: spec.type,
              value: spec.type,
            },
            type: 'select',
          },
        }),
      ),
      // packaging_specifications: sourceData?.packaging_specification || [],
      packaging_specifications: (sourceData?.packaging_specification || []).map(
        (spec: any) => ({
          id: spec.id,
          name: spec.name,
          order: spec.order,
          specifications: (spec.specifications || []).map((spec: any) => ({
            type: 'select',
            value: {
              label: spec.name,
              value: spec.id,
            },
          })),
        }),
      ),
      surveillance_systems: (sourceData?.surveillance_systems || []).map(
        (spec: any) => ({
          value: {
            label: spec.name,
            value: spec.id,
          },
          type: 'select',
        }),
      ),
    },
    avatar: sourceData?.avatar__file_url || null,
    files: sourceData?.file_attachments || [],
  };
  return resultData;
};

