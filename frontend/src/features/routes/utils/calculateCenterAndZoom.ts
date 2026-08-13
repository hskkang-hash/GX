// types
type Stop = { lat: number | string; lng: number | string };

export const getGeographicCenterAndZoom = ({
  stops,
  mapWidth,
  mapHeight,
  tileSize = 256,
  maxZoom = 13,
  padding = 1.2,
}: {
  stops: Stop[];
  mapWidth: number;
  mapHeight: number;
  tileSize?: number;
  maxZoom?: number;
  padding?: number;
}) => {
  if (!stops || stops.length === 0) return { center: null, zoom: null };
  if (stops.length === 1) {
    return {
      center: {
        lat: Number(String(stops[0].lat).replace(',', '.')),
        lng: Number(String(stops[0].lng).replace(',', '.')),
      },
      zoom: 10, // Default zoom for single point
    };
  }

  // --- Center Calculation ---
  let x = 0,
    y = 0,
    z = 0;
  stops.forEach(({ lat, lng }) => {
    const latRad = (Number(String(lat).replace(',', '.')) * Math.PI) / 180;
    const lngRad = (Number(String(lng).replace(',', '.')) * Math.PI) / 180;
    x += Math.cos(latRad) * Math.cos(lngRad);
    y += Math.cos(latRad) * Math.sin(lngRad);
    z += Math.sin(latRad);
  });
  const total = stops.length;
  x /= total;
  y /= total;
  z /= total;
  const lngCenter = Math.atan2(y, x);
  const hyp = Math.sqrt(x * x + y * y);
  const latCenter = Math.atan2(z, hyp);

  const center = {
    lat: (latCenter * 180) / Math.PI,
    lng: (lngCenter * 180) / Math.PI,
  };

  // --- Bounds and Zoom ---
  const lats = stops.map((s) => Number(String(s.lat).replace(',', '.')));
  const lngs = stops.map((s) => Number(String(s.lng).replace(',', '.')));
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const latToY = (lat: number) =>
    Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 180 / 2));
  const latFraction = (latToY(maxLat) - latToY(minLat)) / Math.PI;
  const lngDiff = maxLng - minLng;
  const lngFraction = (lngDiff < 0 ? lngDiff + 360 : lngDiff) / 360;

  const latZoom = Math.floor(
    Math.log2(mapHeight / tileSize / (latFraction * padding)),
  );
  const lngZoom = Math.floor(
    Math.log2(mapWidth / tileSize / (lngFraction * padding)),
  );

  // Kakao Maps uses reverse zoom levels
  const zoom = Math.min(latZoom, lngZoom, maxZoom);
  const kakaoZoom = maxZoom - zoom; // Convert to Kakao's zoom system

  return { center, zoom: kakaoZoom };
};

export const getGeographicCenterAndZoomKakao = ({
  stops,
  map,
}: {
  stops: Stop[];
  map: kakao.maps.Map | null;
}) => {
  if (!stops || stops.length === 0) return { center: null, zoom: null };
  if (stops.length === 1 && map) {
    const { center, zoom } = getGeographicCenterAndZoomKakaoByCenter({
      stop: stops[0],
      map: map as kakao.maps.Map,
    });
    return {
      center:
        center &&
        typeof center === 'object' &&
        'getLat' in center &&
        'getLng' in center
          ? {
              lat: (center as { getLat: () => number }).getLat(),
              lng: (center as { getLng: () => number }).getLng(),
            }
          : center,
      zoom,
    };
  }

  // If map is not available, calculate center and zoom manually
  if (!map) {
    // Calculate center manually
    let x = 0,
      y = 0,
      z = 0;
    stops.forEach(({ lat, lng }) => {
      const latRad = (Number(String(lat).replace(',', '.')) * Math.PI) / 180;
      const lngRad = (Number(String(lng).replace(',', '.')) * Math.PI) / 180;
      x += Math.cos(latRad) * Math.cos(lngRad);
      y += Math.cos(latRad) * Math.sin(lngRad);
      z += Math.sin(latRad);
    });
    const total = stops.length;
    x /= total;
    y /= total;
    z /= total;
    const lngCenter = Math.atan2(y, x);
    const hyp = Math.sqrt(x * x + y * y);
    const latCenter = Math.atan2(z, hyp);

    const center = {
      lat: (latCenter * 180) / Math.PI,
      lng: (lngCenter * 180) / Math.PI,
    };

    // Calculate zoom manually
    const lats = stops.map((s) => Number(s.lat));
    const lngs = stops.map((s) => Number(s.lng));
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const latDiff = maxLat - minLat;
    const lngDiff = maxLng - minLng;
    const maxDiff = Math.max(latDiff, lngDiff);

    // Simple zoom calculation based on the maximum difference
    let zoom = 3; // Default zoom
    if (maxDiff > 10) zoom = 1;
    else if (maxDiff > 5) zoom = 2;
    else if (maxDiff > 1) zoom = 3;
    else if (maxDiff > 0.5) zoom = 4;
    else if (maxDiff > 0.1) zoom = 5;
    else if (maxDiff > 0.05) zoom = 6;
    else if (maxDiff > 0.01) zoom = 7;
    else zoom = 8;

    return { center, zoom };
  }

  // Use map if available
  const bounds = new kakao.maps.LatLngBounds();
  stops.forEach(({ lat, lng }) => {
    bounds.extend(
      new kakao.maps.LatLng(
        Number(String(lat).replace(',', '.')),
        Number(String(lng).replace(',', '.')),
      ),
    );
  });

  map.setBounds(bounds);
  const center = map.getCenter();
  const zoom = map.getLevel();

  return {
    center: { lat: center.getLat(), lng: center.getLng() },
    zoom,
  };
};

