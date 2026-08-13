import { useRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, FormBlock } from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import { remToPx } from '@/utils/utils';

import PaginationSelect from '../../../components/selects/PaginationSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';
import { FieldTemplate } from '../type';
import CustomTiptap from './CustomTipTap';

const FormTemplate = ({
  height,
  fieldsTemplate,
  dataExample,
}: {
  height: number;
  fieldsTemplate: FieldTemplate[];
  dataExample: Record<string, any>;
}) => {
  const { t } = useTranslation();
  const innerTopRef = useRef<HTMLDivElement>(null);
  const { control, watch, setValue } = useFormContext();
  const { getOptionsByModel } = useCommonAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');

  return (
    <FormBlock className="h-100">
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isRoleSuperuser
            ? '3fr 3fr 1fr 1fr'
            : '7fr 1fr 1fr',
          gap: '1.5rem',
        }}
        ref={innerTopRef}
      >
        {isRoleSuperuser && (
          <PaginationSelect
            required
            label={t('Group')}
            name="group"
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'usergroup',
              search_field: 'name',
              key: 'name',
              value: 'id',
            })}
            placeholder={t('Select')}
          />
        )}
        <CustomInputHookForm
          name="name"
          control={control}
          label={t('Name')}
          placeholder={t('Name')}
          required
        />
        <CustomCheckBox
          name={'is_enabled'}
          label={t('Enabled')}
          subLabel={t('Yes')}
          control={control}
        />
        <CustomCheckBox
          name={'is_default'}
          label={t('Default')}
          subLabel={t('Yes')}
          control={control}
        />
      </div>
      <div className="mt-3">
        <CustomTiptap
          content={watch('template')}
          onChange={(value) => {
            setValue('template', value, { shouldDirty: true });
          }}
          heightContent={`${height - innerTopRef.current?.clientHeight - remToPx(3)}px`}
          includeStyles={true}
          fieldsTemplate={fieldsTemplate}
          dataExample={dataExample}
        />
      </div>
    </FormBlock>
  );
};

export default FormTemplate;
