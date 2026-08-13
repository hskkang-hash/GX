import { useCallback, useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { Box } from '@mui/material';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsExclamationCircle } from 'react-icons/bs';
import { useNavigate } from 'react-router-dom';
import GearIcon from '@/assets/images/GearIcon';
import CustomCheckBox from '@/components/Form/CustomCheckBox';
import { CustomRoutes } from '@/services/API';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import { checkStatusAllDrone } from '@/features/surveillanceProfile/utils/checkStatus';
import CheckCompleteModal from './CheckCompleteModal';
import DroneSensorStatus, { DroneSensorStatusType } from './DroneSensorStatus';
import Colors from '@/configs/Colors';
import { convertDataForChecklist } from '@/features/surveillanceProfile/utils/convertDataForChecklist';
import useChecklistSetting from '@/features/checklistSetting/hooks/useChecklistSetting';
import CancelProfileModal from './CancelProfileModal';
import { CustomBtn, FormBlock, ROLE_PERMISSION, ToastTopHelper, useConfigSystem, useLoadingContext, useTheme, useUserInfo } from 'rj-core';
import ListDroneToChangeModal from './ListDroneToChangeModal';
import dayjs from 'dayjs';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

interface ChecklistSetting {
	name_category: string;
	item: {
		id: string;
		item_name: string;
	}[];
}

interface ChecklistFormValues {
	checklistValues: {
		selectedIds: string[];
		byId: Record<string, boolean>;
	};
	action?: string;
}

interface DroneChecklistState {
	deviceId: number;
	profileDroneId: number;
	droneUnitIdWorking: string;
	checklistSetting: ChecklistSetting[];
	droneSensorStatus: DroneSensorStatusType[];
	selectedChecklistIds: string[];
	isComplete: boolean;
	auto_checklist_drone_status?: string;
	sensorStatus?: {
		flightMode?: string;
		armed?: boolean;
	};
}

export interface DroneList {
	id: number;
	unit_id: number;
	start_waypoint_id: number;
	end_waypoint_id: number;
	name: string;
	profile_drone_id: number;
}

