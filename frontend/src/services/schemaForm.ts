import { t, TFunction } from 'i18next';
import * as yup from 'yup';

import i18n from '@/i18n';
import { checkPhoneMaskType, getPhoneMaskTypeByLanguage } from '@/utils/utils';

// Schema for Step 0 Shipping Information
export const addNewOrderSchemaStep0 = (t: TFunction) =>
  yup.object({
    data: yup.object({
      sender: yup
        .object()
        .shape({
          name: yup.string().required(t('Name is required')),
          phone_number: yup
            .string()
            .required(t('Phone number is required'))
            .test(
              'phone-validation',
              t('Phone number is not valid'),
              function (value) {
                if (!value) return true;
                const validationResult = validatePhoneByMask(
                  value,
                  checkPhoneMaskType(value) ||
                  getPhoneMaskTypeByLanguage(i18n.language),
                );
                if (validationResult === true) {
                  return true;
                }
                return this.createError({
                  message: validationResult,
                  path: this.path,
                });
              },
            ),
          location_id: yup
            .object()
            .shape({
              value: yup
                .object()
                .shape({
                  label: yup.string().required(t('Location is required')),
                  value: yup
                    .number()
                    .required(t('Location is required'))
                    .nullable(),
                })
                .required(t('Location is required')),
            })
            .required(t('Location is required')),
        })
        .required(t('Sender is required')),
      recipient: yup
        .object()
        .shape({
          name: yup.string().required(t('Name is required')),
          phone_number: yup
            .string()
            .required(t('Phone number is required'))
            .test(
              'phone-validation',
              t('Phone number is not valid'),
              function (value) {
                if (!value) return true;
                const validationResult = validatePhoneByMask(
                  value,
                  checkPhoneMaskType(value) ||
                  getPhoneMaskTypeByLanguage(i18n.language),
                );
                if (validationResult === true) {
                  return true;
                }
                return this.createError({
                  message: validationResult,
                  path: this.path,
                });
              },
            ),
          full_address: yup.string().required(t('Address is required')),
        })
        .required(t('Recipient is required')),
      delivery_option: yup.string().required(t('Delivery option is required')),
      delivery_location_id: yup.object().when('delivery_option', {
        is: 'collect_at_location',
        then: (schema) =>
          schema
            .shape({
              value: yup
                .object()
                .shape({
                  label: yup
                    .string()
                    .required(t('Delivery location is required')),
                  value: yup
                    .number()
                    .required(t('Delivery location is required'))
                    .nullable(),
                })
                .required(t('Delivery location is required')),
              type: yup
                .string()
                .required(t('Delivery location type is required')),
            })
            .required(t('Delivery location is required')),
        otherwise: (schema) => schema.notRequired(),
      }),
    }),
  });

// Schema for Step 1 Package Information
export const addNewOrderSchemaStep1 = (t: TFunction) =>
  yup.object({
    data: yup.object({
      package: yup
        .array()
        .of(
          yup.object().shape({
            package_weight: yup
              .object()
              .shape({
                value: yup
                  .number()
                  .required(t('Package weight is required'))
                  .min(0, t('Package weight must be greater than 0')),
                unit: yup.string().required(t('Unit is required')),
              })
              .required(t('Package weight is required')),
            dimensions: yup
              .object()
              .shape({
                length: yup
                  .object()
                  .shape({
                    value: yup
                      .number()
                      .required(t('Length is required'))
                      .min(0, t('Length must be greater than 0')),
                    unit: yup.string().required(t('Unit is required')),
                  })
                  .required(t('Length is required')),
                width: yup
                  .object()
                  .shape({
                    value: yup
                      .number()
                      .required(t('Width is required'))
                      .min(0, t('Width must be greater than 0')),
                    unit: yup.string().required(t('Unit is required')),
                  })
                  .required(t('Width is required')),
                height: yup
                  .object()
                  .shape({
                    value: yup
                      .number()
                      .required(t('Height is required'))
                      .min(0, t('Height must be greater than 0')),
                    unit: yup.string().required(t('Unit is required')),
                  })
                  .required(t('Height is required')),
              })
              .required(t('Dimensions are required')),
            item_type: yup
              .object()
              .required(t('Item type is required'))
              .shape({
                value: yup
                  .object()
                  .shape({
                    code: yup.string().required(t('Item type is required')),
                    label: yup.string().required(t('Item type is required')),
                    value: yup.number().required(t('Item type is required')),
                    // .nullable(),
                  })
                  .required(t('Item type is required')),
              })
              .required(t('Item type is required')),
            packaging: yup
              .object()
              .shape({
                value: yup
                  .object()
                  .shape({
                    label: yup.string().required(t('Packaging is required')),
                    value: yup.number().required(t('Packaging is required')),
                    // .nullable(),
                  })
                  .required(t('Packaging is required')),
              })
              .required(t('Packaging is required')),
          }),
        )
        .required(t('Package is required'))
        .min(1, t('At least one package is required')),
    }),
  });

// Schema for Step 2 Payment Information
export const addNewOrderSchemaStep2 = (t: TFunction) =>
  yup.object({
    data: yup.object({
      payment: yup.string().required(t('Payment is required')),
      agree: yup
        .boolean()
        .required(t('Agree is required'))
        .oneOf([true], t('You must agree to the terms')),
    }),
  });

// Legacy schemas for backward compatibility
export const addNewOrderSchema = addNewOrderSchemaStep0;
export const addNewOrderSchema2 = addNewOrderSchemaStep1;

