import { useMap } from '@vis.gl/react-google-maps';
import React, { useEffect, useRef } from 'react';

export interface ProfilePolygonData {
	is_line_mission?: boolean;
	polygon: Array<[number, number]> | Array<{ lat: number; lng: number }>;
}

interface PolygonOverlayProps {
	profiles: ProfilePolygonData[];
	selectedProfileId?: number | null;
}

// Helper function to convert different polygon formats to Google Maps LatLng
const normalizePolygonCoords = (
	polygon: Array<[number, number]> | Array<{ lat: number; lng: number }>
): google.maps.LatLngLiteral[] => {
	if (!polygon || polygon.length === 0) return [];

	const firstPoint = polygon[0];

	if (Array.isArray(firstPoint)) {
		return (polygon as Array<[number, number]>).map(([lat, lng]) => ({
			lat,
			lng,
		}));
	} else {
		return polygon as google.maps.LatLngLiteral[];
	}
};

const PolygonOverlay: React.FC<PolygonOverlayProps> = ({
	profiles,
	selectedProfileId,
}) => {
	const map = useMap();
	const polygonsRef = useRef<google.maps.Polygon[]>([]);

	useEffect(() => {
		if (!map || !profiles || profiles.length === 0) {
			polygonsRef.current.forEach((polygon) => polygon.setMap(null));
			polygonsRef.current = [];
			return;
		}

		// Clean up existing polygons
		polygonsRef.current.forEach((polygon) => polygon.setMap(null));
		polygonsRef.current = [];

		// Create polygons for each profile
		profiles.forEach((profile) => {
			const coords = normalizePolygonCoords(profile.polygon);
			if (coords.length < 2) return;

			const polygon = new google.maps.Polygon({
				paths: coords,
				strokeColor: '#1D9BE2',
				strokeOpacity: 0.8,
				strokeWeight: 2,
				fillColor: '#1D9BE2',
				fillOpacity: 0.25,
				clickable: true,
			});
			polygon.setMap(map);
			polygonsRef.current.push(polygon);
		});

		// Fit map bounds to show all polygons
		if (profiles.length > 0) {
			const bounds = new google.maps.LatLngBounds();

			profiles.forEach((profile) => {
				const coords = normalizePolygonCoords(profile.polygon);
				coords.forEach((coord) => {
					bounds.extend(coord);
				});
			});

			if (!bounds.isEmpty()) {
				map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
			}
		}

		return () => {
			polygonsRef.current.forEach((polygon) => polygon.setMap(null));
			polygonsRef.current = [];
		};
	}, [map, profiles, selectedProfileId]);

	useEffect(() => {
		return () => {
			polygonsRef.current.forEach((polygon) => polygon.setMap(null));
			polygonsRef.current = [];
		};
	}, []);

	return null;
};

export default React.memo(PolygonOverlay);
