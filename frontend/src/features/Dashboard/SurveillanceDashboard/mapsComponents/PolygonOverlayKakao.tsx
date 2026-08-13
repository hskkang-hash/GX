import React, { useEffect, useRef } from 'react';

export interface ProfilePolygonData {
	profile_id: number;
	profile_name: string;
	profile_code: string;
	color_code: string;
	start_time?: string;
	mission_id?: number;
	is_line_mission?: boolean;
	polygon: Array<[number, number]> | Array<{ lat: number; lng: number }>;
	status_code?: string;
	status_name?: string;
}

interface PolygonOverlayKakaoProps {
	map: kakao.maps.Map | null;
	profiles: ProfilePolygonData[];
	selectedProfileId?: number | null;
	isDarkTheme?: boolean;
}

// Helper function to convert different polygon formats to Kakao Maps LatLng
const normalizePolygonCoords = (
	polygon: Array<[number, number]> | Array<{ lat: number; lng: number }>
): { lat: number; lng: number }[] => {
	if (!polygon || polygon.length === 0) return [];

	const firstPoint = polygon[0];

	if (Array.isArray(firstPoint)) {
		return (polygon as Array<[number, number]>).map(([lat, lng]) => ({
			lat,
			lng,
		}));
	} else {
		return polygon as { lat: number; lng: number }[];
	}
};

// Invert color for dark theme
const invertColor = (hex: string): string => {
	hex = hex.replace('#', '');

	const r = parseInt(hex.slice(0, 2), 16);
	const g = parseInt(hex.slice(2, 4), 16);
	const b = parseInt(hex.slice(4, 6), 16);

	const invertedR = 255 - r;
	const invertedG = 255 - g;
	const invertedB = 255 - b;

	return `#${invertedR.toString(16).padStart(2, '0')}${invertedG.toString(16).padStart(2, '0')}${invertedB.toString(16).padStart(2, '0')}`;
};

const PolygonOverlayKakao: React.FC<PolygonOverlayKakaoProps> = ({
	map,
	profiles,
	selectedProfileId,
	isDarkTheme = false,
}) => {
	const polygonsRef = useRef<kakao.maps.Polygon[]>([]);

	useEffect(() => {
		if (!map || typeof kakao === 'undefined') return;

		// Clean up existing polygons
		polygonsRef.current.forEach((polygon) => polygon.setMap(null));
		polygonsRef.current = [];

		if (!profiles || profiles.length === 0) {
			return;
		}

		// Create polygons for each profile
		profiles.forEach((profile) => {
			const coords = normalizePolygonCoords(profile.polygon);

			if (coords.length < 3) return;

			const isSelected = selectedProfileId === profile.profile_id;
			const colorCode = isDarkTheme
				? invertColor(profile.color_code || '#1D9BE2')
				: profile.color_code || '#1D9BE2';

			const path = coords.map(
				(coord) => new kakao.maps.LatLng(coord.lat, coord.lng)
			);

			const polygon = new kakao.maps.Polygon({
				path: path,
				strokeWeight: 2,
				strokeColor: colorCode,
				strokeOpacity: 0.8,
				strokeStyle: 'solid',
				fillColor: colorCode,
				fillOpacity: 0.25,
				zIndex: isSelected ? 10 : 1,
			});

			polygon.setMap(map);
			polygonsRef.current.push(polygon);
		});

		// Fit map bounds to show all polygons
		if (profiles.length > 0) {
			const bounds = new kakao.maps.LatLngBounds();

			profiles.forEach((profile) => {
				const coords = normalizePolygonCoords(profile.polygon);
				coords.forEach((coord) => {
					bounds.extend(new kakao.maps.LatLng(coord.lat, coord.lng));
				});
			});

			map.setBounds(bounds, 50, 50, 50, 50);
		}

		return () => {
			polygonsRef.current.forEach((polygon) => polygon.setMap(null));
			polygonsRef.current = [];
		};
	}, [map, profiles, selectedProfileId, isDarkTheme]);

	useEffect(() => {
		return () => {
			polygonsRef.current.forEach((polygon) => polygon.setMap(null));
			polygonsRef.current = [];
		};
	}, []);

	return null;
};

export default React.memo(PolygonOverlayKakao);