// Dynamic schema for Device based on user role
export const schemaDeviceWhenEdit = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
    main_type_id: yup.string().required(t('Main Type is required')),
    unit_id: yup.object({
      value: yup
        .object({
          value: yup.string().required(t('Unit is required')),
          label: yup.string().required(t('Unit is required')),
        })
        .required(t('Unit is required')),
    }),
    library_id: yup.object({
      value: yup
        .object({
          value: yup.number().required(t('Library is required')),
          label: yup.string().required(t('Library is required')),
        })
        .required(t('Library is required')),
    }),
    terminal_id: yup.object({
      value: yup
        .object({
          value: yup.number().required('Terminal is required'),
          label: yup.string(),
        })
        .required('Terminal is required'),
    }),

    // Add validation for dimensions to check maximum_takeoff_weight > empty_weight
    dimensions: yup
      .object({
        maximum_takeoff_weight: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
        empty_weight: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
      })
      .test(
        'validate-dimensions',
        t('Maximum takeoff weight must be greater than empty weight'),
        function (dimensions) {
          const maxVal = dimensions?.maximum_takeoff_weight?.value;
          const emptyVal = dimensions?.empty_weight?.value;
          if (maxVal == null || emptyVal == null) {
            return true;
          }
          if (maxVal <= emptyVal) {
            const errors = [];
            errors.push(
              this.createError({
                path: `${this.path}.maximum_takeoff_weight.value`,
                message: t(
                  'Maximum takeoff weight must be greater than empty weight',
                ),
              }),
            );
            errors.push(
              this.createError({
                path: `${this.path}.empty_weight.value`,
                message: t(
                  'Maximum takeoff weight must be greater than empty weight',
                ),
              }),
            );
            return new yup.ValidationError(errors);
          }
          return true;
        },
      ),

    cargo_compartments: yup.object({
      dimensions: yup.object({
        length: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Length must be a number'))
            .required(t('Temperature Length is required')),
        }),
        width: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Width must be a number'))
            .required(t('Temperature Width is required')),
        }),
        height: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Height must be a number'))
            .required(t('Temperature Height is required')),
        }),
      }),
      weight_capacity: yup.object({
        value: yup
          .number()
          .typeError(t('Weight Capacity must be a number'))
          .required(t('Weight Capacity is required')),
      }),
    }),

    packaging_specifications: yup.array().of(
      yup.object({
        name: yup.string(),
        order: yup.number(),
        specifications: yup.array().of(
          yup.object({
            value: yup
              .mixed()
              .required(t('Packaging specification is required')),
            type: yup.string(),
          }),
        ),
      }),
    ),

    flight_performance: yup.object({
      operating_altitude: yup
        .object({
          from: yup.object({
            value: yup.number().nullable(),
            unit: yup.string(),
          }),
          to: yup.object({
            value: yup.number().nullable(),
            unit: yup.string(),
          }),
        })
        .test(
          'validate-resolution',
          t('Next value must be greater than previous.'),
          function (operating_altitude) {
            const fromVal = operating_altitude?.from?.value;
            const toVal = operating_altitude?.to?.value;
            if (fromVal == null || toVal == null) {
              return true;
            }
            if (fromVal > toVal || fromVal == toVal) {
              const errors = [];
              errors.push(
                this.createError({
                  path: `${this.path}.from.value`,
                  message: t('Next value must be greater than previous.'),
                }),
              );
              errors.push(
                this.createError({
                  path: `${this.path}.to.value`,
                  message: t('Next value must be greater than previous.'),
                }),
              );
              return new yup.ValidationError(errors);
            }
            return true;
          },
        ),
    }),
    propulsion_system: yup.object({
      number_of_motors: yup
        .number()
        .typeError('Must be a number')
        .integer('Must be an integer')
        .min(-2147483648, 'Minimum value is -2,147,483,648')
        .max(2147483647, 'Maximum value is 2,147,483,647')
        .nullable(),

      flight_time: yup.object({
        value: yup
          .number()
          .nullable()
          .min(1, t('Flight time must be greater than 0'))
          .required(t('Flight time is required')),
      }),
    }),
    device_protocols: yup.array().of(
      yup
        .object({
          type_of_protocol: yup.object({
            value: yup.mixed().nullable(),
          }),
          protocol: yup.object({
            value: yup.mixed().nullable(),
          }),
        })
        .test(
          'require-protocol-if-type-selected',
          t('Protocol is required when Type of Protocol is selected'),
          function (value) {
            const type = value?.type_of_protocol?.value;
            const protocol = value?.protocol?.value;

            if (type && !protocol) {
              return this.createError({
                path: `${this.path}.protocol.value`,
                message: t(
                  'Protocol is required when Type of Protocol is selected',
                ),
              });
            }
            return true;
          },
        ),
    ),
    manufacturer_information: yup.object({
      registration_number: yup
        .string()
        .nullable()
        .matches(/^[A-Za-z][A-Za-z0-9]*$/, {
          message: t(
            'The registration number must be a combination of uppercase letters and numbers.',
          ),
          excludeEmptyString: true,
        }),
    }),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      data: yup.object({
        ...baseSchema,
        group: yup.object({
          value: yup
            .object({
              value: yup.number().required(t('Group is required')),
              label: yup.string(),
            })
            .required(t('Group is required')),
        }),
      }),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    data: yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().nullable(),
          label: yup.string(),
        })
        .nullable(),
    }),
  });
};

