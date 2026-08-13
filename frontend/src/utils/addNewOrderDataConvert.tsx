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
export const convertOrderData = (sourceData: any) => {
  if (!sourceData || !sourceData.data) return null;
  const data = sourceData.data;

  const convertedData = {
    sender_name: data?.sender?.name,
    sender_phone: data?.sender?.phone_number,
    sender_note: data?.sender?.note,
    recipient_name: data?.recipient?.name,
    recipient_phone: data?.recipient?.phone_number,
    recipient_note: data?.recipient?.note,
    pickup_location_id: data?.sender?.location_id?.value?.value,
    delivery_option_code: data?.delivery_option,
    delivery_terminal_id: data?.delivery_location_id?.value?.value,
    payment_method_code: data?.payment,
    recipient_address: {
      city: data?.recipient?.city_province?.value,
      district: data?.recipient?.city_county_district?.value,
      ward: data?.recipient?.ward_town_township?.value,
      street: data?.recipient?.street_address,
      full_address: data?.recipient?.full_address,
      lat: data?.recipient?.latitude,
      lng: data?.recipient?.longitude,
    },
    items: data?.package.map((item: any) => ({
      weight: {
        value: item?.package_weight?.value,
        unit: item?.package_weight?.unit,
      },
      dimension_l: {
        value: item?.dimensions?.length?.value,
        unit: item?.dimensions?.length?.unit,
      },
      dimension_w: {
        value: item?.dimensions?.width?.value,
        unit: item?.dimensions?.width?.unit,
      },
      dimension_h: {
        value: item?.dimensions?.height?.value,
        unit: item?.dimensions?.height?.unit,
      },
      is_waterproof: item?.is_water_proof,
      is_fragile: item?.is_fragile,
      item_type_id: item?.item_type?.value?.value,
      package_id: item?.packaging?.value?.value,
      note: item?.note,
    })),
  };
  // Remove null fields for cleaner output
  Object.entries(convertedData).forEach(([key, value]) => {
    if (value === null) {
      delete convertedData[key as keyof typeof convertedData];
    }
  });

  return removeNullAndEmptyValuesDeep(convertedData);
};
export const convertOrderDataToForm = (detailOrder: any) => {
  return {
    data: {
      sender: {
        name: detailOrder?.sender_name,
        phone_number: detailOrder?.sender_phone,
        location_id: {
          value: {
            label: detailOrder?.pickup_location,
            value: detailOrder?.pickup_location__id,
          },
          type: 'select',
        },
        note: detailOrder?.sender_note,
      },
      recipient: {
        name: detailOrder?.recipient_name,
        phone_number: detailOrder?.recipient_phone,
        address_type: 'geographic_coordinates',
        full_address: detailOrder?.recipient_address__full_address,
        latitude: detailOrder?.recipient_address__lat,
        longitude: detailOrder?.recipient_address__lng,
        street_address: detailOrder?.recipient_address__street,
        city_province: {
          value: detailOrder?.recipient_address__city,
          label: detailOrder?.recipient_address__city,
        },
        city_county_district: {
          value: detailOrder?.recipient_address__district,
          label: detailOrder?.recipient_address__district,
        },
        ward_town_township: {
          value: detailOrder?.recipient_address__ward,
          label: detailOrder?.recipient_address__ward,
        },
        note: detailOrder?.recipient_note,
      },
      delivery_option: detailOrder?.delivery_option__code,
      delivery_location_id: {
        value: {
          label: detailOrder?.delivery_address,
          value: detailOrder?.delivery_terminal__id,
        },
        type: 'select',
      },
      agree: true,
      payment: 'cash',
      package: detailOrder?.items.map((item: any) => ({
        package_weight: {
          value: item?.weight?.value,
          unit: item?.weight?.unit || 'kg',
        },
        dimensions: {
          length: {
            value: item?.dimension_l?.value,
            unit: item?.dimension_l?.unit || 'mm',
          },
          width: {
            value: item?.dimension_w?.value,
            unit: item?.dimension_w?.unit || 'mm',
          },
          height: {
            value: item?.dimension_h?.value,
            unit: item?.dimension_h?.unit || 'mm',
          },
        },
        item_type: {
          value: {
            label: item?.item_type,
            value: item?.item_type_id,
          },
          type: 'select',
        },
        is_water_proof: item?.is_waterproof,
        is_fragile: item?.is_fragile,
        packaging: {
          value: {
            label: item?.details,
            value: item?.package_id,
          },
          type: 'select',
        },
        package_detail: item?.details,
        note: item?.note,
      })),
      orderAfterSubmit: null,
      validStreet: false,
    },
  };
};
