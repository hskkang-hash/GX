export interface IFormData {
  data: Record<string, any>;
}
export const DEFAULT_FORM_VALUES: IFormData = {
  data: {
    sender: {
      name: '',
      phone_number: '',
      location_id: {
        value: null,
        type: 'select',
      },
      note: '',
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
      note: '',
    },
    delivery_option: 'delivery_to_door',
    delivery_location_id: {
      value: null,
      type: 'select',
    },
    agree: false,
    payment: 'cash',
    package: [
      {
        package_weight: {
          value: null,
          unit: 'kg',
        },
        dimensions: {
          length: {
            value: null,
            unit: 'mm',
          },
          width: {
            value: null,
            unit: 'mm',
          },
          height: {
            value: null,
            unit: 'mm',
          },
        },
        item_type: {
          value: {
            label: null,
            code: null,
            value: null,
          },
          type: 'select',
        },
        is_water_proof: false,
        is_fragile: false,
        packaging: {
          value: {
            label: null,
            value: null,
          },
          type: 'select',
        },
        package_detail: '',
        note: '',
      },
    ],
    orderAfterSubmit: null,
  },
};