export const schemaDeviceWhenAddNew = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
    main_type_id: yup.string().required(t('Main Type is required')),
    color: yup.string().required(t('Color is required')),

    unit_id: yup
      .object({
        value: yup
          .object({
            value: yup.string().required(t('Device ID is required')),
            label: yup.string().required(t('Device ID is required')),
          })
          .required(t('Device ID is required')),
        type: yup.string().required(t('Type is required')),
      })
      .required(t('Device ID is required')),

    library_id: yup
      .object({
        value: yup
          .object({
            value: yup.number().required(t('Device Template is required')),
            label: yup.string().required(t('Device Template is required')),
          })
          .required(t('Device Template is required')),
        type: yup.string().required(t('Type is required')),
      })
      .required(t('Device Template is required')),

    terminal_id: yup
      .object({
        value: yup
          .object({
            value: yup.mixed().required(t('Linked Terminal is required')),
            label: yup.string().required(t('Linked Terminal is required')),
          })
          .required(t('Linked Terminal is required')),
      })
      .required(t('Linked Terminal is required')),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      data: yup.object({
        ...baseSchema,
        group: yup
          .object({
            value: yup
              .object({
                value: yup.mixed().required(t('Group is required')),
                label: yup.string().required(t('Group is required')),
              })
              .required(t('Group is required')),
          })
          .required(t('Group is required')),
      }),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    data: yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.mixed().nullable(),
        })
        .nullable(),
    }),
  });
};
export const schemaLibrary = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
    main_type_id: yup.string().required(t('Main Type is required')),

    // Add validation for dimensions to check maximum_takeoff_weight > empty_weight
    dimensions: yup
      .object({
        maximum_takeoff_weight: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
        empty_weight: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
      })
      .test(
        'validate-dimensions',
        t('Maximum takeoff weight must be greater than empty weight'),
        function (dimensions) {
          const maxVal = dimensions?.maximum_takeoff_weight?.value;
          const emptyVal = dimensions?.empty_weight?.value;
          if (maxVal == null || emptyVal == null) {
            return true;
          }
          if (maxVal <= emptyVal) {
            const errors = [];
            errors.push(
              this.createError({
                path: `${this.path}.maximum_takeoff_weight.value`,
                message: t(
                  'Maximum takeoff weight must be greater than empty weight',
                ),
              }),
            );
            errors.push(
              this.createError({
                path: `${this.path}.empty_weight.value`,
                message: t(
                  'Maximum takeoff weight must be greater than empty weight',
                ),
              }),
            );
            return new yup.ValidationError(errors);
          }
          return true;
        },
      ),
    cargo_compartments: yup.object({
      dimensions: yup.object({
        length: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Length must be a number'))
            .required(t('Temperature Length is required')),
        }),
        width: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Width must be a number'))
            .required(t('Temperature Width is required')),
        }),
        height: yup.object({
          value: yup
            .number()
            .typeError(t('Temperature Height must be a number'))
            .required(t('Temperature Height is required')),
        }),
      }),
      weight_capacity: yup.object({
        value: yup
          .number()
          .typeError(t('Weight Capacity must be a number'))
          .required(t('Weight Capacity is required')),
      }),
    }),

    packaging_specifications: yup.array().of(
      yup.object({
        name: yup.string(),
        order: yup.number(),
        specifications: yup.array().of(
          yup.object({
            value: yup
              .mixed()
              .required(t('Packaging specification is required')),
            type: yup.string(),
          }),
        ),
      }),
    ),

    flight_performance: yup.object({
      operating_altitude: yup
        .object({
          from: yup.object({
            value: yup.number().nullable(),
            unit: yup.string(),
          }),
          to: yup.object({
            value: yup.number().nullable(),
            unit: yup.string(),
          }),
        })
        .test(
          'validate-resolution',
          t('Next value must be greater than previous.'),
          function (operating_altitude) {
            const fromVal = operating_altitude?.from?.value;
            const toVal = operating_altitude?.to?.value;
            if (fromVal == null || toVal == null) {
              return true;
            }
            if (fromVal > toVal || fromVal == toVal) {
              const errors = [];
              errors.push(
                this.createError({
                  path: `${this.path}.from.value`,
                  message: t('Next value must be greater than previous.'),
                }),
              );
              errors.push(
                this.createError({
                  path: `${this.path}.to.value`,
                  message: t('Next value must be greater than previous.'),
                }),
              );
              return new yup.ValidationError(errors);
            }
            return true;
          },
        ),
    }),
    propulsion_system: yup.object({
      number_of_motors: yup
        .number()
        .typeError('Must be a number')
        .integer('Must be an integer')
        .min(-2147483648, 'Minimum value is -2,147,483,648')
        .max(2147483647, 'Maximum value is 2,147,483,647')
        .nullable(),
      flight_time: yup.object({
        value: yup
          .number()
          .nullable()
          .min(1, t('Flight time must be greater than 0'))
          .required(t('Flight time is required')),
      }),
    }),
    device_protocols: yup.array().of(
      yup
        .object({
          type_of_protocol: yup.object({
            value: yup.mixed().nullable(),
          }),
          protocol: yup.object({
            value: yup.mixed().nullable(),
          }),
        })
        .test(
          'require-protocol-if-type-selected',
          t('Protocol is required when Type of Protocol is selected'),
          function (value) {
            const type = value?.type_of_protocol?.value;
            const protocol = value?.protocol?.value;

            if (type && !protocol) {
              return this.createError({
                path: `${this.path}.protocol.value`,
                message: t(
                  'Protocol is required when Type of Protocol is selected',
                ),
              });
            }
            return true;
          },
        ),
    ),
    manufacturer_information: yup.object({
      registration_number: yup
        .string()
        .nullable()
        .matches(/^[A-Za-z][A-Za-z0-9]*$/, {
          message: t(
            'The registration number must be a combination of uppercase letters and numbers.',
          ),
          excludeEmptyString: true,
        }),
    }),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      data: yup.object({
        ...baseSchema,
        group: yup
          .object({
            value: yup.number().required(t('Group is required')),
            label: yup.string(),
            code: yup.string(),
          })
          .required(t('Group is required')),
      }),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    data: yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().nullable(),
          label: yup.string(),
          code: yup.string(),
        })
        .nullable(),
    }),
  });
};

export const schemaPackaging = (
  tFunc?: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const translate = tFunc || t;

  const baseSchema = {
    name: yup.string().required(translate('Name is required')),
    dimensions: yup.object({
      length: yup.object({
        value: yup.number().required(translate('Length is required')),
        unit: yup.string().required(translate('Unit is required')),
      }),
      width: yup.object({
        value: yup.number().required(translate('Width is required')),
        unit: yup.string().required(translate('Unit is required')),
      }),
      height: yup.object({
        value: yup.number().required(translate('Height is required')),
        unit: yup.string().required(translate('Unit is required')),
      }),
    }),
    maximum_weight: yup.object({
      value: yup.number().required(translate('Maximum weight is required')),
      unit: yup.string().required(translate('Unit is required')),
    }),
    package_type_id: yup.object({
      value: yup.mixed().required(translate('Package type is required')),
    }),
    // water_proof: yup.boolean().required(t("Waterproof is required")),
    // fragile: yup.boolean().required(t("Fragile is required")),
    // note: yup.string().required(t("Note is required")),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup.object({
        value: yup
          .object({
            value: yup.number().required(translate('Group is required')),
            label: yup.string(),
          })
          .required(translate('Group is required')),
      }),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup
          .object({
            value: yup.number().nullable(),
            label: yup.string(),
          })
          .nullable(),
      })
      .nullable(),
  });
};

