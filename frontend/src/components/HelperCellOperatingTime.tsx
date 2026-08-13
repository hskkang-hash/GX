import TimePicker from 'antd/es/time-picker';
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import SwitchBtn from "@/components/Form/SwitchBtn";
import { ConfigProvider } from "antd";
import { useConfigSystem, useTheme, useUserInfo } from "rj-core";
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import { getTimeFormatString2 } from '@/features/Dashboard/utils/formatDateTime';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';

export interface OperatingTimeData {
	id?: number;
	day_of_week_id: number;
	is_active: boolean;
	start_time: string | null;
	end_time: string | null;
}

export interface ExceptionData {
	id?: number;
	exception_date: string | null;
	start_time: string | null;
	end_time: string | null;
	is_all_day: boolean;
	reason: string | null;
}

// Standard format for storing/sending to backend (24h)
const STORAGE_TIME_FORMAT = 'HH:mm:ss';

export const OperatingTimeSwitchCell = ({
	row,
	updateOperatingTimeByIndex,
}: {
	row: any;
	updateOperatingTimeByIndex: (index: number, field: keyof OperatingTimeData, value: any) => void;
}) => {
	const value = row?.row?.original?.is_active ?? true;

	return (
		<SwitchBtn
			statusValue={value}
			onChange={() => {
				const newValue = !value;
				updateOperatingTimeByIndex(row?.row?.index, 'is_active', newValue);
				// If deactivating, clear times; if activating, set defaults
				if (!newValue) {
					updateOperatingTimeByIndex(row?.row?.index, 'start_time', null);
					updateOperatingTimeByIndex(row?.row?.index, 'end_time', null);
				} else {
					// Store in standard 24h format for backend
					updateOperatingTimeByIndex(row?.row?.index, 'start_time', '08:00:00');
					updateOperatingTimeByIndex(row?.row?.index, 'end_time', '20:00:00');
				}
			}}
		/>
	);
};

export const StartTimeCellOperating = ({
	row,
	updateOperatingTimeByIndex,
	flagError,
}: {
	row: any;
	updateOperatingTimeByIndex: (index: number, field: keyof OperatingTimeData, value: any) => void;
	flagError?: boolean;
}) => {
	const { i18n } = useTranslation();
	const [theme] = useTheme();
	const isActive = row?.row?.original?.is_active ?? true;
	const userInfo = useUserInfo();
	const [configSystem] = useConfigSystem();
	const unitPreferences =
		configSystem && configSystem['system_default_formats'];
	const timeFormat = getTimeFormatString2(userInfo?.settings?.time_format__code ?? unitPreferences?.time_format ?? '24') ?? 'HH:mm';
	const timeValue = row?.row?.original?.start_time;  // Stored in HH:mm:ss format
	const currentLocale = i18n.language || 'en';

	// Parse from storage format (HH:mm:ss) for display
	const displayValue = timeValue ? dayjs(timeValue, STORAGE_TIME_FORMAT).locale(currentLocale) : null;

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
						disabledBg:
							theme === 'dark' ? '#262626' : '#f5f5f5',
					},
				},
				token: {
					colorBgContainerDisabled:
						theme === 'dark' ? '#262626' : '#f5f5f5',
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
			<TimePicker
				format={timeFormat}
				status={flagError ? "error" : undefined}
				value={displayValue}
				disabled={!isActive}
				onChange={(time) => {
					// Save in standard 24h format for backend
					const timeStr = time ? time.format(STORAGE_TIME_FORMAT) : '08:00:00';
					updateOperatingTimeByIndex(row?.row?.index, 'start_time', timeStr);
				}}
				placeholder=""
				style={{
					width: '100%',
					borderRadius: '0.5rem',
					// backgroundColor: theme === 'dark' ? '#1F1F20' : '',
				}}
				popupClassName={
					theme === 'dark'
						? 'custom-timepicker-dark'
						: 'custom-timepicker-light'
				}
			/>
		</ConfigProvider>
	);
};

export const EndTimeCellOperating = ({
	row,
	updateOperatingTimeByIndex,
	flagError,
}: {
	row: any;
	updateOperatingTimeByIndex: (index: number, field: keyof OperatingTimeData, value: any) => void;
	flagError?: boolean;
}) => {
	const { i18n } = useTranslation();
	const [theme] = useTheme();
	const isActive = row?.row?.original?.is_active ?? true;
	const userInfo = useUserInfo();
	const [configSystem] = useConfigSystem();
	const unitPreferences =
		configSystem && configSystem['system_default_formats'];
	const timeFormat = getTimeFormatString2(userInfo?.settings?.time_format__code ?? unitPreferences?.time_format ?? '24') ?? 'HH:mm';
	const currentLocale = i18n.language || 'en';
	const timeValue = row?.row?.original?.end_time || (isActive ? '20:00:00' : null);  // Stored in HH:mm:ss format
	const startTime = row?.row?.original?.start_time;  // Stored in HH:mm:ss format

	// Parse from storage format (HH:mm:ss) for display
	const displayValue = timeValue ? dayjs(timeValue, STORAGE_TIME_FORMAT).locale(currentLocale) : null;
	const startTimeValue = startTime ? dayjs(startTime, STORAGE_TIME_FORMAT) : null;

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
			<TimePicker
				className="custom-timepicker"
				format={timeFormat}
				status={flagError ? "error" : undefined}
				value={displayValue}
				disabled={!isActive}
				disabledTime={(current) => {
					if (!current || !startTimeValue) return {};
					const startHour = startTimeValue.hour();
					const startMinute = startTimeValue.minute();
					const currentHour = current.hour();
					const currentMinute = current.minute();

					// Disable hours before start hour
					if (currentHour < startHour) {
						return {
							disabledHours: () => Array.from({ length: startHour }, (_, i) => i),
							disabledMinutes: () => [],
						};
					}

					// If same hour, disable minutes before start minute
					if (currentHour === startHour) {
						return {
							disabledHours: () => [],
							disabledMinutes: () => Array.from({ length: startMinute + 1 }, (_, i) => i),
						};
					}

					return {};
				}}
				placeholder=""
				onChange={(time) => {
					// Save in standard 24h format for backend
					const timeStr = time ? time.format(STORAGE_TIME_FORMAT) : '20:00:00';
					updateOperatingTimeByIndex(row?.row?.index, 'end_time', timeStr);
				}}
				style={{
					width: '100%',
					borderRadius: '0.5rem',
					// backgroundColor: theme === 'dark' ? '#1F1F20' : '',
				}}
				popupClassName={
					theme === 'dark'
						? 'custom-timepicker-dark'
						: 'custom-timepicker-light'
				}
			/>
		</ConfigProvider>
	);
};
