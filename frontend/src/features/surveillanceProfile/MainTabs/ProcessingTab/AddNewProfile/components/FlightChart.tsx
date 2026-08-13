import { useTheme } from 'rj-core';
import { ChartDataItem } from '../AddNewProfile.d';
import { useTranslation } from 'react-i18next';
import { textLabel } from '@/configs/Colors';
import {
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts';


const CustomTooltip = ({
	active,
	payload,
	t,
}: {
	active?: boolean;
	payload?: any;
	t?: any;
}) => {
	if (active && payload && payload.length) {
		const data = payload[0].payload;
		return (
			<div
				style={{
					backgroundColor: 'white',
					border: '1px solid #ccc',
					borderRadius: '4px',
					padding: '10px',
					boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
				}}
			>
				<p
					style={{
						margin: '0 0 5px 0',
						fontWeight: 'bold',
						color: '#000000',
					}}
				>
					{data.waypointName}
				</p>
				<p style={{ margin: '0 0 3px 0', color: '#7086FD' }}>
					{t('Cruise Speed')}: {data.cruise_speed} m/s
				</p>
				<p style={{ margin: '0', color: '#6FD195' }}>
					{t('Operating Altitude')}: {data.operating_altitude} m
				</p>
			</div>
		);
	}
	return null;
};

const FlightChart = ({ chartData, label }: { chartData: ChartDataItem[], label: string }) => {
	const { t } = useTranslation();
	const [theme] = useTheme();
	return (
		<div>
			<div
				style={{
					fontWeight: 600,
					fontSize: '1.2rem',
					marginBottom: '1rem',
				}}
			>
				{label}
			</div>
			<div
				style={{
					flex: 1,
					width: '100%',
					height: '29.2rem',
				}}
			>
				<ResponsiveContainer
					width="100%"
					height="100%"
				>
					<LineChart
						data={chartData}
						margin={{
							top: 10,
							right: 30,
							left: 0,
							bottom: 0,
						}}
					>
						<CartesianGrid strokeDasharray="3 3" />
						<XAxis
							dataKey="cumulativeDistance"
							stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
							label={{
								position: 'insideBottom',
								offset: -5,
							}}
						/>
						<YAxis
							stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
						/>
						<Tooltip content={<CustomTooltip t={t} />} />
						<Legend />
						<Line
							type="linear"
							dataKey="cruise_speed"
							stroke="#7086FD"
							activeDot={{ r: 8 }}
							name={t('Cruise Speed (m/s)')}
						/>
						<Line
							type="linear"
							dataKey="operating_altitude"
							stroke="#6FD195"
							activeDot={{ r: 8 }}
							name={t('Altitude/Z')}
						/>
					</LineChart>
				</ResponsiveContainer>
			</div>
		</div>

	)
}

export default FlightChart