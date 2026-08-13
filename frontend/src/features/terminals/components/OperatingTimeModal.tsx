import Colors from '@/configs/Colors';
import { Box } from '@mui/material';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import { useTranslation } from 'react-i18next';
import { CenterBtn, CustomModal, useTheme } from 'rj-core';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const dayOfWeekData = [
	{
		id: 1,
		day_of_week: 'Monday',
	},
	{
		id: 2,
		day_of_week: 'Tuesday',
	},
	{
		id: 3,
		day_of_week: 'Wednesday',
	},
	{
		id: 4,
		day_of_week: 'Thursday',
	},
	{
		id: 5,
		day_of_week: 'Friday',
	},
	{
		id: 6,
		day_of_week: 'Saturday',
	},
	{
		id: 7,
		day_of_week: 'Sunday',
	},
];

const STORAGE_TIME_FORMAT = 'HH:mm:ss';

const OperatingTimeModal = ({ show, onHide, data }: { show: boolean, onHide: () => void, data: any }) => {
	const { t, i18n } = useTranslation();
	const [theme] = useTheme();
	const operatingTimes = data?.operating_times?.length > 0 ? data?.operating_times : dayOfWeekData || [];
	const { timeFormat, dateFormat } = useConvertDate();
	const currentLocale = i18n.language || 'en';

	const formatTimeForDisplay = (time: string | null) => {
		if (!time) return '';
		return dayjs(time, STORAGE_TIME_FORMAT).locale(currentLocale).format(timeFormat);
	};
	return (
		<CustomModal
			title={t('Operating Time')}
			show={show}
			onHide={onHide}
		>
			<Box
				className="mb-2 d-flex flex-column gap-4"
				sx={{
					width: '42rem', height: '37rem',
					overflow: 'auto',
				}}
			>
				<Box sx={{
					background: theme === 'dark' ? Colors.Gray7 : Colors.Gray1,
					borderRadius: '10px',
					padding: '6px 16px 6px 16px',
				}}>
					{operatingTimes?.map((item: any, index: number) => (
						<Box className="d-flex flex-column">
							<Box key={index} className="d-flex justify-content-between py-2">
								<span>{t(item.day_of_week)}</span>
								<span>  {(item.start_time || item.end_time) ?
									formatTimeForDisplay(item.start_time) + " - " + formatTimeForDisplay(item.end_time) :
									t('Off')}

								</span>
							</Box>
							{index !== operatingTimes.length - 1 && <hr style={{ borderColor: Colors.Gray5 }} className="my-1" />}
						</Box>
					))}
				</Box>
				{data?.exceptions?.length > 0 && (
					<Box>
						<Box sx={{ borderRadius: '10px', fontSize: '1.25rem', fontWeight: '500', mb: '1rem' }}>{t("Operating Time.Exception")}</Box>
						<Box className="d-flex flex-column gap-2">
							{data?.exceptions?.map((item: any, index: number) => (
								<Box className="d-flex flex-column ">
									<Box key={index} className="d-flex  ">
										<>
											<span style={{ fontWeight: '600' }}>{dayjs(item.exception_date, "YYYY-MM-DD").locale(currentLocale).format(dateFormat)} &nbsp;</span>
											{item.is_all_day ? "(" + t('All day') + ")" : " (" + formatTimeForDisplay(item.start_time) + " - " + formatTimeForDisplay(item.end_time) + ")"}  {item.reason ? ": " + item.reason : " "}
										</>
									</Box>
								</Box>
							))}
						</Box>
					</Box>
				)}
			</Box>
			<CenterBtn
				type="button"
				variant="outline"
				color="secondary"
				size="lg"
				label={t('Close')}
				onClick={onHide}
				style={{
					marginBottom: '1.25rem',
				}}
			/>

		</CustomModal>
	);
};

export default OperatingTimeModal;