import React from 'react';
import { useTranslation } from 'react-i18next';
import { FormBlock, useTheme } from 'rj-core';

const DetailInfoSection = ({
  detailRows,
}: {
  detailRows: Array<
    Array<{ label: string; value: React.ReactNode; colSpan?: number }>
  >;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  return (
    <FormBlock>
      <p
        style={{
          fontWeight: 600,
          fontSize: '1.45rem',
          lineHeight: '140%',
          letterSpacing: '0%',
        }}
      >
        {t('Detailed Information')}
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {detailRows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              style={{
                border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
              }}
            >
              {row.map((item, i) => (
                <React.Fragment key={i}>
                  <td
                    style={{
                      padding: '0.875rem',
                      fontWeight: 'bold',
                      background: `${theme === 'dark' ? '#2D2E30' : '#ECECEF'}`,
                      border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
                      lineHeight: '140%',
                    }}
                  >
                    {item.label}
                  </td>
                  <td
                    colSpan={item.colSpan}
                    style={{
                      padding: '0.875rem',
                      border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
                    }}
                  >
                    {item.value}
                  </td>
                </React.Fragment>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </FormBlock>
  );
};

export default React.memo(DetailInfoSection);
