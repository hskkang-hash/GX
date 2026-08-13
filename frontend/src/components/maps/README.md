# Maps Migration Guide

This directory contains a unified map system that supports both Kakao Maps and Google Maps providers.

## Quick Start

### Basic Usage
```tsx
import { Map } from '@/components/maps';

// Use the unified Map component
<Map
  operatingMarkers={markers}
  standbyMarkers={standbyMarkers}
  polylines={routes}
  centerTerminal={{ lat: 37.5665, lng: 126.978 }}
  style={{ height: '400px' }}
  overlayContent={<div>Custom overlay</div>}
  smallMarker={false}
/>
```

## Configuration

### Environment Variables

Add these environment variables to your `.env` file:

```bash
# Map provider: 'kakao' or 'google' (now defaults to 'google')
VITE_MAP_PROVIDER=google

# Google Maps API Key (required when using Google Maps)
VITE_GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here

# Kakao Maps API Key (optional, for future use)
VITE_KAKAO_MAPS_API_KEY=your_kakao_api_key
```

### Switching Providers

To switch from Kakao Maps to Google Maps:

1. Set `VITE_MAP_PROVIDER=google` in your environment
2. Ensure `VITE_GOOGLE_MAPS_API_KEY` is set
3. Restart your development server

No code changes are needed!

## Migration from MapKakao

### Before (using MapKakao directly)
```tsx
import MapKakao from '@/components/maps/MapKakao';

<MapKakao
  operatingMarkers={markers}
  standbyMarkers={standbyMarkers}
  polylines={routes}
  centerTerminal={{ lat: 37.5665, lng: 126.978 }}
  style={{ height: '400px' }}
/>
```

### After (using unified Map)
```tsx
import { Map } from '@/components/maps';

<Map
  operatingMarkers={markers}
  standbyMarkers={standbyMarkers}
  polylines={routes}
  centerTerminal={{ lat: 37.5665, lng: 126.978 }}
  style={{ height: '400px' }}
/>
```

The interface is identical! Just change the import and component name.

## Components

### Map (Unified Component)
- **File**: `Map.tsx`
- **Description**: Main component that automatically selects between Kakao and Google Maps
- **Usage**: Primary component for all new map implementations

### MapKakao (Kakao Maps Provider)
- **File**: `MapKakao.tsx`
- **Description**: Original Kakao Maps implementation
- **Usage**: Use directly if you specifically need Kakao Maps only

### MapGoogle (Google Maps Provider)
- **File**: `MapGoogle.tsx`
- **Description**: New Google Maps implementation with identical interface to MapKakao
- **Usage**: Use directly if you specifically need Google Maps only

## Features

Both map providers support:

✅ **Markers**: Operating and standby markers with custom icons
✅ **Polylines**: Route paths with robot/normal differentiation
✅ **Auto-centering**: Automatic center and zoom calculation based on markers
✅ **Controls**: Zoom in/out, fullscreen toggle, map type/overlay toggle
✅ **Clustering**: Automatic marker clustering for better performance
✅ **Responsive**: Mobile-friendly with different marker sizes
✅ **Theming**: Dark/light theme support for overlay content
✅ **Custom Overlays**: Support for custom overlay content

## API Reference

### Props Interface

```tsx
interface MapProps {
  centerTerminal?: { lat: number; lng: number } | null;
  level?: number;
  operatingMarkers?: MarkerData[];
  standbyMarkers?: MarkerData[];
  polylines?: PolylinePath[][];
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: MapBounds;
  fitBounds?: boolean;
  boundsPadding?: number;
}

interface MarkerData {
  lat: number | null | undefined;
  lng: number | null | undefined;
  name?: string;
  icon?: string;
  terminal_name?: string;
}

interface PolylinePath {
  lat: number | null | undefined;
  lng: number | null | undefined;
  for_robot?: boolean; // Green for robot routes, red for normal
}
```

### Configuration

```tsx
import { MAP_CONFIG } from '@/components/maps';

console.log(MAP_CONFIG.PROVIDER); // 'kakao' | 'google'
console.log(MAP_CONFIG.GOOGLE_MAPS_API_KEY); // Google Maps API key
console.log(MAP_CONFIG.KAKAO_MAPS_API_KEY); // Kakao Maps API key
```

## Utility Functions

Center and zoom calculation utilities are available for both providers:

```tsx
import {
  getGeographicCenterAndZoomKakao,
  getGeographicCenterAndZoomGoogle,
  getGeographicCenterAndZoomKakaoByCenter,
  getGeographicCenterAndZoomGoogleByCenter
} from '@/features/routes/utils/calculateCenterAndZoom';
```

## Implementation Notes

### Google Maps Specific
- Uses `@vis.gl/react-google-maps` library
- Supports Advanced Markers with clustering
- Standard Google Maps zoom levels (higher = more zoomed in)
- Map types: roadmap, satellite, hybrid, terrain

### Kakao Maps Specific
- Uses `react-kakao-maps-sdk` library
- Reverse zoom levels (lower = more zoomed in)
- Overlay types: traffic, roadview, terrain, district

### Polylines
- **Green**: Robot delivery routes (`for_robot: true`)
- **Red**: Normal delivery routes (`for_robot: false` or undefined)

### Performance
- Both implementations use React.memo for optimization
- Marker clustering enabled by default for Google Maps
- Invalid coordinates (0,0) are automatically filtered out

## Troubleshooting

### Google Maps not loading
1. Check if `VITE_GOOGLE_MAPS_API_KEY` is set correctly
2. Verify the API key has Maps JavaScript API enabled
3. Check browser console for API errors

### Kakao Maps not loading
1. Ensure Kakao Maps SDK is loaded in your HTML
2. Check if `kakao` object is available globally

### Markers not showing
1. Verify marker data has valid `lat` and `lng` values (numbers or numeric strings)
2. Check that coordinates are not `(0, 0)`
3. Ensure markers are within the map bounds
4. The component automatically converts string coordinates to numbers

### Google Maps coordinate errors
The Google Maps component automatically handles coordinate type conversion:
- String coordinates are converted to numbers using `Number()`
- Invalid coordinates (NaN, 0, null, undefined) are filtered out
- A Map ID is automatically provided for Advanced Markers support

For more help, check the browser console for error messages.