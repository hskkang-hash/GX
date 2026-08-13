import React, { useCallback, useMemo } from 'react';
import { Box, IconButton } from '@mui/material';
import { IoTrashOutline } from 'react-icons/io5';
import dayjs from 'dayjs';
import { CustomBtn, CustomizableTable, FormBlock, useConfigSystem, useTheme, useUserInfo } from 'rj-core';
import CustomDatePicker from './Form/CustomDatePicker';
import CustomTimeRangePicker from './Form/CustomTimeRangePicker';
import CustomCheckBox from './Form/CustomCheckBox';
import { CustomInputHookForm } from 'rj-core';
import { EndTimeCellOperating, ExceptionData, OperatingTimeData, OperatingTimeSwitchCell, StartTimeCellOperating } from './HelperCellOperatingTime';
import { useTranslation } from 'react-i18next';
import { useFieldArray, useFormContext } from 'react-hook-form';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';

interface OperatingTimeSectionProps {
	setOperatingTimes: (times: OperatingTimeData[]) => void;
	operatingTimes: OperatingTimeData[];
	operatingTimeErrors: any;
	setOperatingTimeErrors: (errors: any) => void;
}

// Standard format for storing/sending to backend (24h)
const STORAGE_TIME_FORMAT = 'HH:mm:ss';

