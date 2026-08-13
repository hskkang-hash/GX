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

export const convertPackagingData = (sourceData: any) => {
  if (!sourceData) return null;
  // Helper function to format value with unit
  const formatWithUnit = (obj: any) => {
    if (!obj) return null;
    return obj.value && obj.unit ? `${obj.value} ${obj.unit}` : null;
  };
  // Helper function to get ID value from select object
  // const getSelectValue = (selectObj: any) => {
  //     return selectObj?.value?.value || null;
  // };

  const formatDimensions = (data: any) => {
    return data.dimensions?.length?.value &&
      data.dimensions?.width?.value &&
      data.dimensions?.height?.value &&
      data?.maximum_weight?.value
      ? `${data.dimensions?.length?.value} ${data.dimensions?.icon_device} ${
          data.dimensions?.width?.value
        } ${data.dimensions?.icon_device} ${data.dimensions?.height?.value} ${data.dimensions?.length?.unit}`
      : null;
  };
  // Build the final converted object
  const convertedData = {
    active: sourceData?.active !== undefined ? sourceData?.active : true,
    name: sourceData?.name || '',
    code: sourceData?.code || '',
    dimensions: formatDimensions(sourceData),
    max_weight: formatWithUnit(sourceData?.maximum_weight),
    package_type_id: sourceData?.package_type_id?.value?.value || null,
    water_proof: sourceData?.water_proof,
    fragile: sourceData?.fragile,
    note: sourceData?.note || '',
    group_id: sourceData?.group?.value?.value || null,
  };

  // Remove null fields for cleaner output
  Object.entries(convertedData).forEach(([key, value]) => {
    if (value === null) {
      delete convertedData[key as keyof typeof convertedData];
    }
  });
  return removeNullAndEmptyValuesDeep(convertedData);
};

export const convertPackagingDataForEdit = (data: any) => {
  if (Object.keys(data).length === 0) return null;
  const resultData = {
    code: data?.code || null,
    name: data?.name || null,
    group: {
      value: data?.group__id
        ? {
            value: data?.group__id || null,
            label: data?.group__name || null,
          }
        : null,
    },
    dimensions: {
      length: {
        value: data?.dimensions?.length || null,
        unit: data?.dimensions?.unit || 'mm',
      },
      width: {
        value: data?.dimensions?.width || null,
        unit: data?.dimensions?.unit || 'mm',
      },
      height: {
        value: data?.dimensions?.height || null,
        unit: data?.dimensions?.unit || 'mm',
      },
      icon_device: 'x',
    },
    maximum_weight: {
      value: data?.max_weight?.value || null,
      unit: data?.max_weight?.unit || 'kg',
    },
    package_type_id: {
      value: {
        value: data?.package_type_id || null,
        label: data?.package_type__name || null,
      },
    },
    water_proof: data?.water_proof ? data?.water_proof : null,
    fragile: data?.fragile ? data?.fragile : false,
    note: data?.note,
  };
  return resultData;
};
