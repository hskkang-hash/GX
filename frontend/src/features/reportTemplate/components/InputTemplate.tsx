import React, { useRef } from 'react';
import { Control, UseFormSetValue } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, FormBlock } from 'rj-core';

import CustomCheckBox from '../../../components/Form/CustomCheckBox';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { remToPx } from '../../../utils/utils';
import useCommonAPI from '../../useCommonAPI/useAPI';
import {
  FieldTemplate,
  ReportTemplateFormValues,
} from '../types/reportTemplate.types';
import CustomTiptap from './CustomTipTap';

const InputTemplate = ({
  fieldsTemplate,
  height,
  content,
  control,
  setValue,
}: {
  fieldsTemplate: FieldTemplate[];
  height: number;
  content: string;
  control: Control<ReportTemplateFormValues>;
  setValue: UseFormSetValue<ReportTemplateFormValues>;
}) => {
  const { t } = useTranslation();
  const innerTopRef = useRef<HTMLDivElement>(null);
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
            name="group"
            label={t('Group')}
            required
            control={control}
            placeholder={t('Select')}
            loadOptions={getOptionsByModel({
              name_modal: 'usergroup',
              search_field: 'name',
            })}
            className="flex-fill"
          />
        )}
        <CustomInputHookForm
          name="name"
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
          content={content}
          onChange={(value) => {
            setValue('template', value, { shouldDirty: true });
          }}
          heightContent={`${height - (innerTopRef.current?.clientHeight || 0) - remToPx(3)}px`}
          includeStyles={true}
          fieldsTemplate={fieldsTemplate}
        />
      </div>
    </FormBlock>
  );
};

export default React.memo(InputTemplate);