export const schemaOtherEquipments = (
  tFunc?: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const translate = tFunc || t;

  const baseSchema = {
    data: yup.object({
      name: yup.string().required(translate('Name is required')),
      resolution: yup
        .object({
          width: yup.object({
            value: yup.number().required(translate('This field is required')),
            unit: yup.string().required(translate('This field is required')),
          }),
          height: yup.object({
            value: yup.number().required(translate('This field is required')),
            unit: yup.string().required(translate('This field is required')),
          }),
        })
        .test(
          'validate-resolution',
          t('Next value must be smaller than previous.'),
          function (resolution) {
            const widthVal = resolution?.width?.value;
            const heightVal = resolution?.height?.value;
            if (
              (widthVal != null && heightVal != null && widthVal < heightVal) ||
              widthVal == heightVal
            ) {
              const errors = [];
              errors.push(
                this.createError({
                  path: `${this.path}.width.value`,
                  message: translate(
                    'Next value must be smaller than previous.',
                  ),
                }),
              );
              errors.push(
                this.createError({
                  path: `${this.path}.height.value`,
                  message: translate(
                    'Next value must be smaller than previous.',
                  ),
                }),
              );
              return new yup.ValidationError(errors);
            }
            return true;
          },
        ),
      frame_rate: yup.object({
        value: yup.number().required(translate('Frame rate is required')),
      }),
      field_of_view: yup.object({
        value: yup
          .array()
          .of(yup.number())
          .required(translate('Field of view is required')),
      }),
      weight: yup
        .object({
          min: yup.object({
            value: yup.number().required(translate('This field is required')),
            unit: yup.string().required(translate('This field is required')),
          }),
          max: yup.object({
            value: yup.number().required(translate('This field is required')),
            unit: yup.string().required(translate('This field is required')),
          }),
        })
        .test(
          'validate-weight',
          translate('Min must be less than max'),
          function (weight) {
            const minVal = weight?.min?.value;
            const maxVal = weight?.max?.value;
            if (
              (minVal != null && maxVal != null && minVal > maxVal) ||
              minVal == maxVal
            ) {
              const errors = [];
              errors.push(
                this.createError({
                  path: `${this.path}.min.value`,
                  message: translate('Min must be less than max'),
                }),
              );
              errors.push(
                this.createError({
                  path: `${this.path}.max.value`,
                  message: translate('Min must be less than max'),
                }),
              );
              return new yup.ValidationError(errors);
            }
            return true;
          },
        ),
    }),

    image_stabilization: yup.object({
      value: yup.number().nullable(),
    }),
    note: yup.string(),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(translate('Group is required')),
          label: yup.string(),
        })
        .required(translate('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaRoute = (
  tFunc?: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const translate = tFunc || t;

  const baseSchema = {
    name: yup.string().required(translate('Name is required')),
    code: yup.string().required(translate('Code is required')),
    service: yup
      .object({
        value: yup.number().required(translate('Service is required')),
        label: yup.string(),
      })
      .required(translate('Service is required')),
    terminals: yup
      .array()
      .of(
        yup.object({
          cruise_speed: yup
            .string()
            .required(translate('Cruise speed is required')),
          operating_altitude: yup
            .string()
            .required(translate('Operating altitude is required')),
          time_stops: yup.string().required(translate('Hold time is required')),
          frame: yup.object().required(translate('Frame is required')),
          command: yup.object({
            command_terminal: yup
              .object()
              .required(translate('Command terminal is required')),
            frame_1: yup.string().required(translate('Frame 1 is required')),
            frame_2: yup.string().required(translate('Frame 2 is required')),
            frame_3: yup.string().required(translate('Frame 3 is required')),
            frame_4: yup.string().required(translate('Frame 4 is required')),
          }),
        }),
      )
      .optional(),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(translate('Group is required')),
          label: yup.string(),
        })
        .required(translate('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaDeliveryInquiry = yup.object({
  data: yup.object({
    sender: yup.object({
      name: yup.string().required(t('Name is required')),
      phoneNumber: yup
        .string()
        .required('Phone number is required')
        .matches(
          /^01[016789][0-9]{7,8}$/,
          'Phone number must be 10 or 11 digits and valid Korean format',
        ),
      location_id: yup
        .object({
          value: yup.object().required(t('Location is required')),
          type: yup.string(),
        })
        .required(t('Location is required')),
    }),
    recipient: yup.object({
      name: yup.string().required(t('Name is required')),
      phoneNumber: yup
        .string()
        .required('Phone number is required')
        .matches(/^01[016789][0-9]{7,8}$/, 'Invalid Korean phone number'),
      city_province: yup.object().required(t('Location is required')),
      city_county_district: yup.object().required(t('Location is required')),
      ward_town_township: yup.object().required(t('Location is required')),
      street_address: yup.string().required(t('Street address is required')),
      note: yup.string(),
    }),
    // // delivery_option: yup
    // //     .string()
    // //     .required(t("Delivery option is required")),

    // delivery_location_id: yup.object({
    //     value: yup.object().required(t("Location is required")),
    //     type: yup.string()
    // }).required(t("Location is required")),

    // delivery_option: yup.string().oneOf(['collect_at_location']).required(),
    // delivery_location_id: yup.object({
    //     value: yup.object().required('Location is required'),
    //     type: yup.string()
    // }).when('delivery_option', {
    //     is: 'collect_at_location',
    //     then: yup.object().shape({
    //         value: yup.object().required('Location is required'),
    //         type: yup.string()
    //     }).required('Location is required')
    // }),
    package: yup.array().of(
      yup.object({
        package_weight: yup.object({
          value: yup.number().required(t('Package weight is required')),
          unit: yup.string().required(t('Unit is required')),
        }),
        dimensions: yup.object({
          length: yup.object({
            value: yup
              .number()
              .typeError(t('Temperature Length must be a number'))
              .required(t('Temperature Length is required')),
          }),
          width: yup.object({
            value: yup
              .number()
              .typeError(t('Temperature Width must be a number'))
              .required(t('Temperature Width is required')),
          }),
          height: yup.object({
            value: yup
              .number()
              .typeError(t('Temperature Height must be a number'))
              .required(t('Temperature Height is required')),
          }),
        }),
      }),
    ),

    // package: yup.array().of(),
  }),
});

export const schemaTerminal = (
  tFunc?: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const translate = tFunc || t;
  const baseSchema = {
    code: yup.string().required(translate('ID is required')),
    name: yup.string().required(translate('Name is required')),
    terminal_type_ids: yup
      .array()
      .min(1, translate('Type is required'))
      .of(
        yup.object({
          value: yup.number(),
          label: yup.string(),
          code: yup.string(),
        }),
      )
      .required(translate('Type is required')),

    function_ids: yup
      .array()
      .min(1, translate('Function is required'))
      .of(
        yup.object({
          value: yup.string(),
          label: yup.string(),
        }),
      )
      .required(translate('Function is required')),

    terminal_purpose_id: yup
      .object({
        value: yup.string().nullable(),
        label: yup.string().nullable(),
      })
      .nullable()
      .when('terminal_type_ids', {
        is: (terminal_type_ids: any) =>
          Array.isArray(terminal_type_ids) &&
          terminal_type_ids.some((item) => item.code === 'INFRASTRUCTURE'),
        then: (schema) =>
          schema.required(translate('Major Category is required')),
        otherwise: (schema) => schema.nullable(),
      }),
    purpose_type_id: yup
      .object({
        value: yup.string().nullable(),
        label: yup.string().nullable(),
      })
      .nullable()
      .when('terminal_type_ids', {
        is: (terminal_type_ids: any) =>
          Array.isArray(terminal_type_ids) &&
          terminal_type_ids.some((item) => item.code === 'INFRASTRUCTURE'),
        then: (schema) => schema.required(translate('Purpose is required')),
        otherwise: (schema) => schema.nullable(),
      }),

    time_stops: yup.object({
      value: yup
        .number()
        .typeError(translate('Time stops must be a number'))
        .required(translate('Time stops is required')),
      unit: yup.string().required(translate('Unit is required')),
    }),
    latitude: yup
      .number()
      .typeError(translate('Latitude must be a number.'))
      .required(translate('Latitude is required'))
      .test(
        'is-decimal',
        translate('Latitude must be a decimal number.'),
        (value) => (value !== undefined ? value % 1 !== 0 : true),
      ),
    longitude: yup
      .number()
      .typeError(translate('Longitude must be a number.'))
      .required(translate('Longitude is required'))
      .test(
        'is-decimal',
        translate('Longitude must be a decimal number.'),
        (value) => (value !== undefined ? value % 1 !== 0 : true),
      ),
    full_address: yup.string().required(translate('Address is required')),
    exceptions: yup.array().of(
      yup.object({
        exception_date: yup
          .string()
          .required(translate('Exception date is required')),
        start_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean = false) => !is_all_day,
          then: (schema) =>
            schema.required(translate('Start time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        end_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean) => !is_all_day,
          then: (schema) => schema.required(translate('End time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        // is_all_day: yup.boolean().required(translate('Is all day is required')),
        // reason: yup.string().required(translate('Reason is required')),
      }),
    ),
  };

  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(translate('Group is required')),
          label: yup.string(),
          code: yup.string(),
        })
        .required(translate('Group is required')),
    });
  }

  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
        code: yup.string(),
      })
      .nullable(),
  });
};

