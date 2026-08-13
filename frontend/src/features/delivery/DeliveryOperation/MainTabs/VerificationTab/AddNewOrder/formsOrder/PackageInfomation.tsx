import { useCallback, useEffect, useRef, useState } from 'react';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { IoTrashOutline } from 'react-icons/io5';
import {
  CustomInputHookForm,
  ROLE_PERMISSION,
  useConfigSystem,
  useTheme,
  CustomBtn,
} from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import ExpanDropDown from '@/components/Form/ExpanDropDown';
import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';

import useAPI from '../../hooks/useAPI';
import './formOrder.scss';

const PackageInfomation = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { getPackageList } = useAPI();
  const { getOptionsByModel } = useCommonAPI();
  const [configSystem] = useConfigSystem();
  const activeAddMorePackages = configSystem['Add more packages']?.value;

  const { control, setValue, getValues, watch } = useFormContext();
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'data.package',
  });

  const [packageState, setPackageState] = useState<
    Record<
      number,
      {
        key: number;
        isReady: boolean;
        params: any;
      }
    >
  >({});

  // Ref to prevent infinite loops when updating form values
  const isUpdatingRef = useRef(false);
  const packageStateRef = useRef(packageState);

  // Keep ref in sync with state
  useEffect(() => {
    packageStateRef.current = packageState;
  }, [packageState]);

  console.log('packageState', packageState);

  // Helper get params of package
  const getPackageParams = useCallback(
    (index: number) => {
      const getValue = (field: string) =>
        getValues(`data.package.${index}.${field}`);
      return {
        weight: getValue('package_weight.value'),
        dimension_l: getValue('dimensions.length.value'),
        dimension_w: getValue('dimensions.width.value'),
        dimension_h: getValue('dimensions.height.value'),
        item_type: getValue('item_type.value'),
        is_waterproof: getValue('is_water_proof') || false,
        is_fragile: getValue('is_fragile') || false,
      };
    },
    [getValues],
  );

  // Helper check if package is ready
  const checkPackageReady = useCallback((params: any) => {
    return (
      params.weight != null &&
      params.weight !== '' &&
      params.dimension_l &&
      params.dimension_w &&
      params.dimension_h
    );
  }, []);

  // Update state for 1 package
  const updatePackageState = useCallback(
    (index: number, updates: Partial<(typeof packageState)[0]>) => {
      setPackageState((prev) => ({
        ...prev,
        [index]: { ...prev[index], ...updates },
      }));
    },
    [],
  );

  // Load options function with params
  const getPackageListWithParams = useCallback(
    (index: number) => {
      return async (
        search: string,
        loadedOptions: any[],
        { page = 1 } = {},
      ) => {
        const state = packageState[index];
        if (!state?.isReady) return { data: [], hasMore: false };

        try {
          return await getPackageList(state.params)(search, loadedOptions, {
            page,
          });
        } catch (error) {
          console.error(`API Error for package ${index}:`, error);
          return { data: [], hasMore: false };
        }
      };
    },
    [packageState, getPackageList],
  );

  // Watch changes optimize logic
  useEffect(() => {
    const subscription = watch((_, { name }) => {
      // Prevent infinite loops - ignore updates triggered by our own setValue calls
      if (isUpdatingRef.current) return;

      // Ignore changes to packaging.value field itself to prevent loops
      if (name?.includes('packaging.value')) {
        return;
      }

      if (!name?.startsWith('data.package.')) return;

      const index = parseInt(name.split('.')[2]);
      if (isNaN(index)) return;

      const params = getPackageParams(index);
      const isReady = checkPackageReady(params);
      const prevState = packageStateRef.current[index];

      // Check if packaging-related fields have changed to optimize logic
      const isPackagingField = [
        'package_weight',
        'dimensions',
        'item_type',
        'is_water_proof',
        'is_fragile',
      ].some((field) => name.includes(field));

      if (isPackagingField) {
        const hasParamsChanged =
          !prevState ||
          JSON.stringify(prevState.params) !== JSON.stringify(params);

        if (hasParamsChanged) {
          isUpdatingRef.current = true;
          const currentValue = getValues(
            `data.package.${index}.packaging.value`,
          );
          // Only set if value is not already empty
          if (
            currentValue !== '' &&
            currentValue !== null &&
            currentValue !== undefined
          ) {
            setValue(`data.package.${index}.packaging.value`, '', {
              shouldValidate: false,
              shouldDirty: false,
            });
          }
          isUpdatingRef.current = false;

          updatePackageState(index, {
            key: (prevState?.key || 0) + 1,
            params,
            isReady,
          });
          return;
        }
      }
      // Only update ready status if changed
      if (!prevState || prevState.isReady !== isReady) {
        updatePackageState(index, { isReady, params });
        if (!isReady) {
          isUpdatingRef.current = true;
          const currentValue = getValues(
            `data.package.${index}.packaging.value`,
          );
          // Only set if value is not already empty
          if (
            currentValue !== '' &&
            currentValue !== null &&
            currentValue !== undefined
          ) {
            setValue(`data.package.${index}.packaging.value`, '', {
              shouldValidate: false,
              shouldDirty: false,
            });
          }
          isUpdatingRef.current = false;
        }
      }
    });

    return () => subscription.unsubscribe();
  }, [
    watch,
    getPackageParams,
    checkPackageReady,
    setValue,
    getValues,
    updatePackageState,
  ]);

  // Initialize state for new packages
  useEffect(() => {
    const newState = { ...packageState };
    let hasChanges = false;

    fields.forEach((_, index) => {
      if (!newState[index]) {
        const params = getPackageParams(index);
        newState[index] = {
          key: 0,
          isReady: checkPackageReady(params),
          params,
        };
        hasChanges = true;
      }
    });

    if (hasChanges) setPackageState(newState);
  }, [fields.length]);

  const handleAddMore = () => {
    append({
      package_weight: { value: null, unit: 'kg' },
      dimensions: {
        length: { value: null, unit: 'mm' },
        width: { value: null, unit: 'mm' },
        height: { value: null, unit: 'mm' },
      },
      item_type: { value: '', type: 'select' },
      is_water_proof: false,
      is_fragile: false,
      packaging: { value: '', type: 'select' },
      note: '',
    });
  };

  const handleRemove = (index: number) => {
    remove(index);
    setPackageState((prev) => {
      const newState = { ...prev };
      delete newState[index];

      const reindexed: typeof packageState = {};
      Object.entries(newState).forEach(([key, value]) => {
        const oldIndex = parseInt(key);
        reindexed[oldIndex > index ? oldIndex - 1 : oldIndex] = value;
      });
      return reindexed;
    });
  };

  const renderDimensionInputs = (index: number) => (
    <div className="device-size">
      <div className="device-size__label">
        {t('Dimensions')} <span style={{ color: Colors.Red }}>*</span>
      </div>
      <div className={`device-size__dimensions ${theme}`}>
        {['length', 'width', 'height'].map((dim) => (
          <UnitInput
            key={dim}
            name={`data.package.${index}.dimensions.${dim}.value`}
            unit={getValues(`data.package.${index}.dimensions.${dim}.unit`)}
            iconDivider={dim !== 'height' ? 'x' : undefined}
            placeholder={t(dim.charAt(0).toUpperCase() + dim.slice(1))}
            onChange={(e) =>
              setValue(`data.package.${index}.dimensions.${dim}.value`, e)
            }
          />
        ))}
      </div>
    </div>
  );

  return (
    <div className={`form-container ${theme}`}>
      {fields.map((field, index) => (
        <ExpanDropDown
          key={field.id}
          label={`${t('Package')} ${index + 1}`}
        >
          <div className="relative">
            {index > 0 && (
              <div
                className="remove-icon-package mt-1 ms-auto"
                onClick={() => handleRemove(index)}
              >
                <IoTrashOutline
                  color={
                    theme === 'dark'
                      ? 'var(--ga-dark-theme-font-color)'
                      : 'var(--ga-light-theme-font-color)'
                  }
                  size={16}
                />
              </div>
            )}
            <div className="form-grid">
              <UnitInput
                label={t('Weight')}
                isRequired
                name={`data.package.${index}.package_weight.value`}
                unit={getValues(`data.package.${index}.package_weight.unit`)}
                placeholder="0"
                onChange={(e) =>
                  setValue(`data.package.${index}.package_weight.value`, e)
                }
              />
              {renderDimensionInputs(index)}
              <PaginationSelect
                label={t('Item Type')}
                required
                name={`data.package.${index}.item_type.value`}
                control={control}
                loadOptions={getOptionsByModel({
                  name_modal: 'OrderItemType',
                  search_field: 'name',
                })}
                placeholder={t('Select')}
              />

              <div className={theme}>
                <CustomCheckBox
                  name={`data.package.${index}.is_water_proof`}
                  label={t('Waterproof')}
                  control={control}
                />
                <CustomCheckBox
                  name={`data.package.${index}.is_fragile`}
                  label={t('Fragile')}
                  control={control}
                />
              </div>

              <PaginationSelect
                key={`package-${index}-${packageState[index]?.key || 0}`}
                required
                label={t('Packaging')}
                name={`data.package.${index}.packaging.value`}
                control={control}
                loadOptions={getPackageListWithParams(index)}
                placeholder={t('Select')}
                disabled={!packageState[index]?.isReady}
                description={
                  packageState[index]?.isReady
                    ? t(
                        'Please select the most suitable packaging specification.',
                      )
                    : t(
                        'Please enter Weight, Dimensions and Item Type to enable Packaging selection.',
                      )
                }
              />

              <CustomInputHookForm
                name={`data.package.${index}.note`}
                label={t('Note')}
                placeholder={t('Note')}
              />
            </div>
          </div>
        </ExpanDropDown>
      ))}

      {activeAddMorePackages && (
        <CustomBtn
          label={t('Add More')}
          type="button"
          variant="outline"
          style={{ color: 'var(--ga-primary)', width: 'fit-content' }}
          icon={<GoPlus size={18} />}
          className="add-more-button"
          onClick={handleAddMore}
          actionType={ROLE_PERMISSION.CREATE}
        />
      )}
    </div>
  );
};

export default PackageInfomation;
