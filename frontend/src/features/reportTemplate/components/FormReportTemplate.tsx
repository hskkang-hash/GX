import React, { useEffect, useState } from 'react';
import { useFormContext } from 'react-hook-form';

import { isEmptyObject } from '../../../utils/utils';
import { convertFieldsAndData } from '../../waybillTemplate/hooks/convertFields';
import useReportTemplate from '../hooks/useReportTemplate';
import {
  FieldTemplate,
  ReportTemplateFormValues,
} from '../types/reportTemplate.types';
import InputTemplate from './InputTemplate';
import PreviewTemplate from './PreviewTemplate';

const FormReportTemplate = ({
  spaceTableHeight,
}: {
  spaceTableHeight: number;
}) => {
  const { control, setValue, watch } =
    useFormContext<ReportTemplateFormValues>();
  const [fieldsTemplate, setFieldsTemplate] = useState<FieldTemplate[]>([]);
  const [dataExample, setDataExample] = useState<
    Record<string, string | number | boolean | null | undefined>
  >({});
  const { getFieldsTemplate } = useReportTemplate();

  useEffect(() => {
    if (fieldsTemplate.length === 0 && isEmptyObject(dataExample)) {
      Promise.all([
        // getFieldsTemplate('Order'),
        getFieldsTemplate('DeliveryOperation'),
        // getFieldsTemplate('Device'),
      ]).then(async ([res1]) => {
        const result1 = await convertFieldsAndData(res1[0].fields);
        // const result2 = await convertFieldsAndData(res2[0].fields);
        // const result3 = await convertFieldsAndData(res3[0].fields);

        setFieldsTemplate([
          ...result1.fieldTemplate,
          // ...result2.fieldTemplate,
          // ...result3.fieldTemplate,
        ]);
        setDataExample({
          ...result1.data,
          // ...result2.data, ...result3.data
        });
      });
    }
  }, [fieldsTemplate, dataExample]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="d-flex gap-3"
      style={{ height: `${spaceTableHeight}px` }}
    >
      <div
        style={{
          width: '50%',
          height: '100%',
          flex: '0 0 50%',
        }}
      >
        <InputTemplate
          fieldsTemplate={fieldsTemplate}
          height={spaceTableHeight}
          content={watch('template') as string}
          control={control}
          setValue={setValue}
        />
      </div>
      <div
        style={{
          width: '50%',
          height: '100%',
        }}
      >
        <PreviewTemplate
          height={spaceTableHeight}
          dataExample={dataExample}
          templateContent={watch('template') as string}
        />
      </div>
    </div>
  );
};

export default React.memo(FormReportTemplate);
