import React from 'react';
import { useController } from 'react-hook-form';
import { ConfigProvider, TimePicker } from 'antd';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';

// Standard format for storing/sending to backend (24h)
const STORAGE_TIME_FORMAT = 'HH:mm:ss';

type Props = {
	control: any;
	nameStart: string;
	nameEnd: string;
	disabled?: boolean;
	placeholder?: [string, string];
	style?: React.CSSProperties;
	errorMessage?: string;
	format?: string;
};

export default function CustomTimeRangePicker({
	control,
	nameStart,
	nameEnd,
	disabled = false,
	placeholder = ['Start', 'End'],
	style,
	format,
	errorMessage
}: Props) {

	const { i18n } = useTranslation();
	const [theme] = useTheme();
	const currentLocale = i18n.language || 'en';

	// Get start_time
	const {
		field: startField
	} = useController({
		control,
		name: nameStart
	});

	// Get end_time
	const {
		field: endField
	} = useController({
		control,
		name: nameEnd
	});

	// Prepare range value - parse from storage format (HH:mm:ss), apply locale for display
	const rangeValue =
		startField.value && endField.value
			? [
				dayjs(startField.value, STORAGE_TIME_FORMAT).locale(currentLocale),
				dayjs(endField.value, STORAGE_TIME_FORMAT).locale(currentLocale)
			]
			: null;

	return (
		<ConfigProvider
			locale={
				i18n.language === 'en'
					? enLocale
					: i18n.language === 'ko'
						? koLocale
						: thLocale
			}
			theme={{
				components: {
					TimePicker: {
						activeBg: theme === 'dark' ? '#1F1F20' : '#fff',
						hoverBg: theme === 'dark' ? '#2a2a2a' : '#f9f9f9',
						activeBorderColor:
							theme === 'dark'
								? 'var(--ga-primary)'
								: 'var(--ga-primary)',
						hoverBorderColor:
							theme === 'dark'
								? 'var(--ga-primary)'
								: 'var(--ga-primary)',
						cellActiveWithRangeBg:
							theme === 'dark' ? '#262626' : 'var(--ga-primary-4)',
						cellHoverBg:
							theme === 'dark'
								? 'var(--ga-primary)'
								: 'var(--ga-primary-4)',
					},
				},
				token: {
					colorText:
						theme === 'dark'
							? 'var(--ga-dark-theme-font-color)'
							: 'var(--ga-light-theme-font-color)',
					colorTextDisabled:
						theme === 'dark' ? '#777' : '#bfbfbf',
					colorBgContainer: theme === 'dark' ? '#141414' : '#fff',
					colorBgElevated: theme === 'dark' ? '#1f1f1f' : '#fff',
					colorPrimaryBorder:
						theme === 'dark'
							? 'var(--ga-dark-line-color)'
							: 'var(--ga-primary-2)',
					colorBorder: theme === 'dark' ? '#303030' : '#d9d9d9',
					colorIcon: theme === 'dark' ? '#bfbfbf' : '#595959',
					colorIconHover:
						theme === 'dark'
							? 'var(--ga-light-theme-font-color)'
							: 'var(--ga-primary)',
					colorBgContainerDisabled:
						theme === 'dark' ? '#262626' : '#f5f5f5',
					colorTextPlaceholder:
						theme === 'dark' ? '#8c8c8c' : '#bfbfbf',
					controlItemBgActive:
						theme === 'dark'
							? 'var(--ga-light-theme-font-color)'
							: 'var(--ga-primary-4)',
					colorBorderError:
						'#ff4d4f',
				},
			}}
		>
			<TimePicker.RangePicker
				className={"custom-datepicker"}
				format={format}
				value={rangeValue as any}
				disabled={disabled}
				placeholder={placeholder}
				status={errorMessage ? 'error' : undefined}
				style={{ ...style, height: '2.975rem' }}

				onChange={(times) => {
					if (times && times[0] && times[1]) {
						// Save in standard 24h format for backend
						startField.onChange(times[0].format(STORAGE_TIME_FORMAT));
						endField.onChange(times[1].format(STORAGE_TIME_FORMAT));
					} else {
						startField.onChange(null);
						endField.onChange(null);
					}
				}}
				disabledTime={(_, type) => {
					if (type === 'start') return {};

					if (startField.value) {
						// Parse from storage format
						const start = dayjs(startField.value, STORAGE_TIME_FORMAT);
						const startHour = start.hour();
						const startMinute = start.minute();

						return {
							disabledHours: () =>
								Array.from({ length: startHour }, (_, i) => i),
							disabledMinutes: (selectedHour: number) => {
								if (selectedHour === startHour) {
									return Array.from(
										{ length: startMinute + 1 },
										(_, i) => i
									);
								}
								return [];
							}
						};
					}

					return {};
				}}

				popupClassName={
					theme === 'dark'
						? 'custom-timepicker-dark'
						: 'custom-timepicker-light'
				}
			/>

			{errorMessage && (
				<div className="error-message">
					{errorMessage}
				</div>
			)}
		</ConfigProvider>
	);
}
