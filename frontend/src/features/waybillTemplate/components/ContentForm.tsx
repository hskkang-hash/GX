import { useEffect } from 'react';
import { useState } from 'react';
import { useCalculateHeight } from 'rj-core';

import { remToPx } from '@/utils/utils';

import { convertFieldsAndData } from '../hooks/convertFields';
import useWaybill from '../hooks/useWaybill';
import { FieldTemplate } from '../type';
import FormTemplate from './FormTemplate';
import PreviewTemplate from './PreviewTemplate';

const ContentForm = ({
  headerPageRef,
}: {
  headerPageRef: React.RefObject<HTMLElement>;
}) => {
  const [fieldsTemplate, setFieldsTemplate] = useState<FieldTemplate[]>([]);
  const [dataExample, setDataExample] = useState<Record<string, any>>({});

  const { getFieldsTemplate } = useWaybill();

  useEffect(() => {
    if (fieldsTemplate.length === 0) {
      handleGetFieldsTemplate();
    }
  }, []);

  const handleGetFieldsTemplate = async () => {
    const response = await getFieldsTemplate();
    const result = await convertFieldsAndData(response[0].fields);

    setFieldsTemplate(result.fieldTemplate);
    setDataExample(result.data);
  };
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(1.5)],
  });

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
        <FormTemplate
          height={spaceTableHeight || 0}
          fieldsTemplate={fieldsTemplate}
          dataExample={dataExample}
        />
      </div>
      <div
        style={{
          width: '50%',
          height: '100%',
        }}
      >
        <PreviewTemplate
          height={spaceTableHeight || 0}
          dataExample={dataExample}
        />
      </div>
    </div>
  );
};

export default ContentForm;