export const schemaWaybillTemplate = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaCancelOrder = yup.object({
  reason: yup.string().required(t('Reason is required')),
});

export const schemaRefundCash = yup.object({
  bank_name: yup.object({
    value: yup.mixed().required(t('Bank name is required')),
  }),
  account_holder_name: yup
    .string()
    .required(t('Account holder name is required')),
  account_number: yup.string().required(t('Account number is required')),
});

export const schemaLogin = yup.object({
  username: yup.string().required(t('Username is required')),
  password: yup.string().required(t('Password is required')),
});

export const schemaForgotPassword = yup.object({
  email: yup
    .string()
    .email('Invalid email format')
    .required(t('Email is required')),
});

export const schemaNewPassword = yup.object({
  newPwd: yup
    .string()
    .min(4, `Password must be at least ${4} characters`)
    .matches(/[A-Z]/, 'Must include at least one uppercase letter')
    .matches(/[a-z]/, 'Must include at least one lowercase letter')
    .matches(/[0-9]/, 'Must include at least one number')
    .matches(/[\W_]/, 'Must include at least one special character')
    .required(t('Password is required')),
  confirmPwd: yup
    .string()
    .oneOf([yup.ref('newPwd')], 'Passwords do not match')
    .required(t('Password is required')),
});

// Helper function validate JSON
const validateJson = (fieldName: string) => {
  return yup
    .string()
    .test('is-json', t(`${fieldName} must be valid JSON`), function (value) {
      if (!value || !value.trim()) return true; // Required validation sẽ handle empty
      try {
        const parsed = JSON.parse(value);

        if (parsed === null) {
          return this.createError({
            message: t(`${fieldName} cannot be null. Use {} for empty object`),
          });
        }

        return true;
      } catch {
        return false;
      }
    });
};

