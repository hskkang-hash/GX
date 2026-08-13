import { Badge } from 'antd';
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { getColorStatus } from '@/features/surveillanceProfile/utils/getColorStatus';

export const StatusBadge = React.memo(
	({
		status,
		theme,
	}: {
		status: 'normal' | 'loading' | 'error';
		theme: string;
	}) => {
		const { t } = useTranslation();
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
				style={{
					backgroundColor: backgroundColor,
					padding: '0.25rem 0.75rem',
					borderRadius: '0.5rem',
					color: color,
					fontWeight: '600',
				}}
				color={color}
				text={t(status.charAt(0).toUpperCase() + status.slice(1))}
			/>
		);
	},
);