export const getGeographicCenterAndZoomKakaoByCenter = ({
  stop,
  map,
}: {
  stop: Stop;
  map: kakao.maps.Map;
}) => {
  if (!stop) return { center: null, zoom: null };
  if (typeof kakao === 'undefined' || !kakao?.maps) {
    console.warn('Kakao SDK not loaded (Kakao servers may be down).');
    return { center: null, zoom: null };
  }
  const center = new kakao.maps.LatLng(Number(stop.lat), Number(stop.lng));
  const zoomLevel = 6;

  map.setCenter(center);
  map.setLevel(zoomLevel);

  console.log('center 111', center);
  return { center, zoom: zoomLevel };
};

// Google Maps equivalent functions
export const getGeographicCenterAndZoomGoogle = ({
  stops,
  map,
}: {
  stops: Stop[];
  map: google.maps.Map | null;
}) => {
  if (!stops || stops.length === 0) {
    return { center: null, zoom: null };
  }

  // Filter out invalid coordinates
  const validStops = stops.filter((stop) => {
    const lat = Number(String(stop.lat).replace(',', '.'));
    const lng = Number(String(stop.lng).replace(',', '.'));
    return !isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0;
  });

  if (validStops.length === 0) {
    return { center: null, zoom: null };
  }

  if (validStops.length === 1) {
    const lat = Number(String(validStops[0].lat).replace(',', '.'));
    const lng = Number(String(validStops[0].lng).replace(',', '.'));
    const center = { lat, lng };
    const zoom = 13; // Good zoom level for single point

    return { center, zoom };
  }

  // If map is not available, calculate center and zoom manually
  if (!map) {
    // Calculate center manually
    let x = 0,
      y = 0,
      z = 0;
    validStops.forEach(({ lat, lng }) => {
      const latRad = (Number(String(lat).replace(',', '.')) * Math.PI) / 180;
      const lngRad = (Number(String(lng).replace(',', '.')) * Math.PI) / 180;
      x += Math.cos(latRad) * Math.cos(lngRad);
      y += Math.cos(latRad) * Math.sin(lngRad);
      z += Math.sin(latRad);
    });
    const total = validStops.length;
    x /= total;
    y /= total;
    z /= total;
    const lngCenter = Math.atan2(y, x);
    const hyp = Math.sqrt(x * x + y * y);
    const latCenter = Math.atan2(z, hyp);

    const center = {
      lat: (latCenter * 180) / Math.PI,
      lng: (lngCenter * 180) / Math.PI,
    };

    // Calculate zoom manually - Google Maps uses standard zoom levels (higher = more zoomed in)
    const lats = validStops.map((s) => Number(String(s.lat).replace(',', '.')));
    const lngs = validStops.map((s) => Number(String(s.lng).replace(',', '.')));
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const latDiff = maxLat - minLat;
    const lngDiff = maxLng - minLng;
    const maxDiff = Math.max(latDiff, lngDiff);

    // Google Maps zoom calculation (opposite of Kakao)
    let zoom = 3; // Default zoom
    if (maxDiff > 10) zoom = 1;
    else if (maxDiff > 5) zoom = 2;
    else if (maxDiff > 1) zoom = 3;
    else if (maxDiff > 0.5) zoom = 4;
    else if (maxDiff > 0.1) zoom = 5;
    else if (maxDiff > 0.05) zoom = 6;
    else if (maxDiff > 0.01) zoom = 7;
    else if (maxDiff > 0.005) zoom = 8;
    else if (maxDiff > 0.001) zoom = 9;
    else zoom = 10;

    return { center, zoom };
  }

  // Use map if available
  const bounds = new google.maps.LatLngBounds();
  validStops.forEach(({ lat, lng }) => {
    const latNum = Number(String(lat).replace(',', '.'));
    const lngNum = Number(String(lng).replace(',', '.'));
    bounds.extend(new google.maps.LatLng(latNum, lngNum));
  });

  map.fitBounds(bounds, {
    top: 20,
    right: 20,
    bottom: 20,
    left: 20,
  });

  // Get initial zoom after fitBounds
  const finalZoom = map.getZoom() || 13;
  const center = map.getCenter();

  const result = {
    center: center ? { lat: center.lat(), lng: center.lng() } : null,
    zoom: finalZoom,
  };

  return result;
};

export const getGeographicCenterAndZoomGoogleByCenter = ({
  stop,
  map,
}: {
  stop: Stop;
  map: google.maps.Map;
}) => {
  if (!stop) return { center: null, zoom: null };

  const center = { lat: Number(stop.lat), lng: Number(stop.lng) };
  const zoom = 13;

  map.setCenter(center);
  map.setZoom(zoom);

  return { center, zoom };
};