export const schemaOperationSetting = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    is_active: yup.boolean().required(t('Is Active is required')),
    api_url: yup.string().required(t('URL is required')),
    http_method: yup.string().when('is_active', {
      is: true,
      then: (schema) => schema.required(t('HTTP Method is required')),
      otherwise: (schema) => schema.notRequired(),
    }),
    api_params: yup.string().when(['is_active', 'http_method'], {
      is: (is_active: boolean, http_method: string) =>
        is_active && ['GET', 'PUT', 'PATCH', 'DELETE'].includes(http_method),
      then: (schema) =>
        schema.required(t('Param is required')).concat(validateJson('Param')),
      otherwise: (schema) => schema.notRequired(),
    }),
    body_params: yup.string().when(['is_active', 'http_method'], {
      is: (is_active: boolean, http_method: string) =>
        is_active && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(http_method),
      then: (schema) =>
        schema.required(t('Body is required')).concat(validateJson('Body')),
      otherwise: (schema) => schema.notRequired(),
    }),
    expected_response: yup.string().when('is_active', {
      is: true,
      then: (schema) =>
        schema
          .required(t('Response is required'))
          .concat(validateJson('Response')),
      otherwise: (schema) => schema.notRequired(),
    }),
    send_data: yup.boolean().required(t('Send Data is required')),
    receive_data: yup.boolean().required(t('Receive Data is required')),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const addNewEtriOrderSchema = (t: TFunction) =>
  yup.object({
    data: yup.object({
      sender: yup.object({
        name: yup.string().required(t('Name is required')),
        phone_number: yup
          .string()
          .required('Phone number is required')
          .matches(
            /^[0-9]{10,11}$/,
            t('The phone number must be a valid Korean phone number.'),
          ),
        address_type: yup.string(),
        full_address: yup.string().required(t('Address is required')),
        latitude: yup.string().required(t('Address is required')),
        longitude: yup.string().required(t('Address is required')),
        street_address: yup.string().nullable(),
        city_province: yup.mixed().nullable(),
        city_county_district: yup.mixed().nullable(),
        ward_town_township: yup.mixed().nullable(),
        postal_code: yup.string().nullable(),
        address_detail: yup.string(),
        location_id: yup.object({
          value: yup
            .object({
              label: yup.string(),
              value: yup.number(),
            })
            .required(t('Terminal is required')),
          type: yup.string(),
        }),
      }),
      recipient: yup.object({
        name: yup.string().required(t('Name is required')),
        phone_number: yup
          .string()
          .required('Phone number is required')
          .matches(
            /^[0-9]{10,11}$/,
            t('The phone number must be a valid Korean phone number.'),
          ),
        address_type: yup.string(),
        full_address: yup.string().required(t('Address is required')),
        latitude: yup.string().required(t('Latitude is required')),
        longitude: yup.string().required(t('Longitude is required')),
        street_address: yup.string().nullable(),
        city_province: yup.mixed().nullable(),
        city_county_district: yup.mixed().nullable(),
        ward_town_township: yup.mixed().nullable(),
        postal_code: yup.string().nullable(),
        note: yup.string(),
        address_detail: yup.string(),
      }),
      package: yup
        .array()
        .of(
          yup.object().shape({
            package_weight: yup.object().shape({
              value: yup
                .number()
                .typeError(t('Weight must be a number'))
                .max(40, t('Weight cannot exceed 40 kg'))
                .required(t('Weight is required')),
              unit: yup.string().required(t('Unit is required')),
            }),
            dimensions: yup.object().shape({
              length: yup.object().shape({
                value: yup
                  .number()
                  .typeError(t('Length must be a number'))
                  .max(38, t('entri_order.dimension_requirement'))
                  .required(t('Length is required')),
                unit: yup.string().required(t('Unit is required')),
              }),
              width: yup.object().shape({
                value: yup
                  .number()
                  .typeError(t('Width must be a number'))
                  .max(48, t('entri_order.dimension_requirement'))
                  .required(t('Width is required')),
                unit: yup.string().required(t('Unit is required')),
              }),
              height: yup.object().shape({
                value: yup
                  .number()
                  .typeError(t('Height must be a number'))
                  .max(34, t('entri_order.dimension_requirement'))
                  .required(t('Height is required')),
                unit: yup.string().required(t('Unit is required')),
              }),
            }),
            item_type: yup.object().shape({
              value: yup
                .object()
                .shape({
                  label: yup.string(),
                  value: yup.number(),
                })
                .required(t('Item type is required')),
              type: yup.string(),
            }),
          }),
        )
        .min(1, t('At least one package is required')),
    }),
  });

