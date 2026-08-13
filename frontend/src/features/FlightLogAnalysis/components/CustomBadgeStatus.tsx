import { Badge } from 'antd';
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import '../assets/styles/CustomBadgeStatus.scss';
import { getColorStatus } from '../utils/getColorStatus';

export const CustomBadgeStatus = React.memo(
  ({
    status,
    label,
  }: {
    status: 'normal' | 'loading' | 'warning';
    label: string;
  }) => {
    const { t } = useTranslation();
    const [theme] = useTheme();
    const { backgroundColor, color } = useMemo(
      () =>
        getColorStatus({
          theme,
          status,
        }),
      [theme, status],
    );

    return (
      <Badge
        className="custom-badge-status"
        style={{
          backgroundColor: backgroundColor,
          padding: '0.25rem 0.75rem',
          borderRadius: '0.5rem',
          color: color,
          fontWeight: '600',
        }}
        dot={false}
        color={color}
        text={t(label)}
      />
    );
  },
);
