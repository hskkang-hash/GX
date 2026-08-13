import { Box, Radio } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CustomBtn, CustomizableTable, CustomModal, ToastTopHelper, useTheme } from 'rj-core';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import { DroneList } from './CheckList';

interface SearchParam {
	id: string;
	value: string | number | boolean;
}

interface SortParam {
	id: string;
	desc: boolean;
}

interface SearchObject {
	searchParams?: SearchParam[];
	filters?: Record<string, unknown>;
	sortParams?: SortParam[];
}


interface DroneChange {
	battery: string,
	device_id: number
	model: string,
	serial_number: string,
}

export default function ListDroneToChangeModal({
	profile_id,
	selectedDevice,
	show,
	onClose,
	onChangeDroneSuccess,
}: {
	profile_id: number;
	selectedDevice: DroneList | null;
	show: boolean;
	onClose: () => void;
	onChangeDroneSuccess: (data: any) => void | Promise<void>;
}) {
	console.log("selectedDevice", selectedDevice)
	// console.log("propssss__start_time", dayjs(start_time, 'DD/MM/YYYY HH:mm').toISOString());
	const { t } = useTranslation();
	const [theme] = useTheme();
	const [pageSize, setPageSize] = useState<number>();
	const [currentPage, setCurrentPage] = useState<number>(1);
	const [objSearch, setObjSearch] = useState({});
	const [refreshTable, setRefreshTable] = useState<boolean>(false);
	const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
	const { fetchChangeDroneOptions, fetchChangeDroneProfile } = useSurveillanceProfile();
	const [loading, setLoading] = useState<boolean>(false);

	const [droneList, setDroneList] = useState<{
		data: any[];
		totalItem: number;
		totalPage: number;
	}>({
		data: [],
		totalItem: 0,
		totalPage: 0,
	});

	const handleChangeDrone = async (selectedDroneUnitIdWorking: DroneChange) => {
		setIsSubmitting(true);
		const { success, message, data } = await fetchChangeDroneProfile({
			profile_id: profile_id,
			from_drone_id: selectedDevice?.id ?? 0,
			to_drone_id: selectedDroneUnitIdWorking?.device_id,
		});
		if (success) {
			console.log("data_handleChangeDrone", data)
			onChangeDroneSuccess(data);
			onClose();
		}
	};

	const columns = [
		{
			Header: '',
			accessor: 'action',
			enableSorting: false,
			enableColumnFilter: false,
			customStyle: { width: '2rem' },
			cell: (info: any) => {
				console.log("info_drones", info)
				const device_info = info.row.original ?? {}
				return (
					<Box
						display="flex"
						justifyContent="center"
					>
						<Radio
							onChange={() => handleChangeDrone(device_info)}
							sx={{
								color: '#2196F3',
								padding: 0,
								'&.Mui-checked': { color: '#2196F3' },
							}}
						/>
					</Box>
				);
			},
		},
		{
			Header: t('Name'),
			accessor: 'serial_number',
		},
		{
			Header: t('Modal'),
			accessor: 'model',
		},
		{
			Header: t('Battery'),
			accessor: 'battery',
		},
	];


	const handleFetchChangeDroneOptions = async (
		profile_id: number,
		start_waypoint_id: number,
		end_waypoint_id: number,
		objSearch: SearchObject,
		pageSize: number,
		currentPage: number,
	): Promise<void> => {
		setLoading(true);
		const { success, data } = await fetchChangeDroneOptions({
			profile_id: profile_id,
			start_waypoint_id: start_waypoint_id,
			end_waypoint_id: end_waypoint_id,
			objSearch: objSearch,
			pageSize: pageSize,
			currentPage: currentPage,
		});
		console.log("data_handleFetchChangeDroneOptions", data);
		if (success) {
			setDroneList(data);
			setRefreshTable(true)
		} else {
			const errorMessage = (data as { message?: string })?.message;
			if (errorMessage) {
				ToastTopHelper.error(errorMessage);
			}
		}
		setLoading(false);
		setRefreshTable(false)
	};


	useEffect(() => {
		if (
			show &&
			profile_id &&
			selectedDevice?.start_waypoint_id &&
			selectedDevice?.end_waypoint_id &&
			pageSize
		) {
			handleFetchChangeDroneOptions(
				profile_id,
				selectedDevice?.start_waypoint_id,
				selectedDevice?.end_waypoint_id,
				objSearch,
				pageSize,
				currentPage,
			);
		}
	}, [profile_id, pageSize, currentPage, objSearch]);

	return (
		<CustomModal
			title={t('Change Drone')}
			show={show}
			onHide={onClose}
			loading={loading}
		>
			<Box
				width="50vw"
				maxWidth="800px"
				display="flex"
				flexDirection="column"
				alignItems="center"
				gap={1}
				pb={1}
			>
				<Box width="100%">
					<CustomizableTable
						subTable={true}
						notShowSelectRow
						columns={columns}
						data={droneList}
						objSearch={objSearch}
						setObjSearch={setObjSearch}
						refreshTable={refreshTable}
						setRefreshTable={setRefreshTable}
						currentPage={currentPage}
						setCurrentPage={setCurrentPage}
						pageSize={pageSize}
						setPageSize={setPageSize}
						useSystemSetting
						loading={loading}
					/>
				</Box>

				<CustomBtn
					label={t('Cancel')}
					variant="outline"
					color="secondary"
					size="lg"
					style={{ width: '10rem' }}
					onClick={onClose}
				/>
			</Box>
		</CustomModal>
	);
}