export const CheckList = ({
	setRefetchChecklist = () => { },
	checklistDisabled = false,
	selectedRowForDetail = null,
	handleRefreshDroneList = (profileId?: number) => { },
	setOpenModalStopRepeat = () => { },
	setRefreshTable = () => { },
	isStopRepeatProfile = false,
	cancelDataProfile = (id: number) => { },
	handleRefreshWhenWaiting = () => { },
}: {
	setRefetchChecklist: (refetch: boolean) => void;
	checklistDisabled?: boolean;
	selectedRowForDetail: any | null;
	setRefreshTable: (refresh: boolean) => void;
	handleRefreshDroneList: (profileId?: number) => void | Promise<void>;
	setOpenModalStopRepeat: (open: { id: number | undefined, show: boolean }) => void;
	isStopRepeatProfile: boolean;
	cancelDataProfile: (id: number) => void;
	handleRefreshWhenWaiting: (profileId?: number) => void;
}): ReactElement => {




	//LIST DRONE IN PROFILE
	const droneList: DroneList[] = useMemo(() => {
		if (!selectedRowForDetail?.devices || !selectedRowForDetail?.drone_assignments) return [];
		return selectedRowForDetail.devices.map((device: { id: number, unit_id: number, library: string }, index: number) => {
			const assignment = selectedRowForDetail.drone_assignments?.find(
				(assignment: { device__id?: number }) => assignment.device__id === device.id
			);
			return {
				id: device?.id ?? 0,
				unit_id: device?.unit_id,
				name: device?.name,
				profile_drone_id: assignment?.id ?? 0,
				start_waypoint_id: assignment?.start_waypoint_id ?? 0,
				end_waypoint_id: assignment?.end_waypoint_id ?? 0,
			}
		});
	}, [selectedRowForDetail]);

	const [droneListdata, setDroneListdata] = useState<DroneList[]>(droneList);
	useEffect(() => {
		setDroneListdata(droneList);
	}, [droneList]);

	const [droneChecklistStates, setDroneChecklistStates] = useState<Record<string, DroneChecklistState>>({});
	const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");


	// Track which profile has been loaded to prevent refetching
	// Track previous selectedDeviceId to sync form only on change
	// Track loading state to prevent duplicate API calls
	const loadedProfileIdRef = useRef<number | null>(null);
	const prevSelectedDeviceIdRef = useRef<string>("");
	const loadingDroneRef = useRef<string | null>(null);

	// GET CURRENT SELECTED DRONE'S STATE
	const currentDroneState = useMemo(() => {
		if (!selectedDeviceId) return null;
		return droneChecklistStates[selectedDeviceId] || null;
	}, [selectedDeviceId, droneChecklistStates]);

	const droneSensorStatus = currentDroneState?.droneSensorStatus || [];
	const autoChecklistDroneStatus = currentDroneState?.auto_checklist_drone_status;
	const checklistSetting = currentDroneState?.checklistSetting || [];

	const [sensorStatus, setSensorStatus] = useState<any>(currentDroneState?.sensorStatus || {});
	const [loadingSensorStatus, setLoadingSensorStatus] = useState<boolean>(false);


	useEffect(() => {
		if (currentDroneState?.sensorStatus) {
			setSensorStatus(currentDroneState?.sensorStatus);
		}
	}, [currentDroneState?.sensorStatus]);

	const { t } = useTranslation();
	const [theme] = useTheme();
	const methods = useForm<ChecklistFormValues>({
		defaultValues: {
			checklistValues: {
				selectedIds: [],
				byId: {},
			},
			action: '',
		},
	});
	const navigate = useNavigate();
	const [reasonNote, setReasonNote] = useState<string>('');
	const [showCheckCompleteModal, setShowCheckCompleteModal] = useState(false);
	const [showCancelProfileModal, setShowCancelProfileModal] = useState(false);
	const { timeZoneFormat } = useConvertDate();
	console.log("selectedRowForDetail__start_time", selectedRowForDetail?.start_time);
	console.log("curentdatetime", dayjs().tz(timeZoneFormat));
	console.log("curentdatetime_start_time", dayjs(selectedRowForDetail?.start_time).tz(timeZoneFormat));
	const isLate = dayjs(selectedRowForDetail?.start_time).tz(timeZoneFormat).isBefore(dayjs().tz(timeZoneFormat));
	console.log("curentdatetime_isLate", isLate);

	const orderFixPosition = [
		'Pre-flight Check',
		'Controller Check',
		'Weather Check',
	];
	const positionOrder = new Map(
		orderFixPosition.map((name, index) => [name, index] as const),
	);
	const [showListDroneToChangeModal, setShowListDroneToChangeModal] =
		useState(false);

	const sortedChecklistSetting = useMemo(() => {
		return (checklistSetting ?? [])
			.map((item, originalIndex) => ({ item, originalIndex }))
			.sort((a, b) => {
				const rankA = positionOrder.get(a.item.name_category);
				const rankB = positionOrder.get(b.item.name_category);
				const valueA =
					typeof rankA === 'number' ? rankA : Number.MAX_SAFE_INTEGER;
				const valueB =
					typeof rankB === 'number' ? rankB : Number.MAX_SAFE_INTEGER;
				if (valueA !== valueB) return valueA - valueB;
				return a.originalIndex - b.originalIndex;
			})
			.map(({ item }) => item);
	}, [checklistSetting, positionOrder]);

	const {
		control,
		handleSubmit,
		reset,
		formState: { isSubmitting },
	} = methods;

	const {
		cancelProfile,
		actionCheckComplete,
	} = useSurveillanceProfile();


	const resetChecklist = () => {
		setDroneChecklistStates({});
		setDroneListdata([]);
		setSelectedDeviceId("");
		setSensorStatus({});
		setReasonNote('');
		loadingDroneRef.current = null;
		loadedProfileIdRef.current = null;
		prevSelectedDeviceIdRef.current = "";
		reset({
			checklistValues: {
				selectedIds: [],
				byId: {},
			},
			action: '',
		});
	}

	const onValidSubmit = async (data: ChecklistFormValues): Promise<void> => {
		const action = data.action;
		if (!action) {
			return;
		}
		switch (action) {
			case 'cancelProfile': {
				if (!selectedDeviceId) return;
				// eslint-disable-next-line no-console
				const response = await cancelProfile({
					profile_id: selectedRowForDetail?.id,
					reason: reasonNote,
				});
				if (response?.success) {
					ToastTopHelper.success(response?.message);
					handleRefreshDroneList(selectedRowForDetail?.id as number);
					cancelDataProfile(selectedRowForDetail?.id);
					resetChecklist();
				} else {
					ToastTopHelper.error(response?.message);
				}
				break;
			}
			case 'checkCompleteNow': {
				if (!selectedRowForDetail?.id) return;
				const droneChecks = droneListdata
					.map(drone => {
						const state = droneChecklistStates[String(drone.unit_id)];
						if (!state) return null;

						return {
							profile_drone_id: state.profileDroneId,
							drone_id: state.deviceId,
							check_lists: state.selectedChecklistIds.map((id) => Number(id)),
							auto_checklist: state.droneSensorStatus,
						};
					})
					.filter((item): item is {
						profile_drone_id: number;
						drone_id: number;
						check_lists: number[];
						auto_checklist: DroneSensorStatusType[];
					} => item !== null);

				// // eslint-disable-next-line no-console
				const response = await actionCheckComplete({
					profile_id: selectedRowForDetail.id,
					drone_checks: droneChecks,
					not_yet: false,
				});
				if (response?.success) {
					ToastTopHelper.success(response?.message);
					handleRefreshDroneList(selectedRowForDetail.id);
					cancelDataProfile(selectedRowForDetail.id);
					resetChecklist();
				} else {
					ToastTopHelper.error(response?.message);
				}
				break;
			}
			case 'checkCompleteWait': {
				if (!selectedRowForDetail?.id) return;
				const droneChecks = droneListdata
					.map(drone => {
						const state = droneChecklistStates[String(drone.unit_id)];
						if (!state) return null;

						return {
							profile_drone_id: state.profileDroneId,
							drone_id: state.deviceId,
							check_lists: state.selectedChecklistIds.map((id) => Number(id)),
							auto_checklist: state.droneSensorStatus,
						};
					})
					.filter((item): item is {
						profile_drone_id: number;
						drone_id: number;
						check_lists: number[];
						auto_checklist: DroneSensorStatusType[];
					} => item !== null);

				// // eslint-disable-next-line no-console
				const response = await actionCheckComplete({
					profile_id: selectedRowForDetail.id,
					drone_checks: droneChecks,
					not_yet: true,
				});
				if (response?.success) {
					ToastTopHelper.success(response?.message);
					handleRefreshWhenWaiting(selectedRowForDetail.id);
					resetChecklist();
				} else {
					ToastTopHelper.error(response?.message);
				}
				break;
			}
			default:
				// eslint-disable-next-line no-console
				console.log('Submit: unknown action', action, data);
		}
	};

	const renderChecklistWithCategory = (
		checklist: ChecklistSetting,
	): ReactElement => {
		return (
			<FormBlock
				style={{
					backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
					height: '22rem',
					overflow: 'auto',
					width: '100%',
				}}
			>
				<div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
					{t(checklist.name_category)}
				</div>
				<div className="content-title d-flex flex-column">
					{checklist.item.map((item) => {
						const selectedIds =
							methods.watch('checklistValues.selectedIds') ?? [];
						const isChecked = selectedIds.includes(String(item.id));

						return (
							<CustomCheckBox
								name={`checklistValues.byId.${item.id}`}
								subLabel={item.item_name}
								control={control}
								onChangeValue={(checked): void => {
									const current =
										methods.getValues('checklistValues.selectedIds') ?? [];
									const itemIdStr = String(item.id);
									const exists = current.includes(itemIdStr);
									const next = checked
										? exists
											? current
											: [...current, itemIdStr]
										: exists
											? current.filter((id) => id !== itemIdStr)
											: current;
									methods.setValue('checklistValues.selectedIds', next, {
										shouldDirty: true,
									});


									// UPDATE DRONE CHECKLIST STATE WITH COMPLETION STATUS
									if (selectedDeviceId && droneChecklistStates[selectedDeviceId]) {
										const currentState = droneChecklistStates[selectedDeviceId];
										const allSensorsNormal = currentState.droneSensorStatus.length > 0 &&
											currentState.droneSensorStatus.every((item: DroneSensorStatusType) => item.situation === 'Normal');
										const hasCheckedItems = next.length > 0;
										const isComplete = allSensorsNormal && hasCheckedItems;

										setDroneChecklistStates(prev => ({
											...prev,
											[selectedDeviceId]: {
												...prev[selectedDeviceId],
												selectedChecklistIds: next,
												isComplete,
											}
										}));
									}
								}}
								disabled={!selectedDeviceId || checklistDisabled}
								key={`${item.id}-${checklist.name_category}-${item.item_name}`}
							/>
						);
					})}
				</div>
			</FormBlock>
		);
	};

	const isAllDroneSensorStatusNormal = useMemo(() => {
		return (
			droneSensorStatus &&
			droneSensorStatus.length > 0 &&
			checkStatusAllDrone('Normal', droneSensorStatus)
		);
	}, [droneSensorStatus]);

	// CHECK IF ALL DRONES ARE COMPLETE
	const areAllDronesComplete = useMemo(() => {
		if (droneListdata.length === 0) return false;
		return droneListdata.every(drone => {
			const state = droneChecklistStates[String(drone.unit_id)];
			return state?.isComplete === true;
		});
	}, [droneListdata, droneChecklistStates]);

	const { getChecklistSetting } = useChecklistSetting();
	const { showLoading, hideLoading } = useLoadingContext();

	// LOAD CHECKLIST FOR A SPECIFIC DRONE
	const handleGetChecklistSetting = useCallback(
		async (deviceId: number, droneUnitIdWorking: string, profileDroneId: number) => {
			const { data: dataChecklistSetting, auto_checklist, auto_checklist_drone_status, sensorStatus: sensorStatusData } =
				await getChecklistSetting({
					currentPage: 1,
					pageSize: 10000,
					objSearch: {
						searchParams: [
							{
								id: 'device_id',
								value: droneUnitIdWorking,
							},
							{
								id: 'active',
								value: true,
							},
						],
					},
				});

			const convertedChecklist = convertDataForChecklist(dataChecklistSetting);
			const sensorStatus = auto_checklist || [];

			// ALL SENSORS NORMAL AND AT LEAST 1 CHECKLIST CHECKED -> COMPLETE
			const allSensorsNormal = sensorStatus.length > 0 &&
				sensorStatus.every((item: DroneSensorStatusType) => item.situation === 'Normal');
			const hasCheckedItems = false;
			const isComplete = allSensorsNormal && hasCheckedItems;

			setDroneChecklistStates(prev => ({
				...prev,
				[droneUnitIdWorking]: {
					deviceId,
					profileDroneId,
					droneUnitIdWorking,
					checklistSetting: convertedChecklist,
					droneSensorStatus: sensorStatus,
					sensorStatus: sensorStatusData,
					selectedChecklistIds: [],
					isComplete: isComplete || false,
					auto_checklist_drone_status: auto_checklist_drone_status,
				}
			}));
		},
		[getChecklistSetting, convertDataForChecklist],
	);

	//ONLY REFRESH SENSOR STATUS
	const handleRefreshSensorStatus = useCallback(async () => {
		if (!selectedDeviceId) return;
		setLoadingSensorStatus(true);
		showLoading();
		try {
			const { sensorStatus: SensorStatusData } = await getChecklistSetting({
				currentPage: 1,
				pageSize: 10000,
				objSearch: {
					searchParams: [
						{
							id: 'device_id',
							value: selectedDeviceId,
						},
						{
							id: 'active',
							value: true,
						},
					],
				},
			});
			setSensorStatus(SensorStatusData || {});
			setLoadingSensorStatus(false);
		} catch (error) {
			console.error('Error refreshing sensor status:', error);
		} finally {
			hideLoading();
			setLoadingSensorStatus(false);
		}
	}, [getChecklistSetting, selectedDeviceId]);


	// RESET STATE WHEN PROFILE CHANGES AND SELECT FIRST DRONE
	useEffect(() => {
		const profileId = selectedRowForDetail?.id;
		// ONLY RESET IF PROFILE CHANGED AND HAS DRONES
		if (profileId && droneList.length > 0 && loadedProfileIdRef.current !== profileId) {
			setDroneChecklistStates({});
			setSelectedDeviceId("");
			setSensorStatus({});
			loadingDroneRef.current = null;
			loadedProfileIdRef.current = profileId;
			prevSelectedDeviceIdRef.current = "";
			if (droneList.length > 0) {
				setSelectedDeviceId(String(droneList[0]?.unit_id || ""));
			}
		}
	}, [selectedRowForDetail?.id, droneList.length, selectedRowForDetail, reset]);

	// LOAD CHECKLIST SETTING WHEN DRONE IS SELECTED (IF NOT ALREADY LOADED)
	useEffect(() => {
		if (!selectedDeviceId) return;

		const droneState = droneChecklistStates[selectedDeviceId];
		const selectedDrone = droneListdata.find(drone => String(drone.unit_id) === selectedDeviceId);

		// ONLY CALL API IF DRONE IS SELECTED AND DOESN'T HAVE STATE YET AND NOT ALREADY LOADING
		if (!droneState && selectedDrone && loadingDroneRef.current !== selectedDeviceId) {
			loadingDroneRef.current = selectedDeviceId;
			showLoading();
			setSensorStatus({});
			handleGetChecklistSetting(
				selectedDrone.id,
				selectedDeviceId,
				selectedDrone.profile_drone_id
			).finally(() => {
				hideLoading();
				loadingDroneRef.current = null;
			});
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [selectedDeviceId, droneChecklistStates]);

	// SYNC FORM VALUES WITH DRONE STATE WHEN SWITCHING DRONES
	useEffect(() => {
		if (!selectedDeviceId || prevSelectedDeviceIdRef.current === selectedDeviceId) {
			if (selectedDeviceId) {
				prevSelectedDeviceIdRef.current = selectedDeviceId;
			}
			return;
		}

		prevSelectedDeviceIdRef.current = selectedDeviceId;
		// SYNC CHECKBOX FROM DRONE'S STATE WHEN SWITCHING DRONES
		// EACH DRONE HAS ITS OWN INDEPENDENT CHECKBOX LIST
		setDroneChecklistStates(prev => {
			const state = prev[selectedDeviceId];
			if (state && state.selectedChecklistIds.length > 0) {
				// IF DRONE HAS CHECKED ITEMS, SYNC THEM TO FORM
				const byId: Record<string, boolean> = {};
				state.selectedChecklistIds.forEach((id) => {
					byId[id] = true;
				});
				reset({
					checklistValues: {
						selectedIds: state.selectedChecklistIds,
						byId: byId,
					},
					action: '',
				});
			} else {
				reset({
					checklistValues: {
						selectedIds: [],
						byId: {},
					},
					action: '',
				});
			}
			return prev;
		});
	}, [selectedDeviceId, reset]);

	const selectedDevice: DroneList | undefined = useMemo(() => {
		return droneListdata.find(drone => String(drone.unit_id) === selectedDeviceId);
	}, [droneListdata, selectedDeviceId]);

	return (
		<>
			<FormProvider {...methods}>
				<form onSubmit={handleSubmit(onValidSubmit)}>
					<Box
						height={410}
						overflow={'auto'}
						display="flex"
						flexDirection="column"
						gap={2}
					>
						<Box className="d-flex gap-2 flex-row">
							{droneListdata?.map((device) => {
								const deviceUnitIdStr = String(device.unit_id);
								const droneState = droneChecklistStates[deviceUnitIdStr];

								const isComplete = droneState?.isComplete === true;
								const isSelected = deviceUnitIdStr === selectedDeviceId;

								return <Box
									onClick={() => {
										setSelectedDeviceId(deviceUnitIdStr);
										// SYNC CHECKBOX FROM THIS DRONE'S STATE WHEN CLICKING
										const state = droneChecklistStates[deviceUnitIdStr];
										if (state && state.selectedChecklistIds.length > 0) {
											const byId: Record<string, boolean> = {};
											state.selectedChecklistIds.forEach((id) => {
												byId[id] = true;
											});
											reset({
												checklistValues: {
													selectedIds: state.selectedChecklistIds,
													byId: byId,
												},
												action: '',
											});
										} else {
											reset({
												checklistValues: {
													selectedIds: [],
													byId: {},
												},
												action: '',
											});
										}
									}}
									sx={{
										backgroundColor: isComplete
											? theme === 'dark' ? '#3F5848' : '#D6F8E2'
											: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
										color: isComplete ? '#0CBA47' : 'inherit',
										padding: '0.5rem 0.75rem',
										borderRadius: '0.5rem',
										border: `1px solid ${isSelected ? Colors.Primary : 'transparent'}`,
										cursor: 'pointer',
									}}

									key={device.unit_id}>{device.name}</Box>
							})}
						</Box>
						<Box className="d-flex gap-2 flex-row"
							style={{ fontSize: '1rem', fontWeight: 400, color: Colors.Gray5 }}>
							{t('Complete the checklist for all drones in this profile before starting the flight.')}
						</Box>

						{/* DRONE SENSOR STATUS */}
						<DroneSensorStatus
							droneSensorStatus={droneSensorStatus}
							sensorStatus={sensorStatus}
							onRefreshSensorStatus={handleRefreshSensorStatus}
							loadingSensorStatus={loadingSensorStatus}
						/>
						{currentDroneState && (
							<>
								{(isAllDroneSensorStatusNormal &&
									droneSensorStatus &&
									droneSensorStatus.length > 0 &&
									autoChecklistDroneStatus === "available") ? (
									<>
										<div className="d-flex justify-content-between align-items-center mt-4">
											<div>
												<h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>
													{t('Check List')}
												</h1>
											</div>
											<div
												style={{
													cursor: 'pointer',
													border: '1px solid #E0E0E0',
													borderRadius: '8px',
													padding: '0.25rem',
												}}
												onClick={() => {
													navigate(CustomRoutes.checklistSetting.path);
												}}
											>
												<GearIcon
													color={theme === 'dark' ? '#FFFFFF' : '#2D2E30'}
												/>
											</div>
										</div>
										<div className="d-flex gap-4 flex-row mt-3">
											{sortedChecklistSetting &&
												sortedChecklistSetting.map((checklist) => {
													return renderChecklistWithCategory(checklist);
												})}
										</div>
									</>
								) : (
									<div
										className="d-flex justify-content-center align-items-center"
										style={{
											flex: 1,
											minHeight: 0,
											color: '#EB7509',
											fontSize: '1rem',
											fontWeight: 600,
										}}
									>
										<BsExclamationCircle
											className="me-2"
											size={16}
										/>
										<p className="text-center mb-0">
											{(autoChecklistDroneStatus !== "available" || droneSensorStatus.length === 0) ?
												t('The selected drone is currently performing another mission, so please choose a different drone.')
												: t('This drone has a malfunctioning sensor and cannot fly. Please select another drone or cancel the operation')}
										</p>
									</div>
								)}
							</>
						)}
					</Box>
					{selectedDeviceId && (
						<div className="d-flex justify-content-center gap-3 mt-3">
							<CustomBtn
								actionType={ROLE_PERMISSION.UPDATE}
								label={t('Cancel Profile')}
								color="secondary"
								variant="outline"
								type="button"
								onClick={() => {
									setShowCancelProfileModal(true);
								}}
								loading={isSubmitting}
								disabled={!selectedDeviceId}
							/>
							<CustomBtn
								actionType={ROLE_PERMISSION.UPDATE}
								label={t('Change Drone')}
								variant="outline"
								color="primary"
								type="button"
								onClick={() => {
									setShowListDroneToChangeModal(true);
								}}
								disabled={
									!selectedDeviceId ||
									checklistDisabled ||
									selectedRowForDetail?.is_upload_mission
								}
							/>
							{!isStopRepeatProfile && <CustomBtn
								actionType={ROLE_PERMISSION.UPDATE}
								label={t('Stop Repeat')}
								variant="outline"
								color="primary"
								type="button"
								onClick={() => {
									setOpenModalStopRepeat({ id: selectedRowForDetail?.id, show: true });
								}}
								disabled={
									!selectedDeviceId ||
									checklistDisabled ||
									selectedRowForDetail?.is_upload_mission
								}
							/>}
							<CustomBtn
								actionType={ROLE_PERMISSION.UPDATE}
								label={t('Check Complete')}
								type="button"
								onClick={() => {
									setShowCheckCompleteModal(true);
								}}
								loading={isSubmitting}
								disabled={
									!selectedDeviceId ||
									checklistDisabled ||
									!areAllDronesComplete
								}
							/>
						</div>
					)}
				</form>
			</FormProvider>

			{/* LIST DRONE TO CHANGE MODAL */}
			<ListDroneToChangeModal
				profile_id={selectedRowForDetail?.id}
				selectedDevice={selectedDevice ?? null}
				show={showListDroneToChangeModal}
				onChangeDroneSuccess={async (data) => {
					setRefetchChecklist(true);
					const updatedDeviceUnitId = data.device_unit_id;
					const toDeviceId = data.to_device_id;
					const assignmentId = data.assignment_id;
					const deviceName = data.device_name;

					// FIND THE DEVICE TO BE REPLACED
					const changedDeviceIndex = droneListdata.findIndex(drone => drone.id === data.from_device_id);
					const changedDevice = changedDeviceIndex !== -1 ? droneListdata[changedDeviceIndex] : null;

					if (changedDevice) {
						const oldUnitId = String(changedDevice.unit_id);
						const wasSelected = oldUnitId === selectedDeviceId;

						// UPDATE DRONE LIST DATA WITH NEW DEVICE INFO
						setDroneListdata(prev => {
							const updated = [...prev];
							updated[changedDeviceIndex] = {
								id: toDeviceId,
								unit_id: updatedDeviceUnitId,
								name: deviceName,
								profile_drone_id: assignmentId,
								start_waypoint_id: changedDevice.start_waypoint_id,
								end_waypoint_id: changedDevice.end_waypoint_id,
							};
							return updated;
						});

						// REMOVE OLD STATE IF UNIT ID CHANGED
						setDroneChecklistStates(prev => {
							const updated = { ...prev };
							if (oldUnitId !== updatedDeviceUnitId && updated[oldUnitId]) {
								delete updated[oldUnitId];
							}
							return updated;
						});

						// CALL API CHECKLIST WITH NEW UNIT ID USING handleGetChecklistSetting
						showLoading();
						await handleGetChecklistSetting(
							toDeviceId,
							String(updatedDeviceUnitId),
							assignmentId
						).finally(() => {
							hideLoading();
						});

						// UPDATE SELECTED DEVICE ID AFTER STATE IS UPDATED
						if (wasSelected) {
							setTimeout(() => {
								setSelectedDeviceId(String(updatedDeviceUnitId));
								reset({
									checklistValues: {
										selectedIds: [],
										byId: {},
									},
									action: '',
								});
							}, 0);
						}
					}
				}}
				onClose={() => setShowListDroneToChangeModal(false)}
			/>

			<CheckCompleteModal
				show={showCheckCompleteModal}
				onClose={() => setShowCheckCompleteModal(false)}
				isLate={isLate}
				onStartNow={() => {
					methods.setValue('action', 'checkCompleteNow');
					setShowCheckCompleteModal(false);
					handleSubmit(onValidSubmit)();
				}}
				onWait={() => {
					methods.setValue('action', 'checkCompleteWait');
					setShowCheckCompleteModal(false);
					handleSubmit(onValidSubmit)();
				}}
			/>
			<CancelProfileModal
				show={showCancelProfileModal}
				onClose={() => {
					setShowCancelProfileModal(false);
					setReasonNote('');
				}}
				onCancelProfile={(reason: string) => {
					setReasonNote(reason);
					methods.setValue('action', 'cancelProfile');
					setShowCancelProfileModal(false);
					handleSubmit(onValidSubmit)();
				}}
				reasonNote={reasonNote}
				onReasonChange={setReasonNote}
			/>
		</>
	);
};
