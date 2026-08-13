import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const DailyProfileOverviewSkeleton: React.FC = () => {
	const [theme] = useTheme();

	return (
		<Box
			display="flex"
			flexDirection="column"
			flex={1}
		>
			{/* Title skeleton */}
			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'center',
				}}
			>
				<Skeleton
					variant="text"
					width={150}
					height={32}
					sx={{
						bgcolor:
							theme === 'dark'
								? 'rgba(255, 255, 255, 0.1)'
								: 'rgba(0, 0, 0, 0.1)',
					}}
				/>
				<Skeleton
					variant="text"
					width={30}
					height={30}
					sx={{
						bgcolor:
							theme === 'dark'
								? 'rgba(255, 255, 255, 0.1)'
								: 'rgba(0, 0, 0, 0.1)',
					}}
				/>
			</div>

			{/* Data items skeleton */}
			<Box
				display="flex"
				flexDirection="column"
				flex={1}
				gap="1rem"
			>
				<Skeleton
					variant="text"
					width="100%"
					height={50}
					sx={{
						bgcolor:
							theme === 'dark'
								? 'rgba(255, 255, 255, 0.1)'
								: 'rgba(0, 0, 0, 0.1)',
					}}
				/>
				<Box
					flex={1}
					display="grid"
					gap="1rem"
					gridTemplateColumns={{
						xs: '1fr',
						sm: 'repeat(2, 1fr)',
					}}
					gridAutoRows="1fr"
				>
					{Array.from({ length: 4 }).map((_, index) => (
						<>
							{index === 1 ? (
								<Box
									style={{

										display: 'flex',
										justifyContent: 'center',
										alignItems: 'center',
									}}
								>
									<Skeleton
										variant="circular"
										width={80}
										height={80}
										sx={{
											bgcolor:
												theme === 'dark'
													? 'rgba(255, 255, 255, 0.2)'
													: 'rgba(0, 0, 0, 0.1)',
										}}
									/>
								</Box>
							) : (
								<Box
									key={index}
									style={{
										background:
											theme === 'dark'
												? 'rgba(255, 255, 255, 0.1)'
												: 'rgba(0, 0, 0, 0.1)',
										gridColumn: 'auto',
										padding: '0 15px',
										borderRadius: 8,
										display: 'flex',
										flexDirection: 'column',
										justifyContent: 'center',
										alignItems: 'flex-start',
									}}
								>
									<Skeleton
										variant="text"
										width="40%"
										height={32}
										sx={{
											bgcolor:
												theme === 'dark'
													? 'rgba(255, 255, 255, 0.2)'
													: 'rgba(0, 0, 0, 0.1)',
										}}
									/>
									<Skeleton
										variant="text"
										width="20%"
										height={40}
										sx={{
											bgcolor:
												theme === 'dark'
													? 'rgba(255, 255, 255, 0.2)'
													: 'rgba(0, 0, 0, 0.1)',
										}}
									/>
								</Box>
							)}
						</>
					))}
				</Box>
			</Box>
		</Box>
	);
};

export default DailyProfileOverviewSkeleton;