export const schemaInfrastructure = (
  t: TFunction,
  isRoleSuperuser: boolean,
) => {
  const baseSchema = {
    code: yup.string().required(t('ID is required')),
    name: yup.string().required(t('Name is required')),
    function_ids: yup.lazy((value) => {
      const objectSchema = yup.object({
        value: yup.string(),
        label: yup.string(),
      });
      if (Array.isArray(value)) {
        return yup
          .array()
          .of(objectSchema)
          .required(t('Minor Category is required'));
      }
      return objectSchema.required(t('Minor Category is required'));
    }),
    terminal_purpose_id: yup.lazy((value) => {
      const objectSchema = yup.object({
        value: yup.string(),
        label: yup.string(),
      });
      if (Array.isArray(value)) {
        return yup
          .array()
          .of(objectSchema)
          .required(t('Major Category is required'));
      }
      return objectSchema.required(t('Major Category is required'));
    }),
    full_address: yup.string().required(t('Address is required')),
    latitude: yup
      .number()
      .typeError('Latitude must be a number.')
      .required(t('Latitude is required'))
      .test('is-decimal', 'Latitude must be a decimal number.', (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),
    longitude: yup
      .number()
      .typeError('Longitude must be a number.')
      .required(t('Longitude is required'))
      .test('is-decimal', 'Longitude must be a decimal number.', (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),
    purpose_type_id: yup
      .object({
        value: yup.string(),
        label: yup.string(),
      })
      .required(t('Purpose is required')),
    exceptions: yup.array().of(
      yup.object({
        exception_date: yup.string().required(t('Exception date is required')),
        start_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean = false) => !is_all_day,
          then: (schema) => schema.required(t('Start time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        end_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean) => !is_all_day,
          then: (schema) => schema.required(t('End time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        // is_all_day: yup.boolean().required(translate('Is all day is required')),
        // reason: yup.string().required(translate('Reason is required')),
      }),
    ),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required('Group is required'),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaDockingStation = (
  t: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const baseSchema = {
    code: yup.string().required(t('ID is required')),
    name: yup.string().required(t('Name is required')),
    full_address: yup.string().required(t('Address is required')),
    function_ids: yup.lazy((value) => {
      const objectSchema = yup.object({
        value: yup.string(),
        label: yup.string(),
        code: yup.string(),
      });
      if (Array.isArray(value)) {
        return yup
          .array()
          .of(objectSchema)
          .required(t('Terminal type is required'));
      }
      return objectSchema.required(t('Terminal type is required'));
    }),
    time_stops: yup.object({
      value: yup.number().required(t('Time stops is required')),
      unit: yup.string().required(t('Unit is required')),
    }),

    latitude: yup
      .number()
      .typeError(t('Latitude must be a number.'))
      .required(t('Latitude is required'))
      .test('is-decimal', t('Latitude must be a decimal number.'), (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),

    longitude: yup
      .number()
      .typeError(t('Longitude must be a number.'))
      .required(t('Longitude is required'))
      .test('is-decimal', t('Longitude must be a decimal number.'), (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),
    temperature_range: yup
      .object({
        from: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
        to: yup.object({
          value: yup.number().nullable(),
          unit: yup.string(),
        }),
      })
      .test(
        'validate-temperature-range',
        t('Next value must be greater than previous.'),
        function (temperature_range) {
          const fromVal = temperature_range?.from?.value;
          const toVal = temperature_range?.to?.value;

          if (
            fromVal === null ||
            toVal === null ||
            fromVal === undefined ||
            toVal === undefined
          ) {
            return true;
          }

          if (typeof fromVal === 'number' && typeof toVal === 'number') {
            if (fromVal >= toVal) {
              return this.createError({
                path: `${this.path}.to.value`,
                message: t('Next value must be greater than previous.'),
              });
            }
          }

          return true;
        },
      ),
    exceptions: yup.array().of(
      yup.object({
        exception_date: yup.string().required(t('Exception date is required')),
        start_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean = false) => !is_all_day,
          then: (schema) => schema.required(t('Start time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        end_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean) => !is_all_day,
          then: (schema) => schema.required(t('End time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
      }),
    ),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const formRegisterDeliveryHubs = (
  t: TFunction,
  isRoleSuperuser: boolean = false,
) => {
  const baseSchema = {
    code: yup.string().required(t('ID is required')),
    name: yup.string().required(t('Name is required')),
    is_docking_station: yup.boolean(),
    function_ids: yup.lazy((value) => {
      const objectSchema = yup.object({
        value: yup.string(),
        label: yup.string(),
        code: yup.string(),
      });
      if (Array.isArray(value)) {
        return yup
          .array()
          .of(objectSchema)
          .required(t('Terminal type is required'));
      }

      return objectSchema.required(t('Terminal type is required'));
    }),
    address: yup.string().required(t('Address is required')),

    latitude: yup
      .number()
      .typeError(t('Latitude must be a number.'))
      .required(t('Latitude is required'))
      .test('is-decimal', t('Latitude must be a decimal number.'), (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),

    longitude: yup
      .number()
      .typeError(t('Longitude must be a number.'))
      .required(t('Longitude is required'))
      .test('is-decimal', t('Longitude must be a decimal number.'), (value) =>
        value !== undefined ? value % 1 !== 0 : true,
      ),

    exceptions: yup.array().of(
      yup.object({
        exception_date: yup.string().required(t('Exception date is required')),
        start_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean = false) => !is_all_day,
          then: (schema) => schema.required(t('Start time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        end_time: yup.string().when('is_all_day', {
          is: (is_all_day: boolean) => !is_all_day,
          then: (schema) => schema.required(t('End time is required')),
          otherwise: (schema) => schema.nullable(),
        }),
        // is_all_day: yup.boolean().required(translate('Is all day is required')),
        // reason: yup.string().required(translate('Reason is required')),
      }),
    ),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
          code: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
        code: yup.string(),
      })
      .nullable(),
  });
};

export const schemaOperationalNotice = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
    active: yup.boolean(),
    contentSections: yup.array().of(
      yup.object({
        id: yup.string().required(),
        title: yup.string().required(),
        content: yup.string(),
      }),
    ),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
          code: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
        code: yup.string(),
      })
      .nullable(),
  });
};

// Dynamic schema for ReportTemplate based on user role
export const reportTemplateSchema = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    name: yup.string().required(t('Name is required')),
    is_enabled: yup.boolean(),
    is_default: yup.boolean(),
    template: yup.string(),
  };

  // Add group validation only for superuser
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  // For non-superuser, group is optional
  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaChecklistSetting = (isRoleSuperuser: boolean) => {
  const baseSchema = {
    id: yup.number(),
    item_name: yup
      .object({
        en: yup.string().nullable(),
        ko: yup.string().nullable(),
        th: yup.string().nullable(),
      })
      .test(
        'at-least-one',
        'Item name is required in at least one language',
        function (values) {
          const { en, ko, th } = values || {};
          return (
            !!(en && en.trim()) || !!(ko && ko.trim()) || !!(th && th.trim())
          );
        },
      ),
    category: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .required(t('Category is required')),
  };

  // Conditional group validation based on user role
  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number().required(t('Group is required')),
          label: yup.string(),
        })
        .required(t('Group is required')),
    });
  }

  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number().nullable(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const schemaOrderStatus = yup.object({
  id: yup.number().nullable(),
  name: yup
    .object({
      en: yup.string().nullable(),
      ko: yup.string().nullable(),
      th: yup.string().nullable(),
    })
    .test(
      'at-least-one',
      'Name is required in at least one language',
      function (values) {
        const { en, ko, th } = values || {};
        return (
          !!(en && en.trim()) || !!(ko && ko.trim()) || !!(th && th.trim())
        );
      },
    ),
  value: yup.string().required(t('Value is required')),
  text_color: yup.string(),
  background_color: yup.string(),
  border_color: yup.string(),
  no_background_color: yup.boolean(),
  no_border_color: yup.boolean(),
});

export const schemaOrderStatusIsSuperuser = yup.object({
  id: yup.number().nullable(),
  name: yup
    .object({
      en: yup.string().nullable(),
      ko: yup.string().nullable(),
      th: yup.string().nullable(),
    })
    .test(
      'at-least-one',
      'Name is required in at least one language',
      function (values) {
        const { en, ko, th } = values || {};
        return (
          !!(en && en.trim()) || !!(ko && ko.trim()) || !!(th && th.trim())
        );
      },
    ),
  value: yup.string().required(t('Value is required')),
  text_color: yup.string(),
  background_color: yup.string(),
  border_color: yup.string(),
  group: yup
    .object({
      value: yup.number(),
      label: yup.string(),
    })
    .required(t('Group is required')),
  no_background_color: yup.boolean(),
  no_border_color: yup.boolean(),
});

export const schemaMappingStatus = yup.object({
  id: yup.number().nullable(),
});

export const schemaMappingStatusIsSuperuser = yup.object({
  id: yup.number().nullable(),
  group: yup
    .object({
      value: yup.number(),
      label: yup.string(),
    })
    .required(t('Group is required')),
});

export const schemaPartner = (tFunc?: TFunction) => {
  const translate = tFunc || t;
  return yup.object({
    name: yup.string().required(translate('Name is required')),
    service_key: yup.string().required(translate('ServiceKey​ is required')),
    expired_days: yup
      .number()
      .required(translate('Expired days is required'))
      .min(1, translate('Expired days must be greater than 0')),
    group: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .notRequired(),
    api_callback_url: yup.object({
      DroneUserNotice: yup
        .string()
        .url(translate('DroneUserNotice​ must be a valid URL'))
        .required(translate('DroneUserNotice​ is required')),
      DroneBaseStation: yup
        .string()
        .url(translate('DroneBaseStation​ must be a valid URL'))
        .required(translate('DroneBaseStation​ is required')),
      DeliveryStatusCallback: yup
        .string()
        .url(translate('DeliveryStatusCallback​ must be a valid URL'))
        .required(translate('DeliveryStatusCallback​ is required')),
    }),
  });
};

export const validatePhoneByMask = (value: string, maskType: string) => {
  if (!value?.trim()) return true;
  const digitsOnly = value.replace(/\D/g, '');
  const rules: Record<string, { min: number; max: number; message: string }> = {
    Kr: { min: 12, max: 13, message: t('Phone number of Korea is not valid') },
    En: { min: 11, max: 11, message: t('Phone number of USA is not valid') },
    Th: {
      min: 11,
      max: 12,
      message: t('Phone number of Thailand is not valid'),
    },
  };
  const rule = rules[maskType];
  if (rule && (digitsOnly.length < rule.min || digitsOnly.length > rule.max)) {
    return rule.message;
  }

  return true;
};

export const surveyMissionSchema = (
  isRoleSuperuser: boolean,
  drawingMode?: string,
) => {
  const baseSchema = {
    name: yup.string().nullable().required(t('Name is required')),
    return: yup.boolean(),
    maximum_number_of_drones: yup
      .number()
      .nullable()
      .required(t('Maximum number of drones is required')),
    purpose: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .nullable()
      .required(t('Purpose is required')),
    region: yup.string().nullable(),
    log_collection: yup.boolean(),
    video_recording: yup.boolean(),
    video_analysis: yup.boolean(),
    total_distance: yup.number().nullable(),
    estimated_time: yup.number().nullable(),
    note: yup.string().nullable(),
    waypoints: yup
      .array()
      .min(1, t('At least one waypoint is required'))
      .required(t('Waypoints are required')),
    settings: yup.object().shape({
      altitude: yup.number().required(t('Altitude is required')),
      trigger_distance: yup
        .number()
        .required(t('Trigger distance is required')),
      overlap: yup.number().required(t('Overlap is required')),
      altitude_separation: yup
        .number()
        .required(t('Altitude separation is required')),
      takeoff_altitude: yup
        .number()
        .required(t('Takeoff altitude is required')),
      spacing: yup.number().required(t('Spacing is required')),
      angle: yup.number().required(t('Angle is required')),
      turnaround_distance: yup
        .number()
        .required(t('Turnaround distance is required')),
    }),
  };

  if (isRoleSuperuser) {
    return yup.object({
      ...baseSchema,
      group: yup
        .object({
          value: yup.number(),
          label: yup.string(),
        })
        .nullable()
        .required(t('Group is required')),
    });
  }

  return yup.object({
    ...baseSchema,
    group: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .nullable(),
  });
};

export const importSurveyMissionSchema = () => {
  return yup.object({
    route_ids: yup
      .array()
      .min(1, t('Route is required'))
      .required(t('Route is required')),
    name: yup.string().nullable().required(t('Name is required')),
    purpose_id: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .nullable()
      .required(t('Purpose is required')),
  });
};

export const schemaSurveillanceProfile = (tFunc?: TFunction) => {
  const translate = tFunc || t;
  return yup.object({
    name: yup.string().required(translate('Name is required')),
    mission_id: yup
      .object({
        value: yup.number().required(translate('Mission is required')),
        label: yup.string(),
      })
      .required(translate('Mission is required')),
    start_time: yup
      .string()
      .nullable()
      .required(translate('Start time is required')),
    operator_id: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .required(translate('Operator is required')),
    repeat_type_id: yup
      .object({
        value: yup.number(),
        label: yup.string(),
      })
      .required(translate('Repeat type is required')),

    repeat_until_type_id: yup.object().when('repeat_type_id', {
      is: (repeat_type_id: any) => repeat_type_id?.code !== 'none',
      then: (schema) =>
        schema.shape({
          value: yup.number().required(translate('Util is required')),
          label: yup.string(),
        }),
      otherwise: (schema) => schema.notRequired(),
    }),

    repeat_occurrences: yup
      .number()
      .nullable()
      .transform((value, originalValue) => {
        if (
          originalValue === '' ||
          originalValue === null ||
          originalValue === undefined
        ) {
          return null;
        }
        const num = Number(originalValue);
        return isNaN(num) ? null : num;
      })
      .typeError(translate('Occurrences must be a number'))
      .when('repeat_until_type_id.code', {
        is: 'after_occurrences',
        then: (schema) =>
          schema
            .required(translate('Occurrences is required'))
            .min(1, translate('Occurrences must be at least 1')),
      }),

    repeat_until_date: yup
      .string()
      .nullable()
      .when('repeat_until_type_id.code', {
        is: 'on_date',
        then: (schema) => schema.required(translate('Date is required')),
        otherwise: (schema) => schema.notRequired(),
      }),
    color_code: yup.string().required(translate('Color code is required')),

    takeoff_altitude: yup
      .number()
      .nullable()
      .required(translate('Takeoff altitude is required')),
    altitude_separation: yup
      .number()
      .nullable()
      .required(translate('Altitude separation is required')),
  });
};