const OperatingTimeSection: React.FC<OperatingTimeSectionProps> = ({
	setOperatingTimes,
	operatingTimes,
	operatingTimeErrors,
	setOperatingTimeErrors,
}) => {
	const { clearErrors, control, watch, formState: { errors }, setValue } = useFormContext();
	const { t } = useTranslation();

	const [theme] = useTheme();
	const { timeFormat, dateFormat } = useConvertDate();

	const updateOperatingTimeByIndex = useCallback(
		(index: number, field: keyof OperatingTimeData, value: unknown): void => {
			setOperatingTimes((previousAssignments) => {
				if (index < 0 || index >= previousAssignments.length) {
					return previousAssignments;
				}
				const updatedAssignments = [...previousAssignments];
				const currentAssignment = updatedAssignments[index];

				if (field === 'is_active') {
					updatedAssignments[index] = {
						...currentAssignment,
						[field]: value,
					};
					// If deactivating, clear times; if activating, set defaults
					if (value === false) {
						updatedAssignments[index].start_time = null;
						updatedAssignments[index].end_time = null;
					} else {
						// Store in standard 24h format for backend
						updatedAssignments[index].start_time = '08:00:00';
						updatedAssignments[index].end_time = '20:00:00';
					}
				} else if (
					field === 'start_time' ||
					field === 'end_time'
				) {
					const timeValue = value as string | null;
					updatedAssignments[index] = {
						...currentAssignment,
						[field]: timeValue,
					} as OperatingTimeData;

					// Validate end time > start time (parse from storage format)
					const startTime = updatedAssignments[index].start_time;
					const endTime = updatedAssignments[index].end_time;
					const isActive = updatedAssignments[index].is_active;

					if (isActive && startTime && endTime) {
						const start = dayjs(startTime, STORAGE_TIME_FORMAT);
						const end = dayjs(endTime, STORAGE_TIME_FORMAT);
						const errorKey = `operating_time_${index}`;
						if (end.isBefore(start) || end.isSame(start)) {
							setOperatingTimeErrors((prev) => ({ ...prev, [errorKey]: true }));
						} else {
							setOperatingTimeErrors((prev) => {
								const newErrors = { ...prev };
								delete newErrors[errorKey];
								return newErrors;
							});
						}
					}
				}
				return updatedAssignments;
			});
		},
		[],
	);

	const historyBehaviorColumns = useMemo(() => {
		const columns = [];
		columns.push({
			Header: 'Day of Week',
			accessor: 'day_of_week_id',
			enableSorting: false,
			enableColumnFilter: false,
			cell: (row: any) => {
				return <span>{t(row?.row?.original?.name || '')}</span>;
			},
		});
		columns.push({
			Header: t('Active?'),
			accessor: 'is_active',
			enableSorting: false,
			enableColumnFilter: false,
			customStyle: { width: '80px' },
			cell: (row: any) => (
				<OperatingTimeSwitchCell
					row={row}
					updateOperatingTimeByIndex={updateOperatingTimeByIndex}
				/>
			),
		});
		columns.push({
			Header: t('Start Time'),
			accessor: 'start_time',
			enableSorting: false,
			enableColumnFilter: false,
			customStyle: {
				width: '130px',
			},
			cell: (row: any) => {
				const errorKey = `operating_time_${row?.row?.index}`;
				return (
					<StartTimeCellOperating
						row={row}
						updateOperatingTimeByIndex={updateOperatingTimeByIndex}
						flagError={operatingTimeErrors[errorKey]}
					/>
				);
			},
		});
		columns.push({
			Header: t('End Time'),
			accessor: 'end_time',
			enableSorting: false,
			enableColumnFilter: false,
			customStyle: {
				width: '130px',
			},
			cell: (row: any) => {
				const errorKey = `operating_time_${row?.row?.index}`;
				return (
					<EndTimeCellOperating
						row={row}
						updateOperatingTimeByIndex={updateOperatingTimeByIndex}
						flagError={operatingTimeErrors[errorKey]}
					/>
				);
			},
		});
		return columns;
	}, [
		t,
		updateOperatingTimeByIndex,
		operatingTimeErrors,
	]);

	const { fields, append, remove, update } = useFieldArray({
		control,
		name: 'exceptions',
	});

	const handleAddException = useCallback(() => {
		const newException: ExceptionData = {
			exception_date: null,
			start_time: null,
			end_time: null,
			is_all_day: false,
			reason: null,
		};
		append(newException);
	}, [append]);

	const handleRemoveException = useCallback(
		(index: number) => {
			remove(index);
		},
		[remove],
	);

	return (
		<FormBlock>
			{/* TITLE */}
			<span style={{ fontSize: "1.25rem", fontWeight: 500 }}>
				{t("Operating Time")}
			</span>

			{/* TABLE */}
			<CustomizableTable
				columns={historyBehaviorColumns}
				data={{
					data: operatingTimes || [],
					totalItem: operatingTimes?.length || 0,
					totalPage: 1,
				}}
				hasPagination={false}
				notUseGroupColumn
				useSystemSetting
				subTable
				notShowSelectRow
			/>

			{/* ADD EXCEPTION BUTTON */}
			<Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '1.5rem 0' }}>
				<CustomBtn
					label={`+ ${t('Add Exception')}`}
					variant="outline"
					color="primary"
					type="button"
					onClick={handleAddException}
					style={{ border: 'none', color: '#1d9be2' }}
				/>
			</Box>

			{/* EXCEPTIONS LIST */}
			{fields.length > 0 && (
				<div>
					{fields.map((field, index) => {
						const isAllDay = watch(`exceptions.${index}.is_all_day`);

						return (
							<div
								key={field.id}
								className="d-flex justify-content-between align-items-start mb-3"
								style={{ gap: '1rem' }}
							>
								{/* Date */}
								<div style={{ flex: 1 }}>
									<CustomDatePicker
										name={`exceptions.${index}.exception_date`}
										control={control}
										format={dateFormat}
										disablePastTime={true}
										placeholder=" "
									/>
								</div>

								{/* Time Range */}
								<div style={{ flex: 1 }}>
									<CustomTimeRangePicker
										control={control}
										nameStart={`exceptions.${index}.start_time`}
										nameEnd={`exceptions.${index}.end_time`}
										disabled={isAllDay}
										format={timeFormat}
										placeholder=" "
										errorMessage={
											errors?.exceptions?.[index]?.end_time?.message
												? t("Schedule time is required")
												: undefined
										}
									/>
								</div>
								{/* All day checkbox */}
								<div>
									<CustomCheckBox
										name={`exceptions.${index}.is_all_day`}
										control={control}
										minWidthStyle="7rem"
										subLabel={t('All day')}
										position="end"
										onChangeValue={(value) => {
											setValue(`exceptions.${index}.is_all_day`, value);
											if (value) {
												setValue(`exceptions.${index}.start_time`, null);
												setValue(`exceptions.${index}.end_time`, null);
											}
											clearErrors(`exceptions.${index}.start_time`);
											clearErrors(`exceptions.${index}.end_time`);
										}}
									/>
								</div>

								{/* Reason */}
								<div style={{ flex: 1 }}>
									<CustomInputHookForm
										name={`exceptions.${index}.reason`}
										control={control}
									/>
								</div>
								{/* Delete */}
								<div>
									<IconButton onClick={() => handleRemoveException(index)}>
										<IoTrashOutline
											size={16}
											color={
												theme === "dark"
													? "var(--ga-dark-theme-font-color)"
													: "var(--ga-light-theme-font-color)"
											}
										/>
									</IconButton>
								</div>
							</div>
						);
					})}
				</div>
			)}
		</FormBlock>
	);
};

export default OperatingTimeSection;
