import dayjs from "dayjs";

// Helper function to parse datetime string to HH:mm format
export const parseTimeFromDateTime = (dateTimeStr: string, datetimeFormat: string): string => {
	if (!dateTimeStr) {
		return '00:00';
	}
	return dayjs(dateTimeStr, datetimeFormat).format('HH:mm');
};

// Helper function to darken color
export const darkenColor = (color: string, percent: number = 0.3): string => {
	const num = parseInt(color.replace('#', ''), 16);
	const r = Math.max(0, Math.floor((num >> 16) * (1 - percent)));
	const g = Math.max(0, Math.floor(((num >> 8) & 0x00FF) * (1 - percent)));
	const b = Math.max(0, Math.floor((num & 0x0000FF) * (1 - percent)));
	return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
};

// Helper function to blend color with background color
// Blend formula: finalColor = color * alpha + backgroundColor * (1 - alpha)
export const blendWithBackground = (color: string, alphaHex: string, backgroundColor: string): string => {
	const num = parseInt(color.replace('#', ''), 16);
	const r = (num >> 16) & 0xFF;
	const g = (num >> 8) & 0xFF;
	const b = num & 0xFF;
	const alpha = parseInt(alphaHex, 16) / 255;

	const bgNum = parseInt(backgroundColor.replace('#', ''), 16);
	const bgR = (bgNum >> 16) & 0xFF;
	const bgG = (bgNum >> 8) & 0xFF;
	const bgB = bgNum & 0xFF;

	// Blend with background color
	const blendedR = Math.round(r * alpha + bgR * (1 - alpha));
	const blendedG = Math.round(g * alpha + bgG * (1 - alpha));
	const blendedB = Math.round(b * alpha + bgB * (1 - alpha));

	return `rgb(${blendedR}, ${blendedG}, ${blendedB})`;
};

// Helper function to convert time string to minutes
export const timeToMinutes = (timeStr: string): number => {
	const [hours, minutes] = timeStr.split(':').map(Number);
	if (isNaN(hours) || isNaN(minutes)) {
		return 0;
	}
	return hours * 60 + minutes;
};


// Helper function to validate and normalize time
export const normalizeTime = (timeStr: string): string => {
	if (!timeStr || !timeStr.includes(':')) {
		return '00:00';
	}
	const [hours, minutes] = timeStr.split(':').map(Number);
	if (isNaN(hours) || isNaN(minutes)) {
		return '00:00';
	}
	// Clamp hours to 0-23 and minutes to 0-59
	const normalizedHours = Math.max(0, Math.min(23, hours));
	const normalizedMinutes = Math.max(0, Math.min(59, minutes));
	return `${String(normalizedHours).padStart(2, '0')}:${String(normalizedMinutes).padStart(2, '0')}`;
};

export const getEventPosition = (startTime: string, endTime: string, HOUR_WIDTH: number) => {
	const normalizedStart = normalizeTime(startTime);
	const normalizedEnd = normalizeTime(endTime);

	const startMinutes = timeToMinutes(normalizedStart);
	let endMinutes = timeToMinutes(normalizedEnd);

	// Handle case where end time is before start time (crosses midnight)
	if (endMinutes <= startMinutes) {
		endMinutes = startMinutes + 60; // Default to 1 hour duration
	}
	// Clamp to 24 hours (1440 minutes)
	const clampedStartMinutes = Math.max(0, Math.min(1440, startMinutes));
	const clampedEndMinutes = Math.max(clampedStartMinutes, Math.min(1440, endMinutes));

	const duration = clampedEndMinutes - clampedStartMinutes;

	// Calculate position in pixels: each hour = 300px, each minute = 5px
	const leftPx = (clampedStartMinutes / 60) * HOUR_WIDTH;
	const widthPx = (duration / 60) * HOUR_WIDTH;

	return { left: `${leftPx}px`, width: `${widthPx}px` };
};