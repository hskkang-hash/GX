import L from 'leaflet';
import 'leaflet-simple-map-screenshoter';
import 'leaflet/dist/leaflet.css';

// Type definition for the screenshoter plugin
interface SimpleMapScreenshoter {
  addTo(map: L.Map): SimpleMapScreenshoter;
  takeScreen(format: 'blob'): Promise<Blob>;
}

// Extend Leaflet interface to include the plugin
interface LeafletWithScreenshoter {
  simpleMapScreenshoter(options: {
    mimeType: string;
    hideElementsWithSelectors: string[];
  }): SimpleMapScreenshoter;
}

/**
 * 🗺️ Function to create a map and return a PNG image
 * @param {Array<{lat:number, lng:number}>} markers - list of markers
 * @param {Object} [options] - additional options (width, height)
 * @returns {Promise<Blob>} Blob object of the map image
 */
export async function generateMapImage(
  markers: Array<{ lat: number; lng: number }>,
  options: { width?: string; height?: string } = {},
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    try {
      // 1️⃣ Create temporary container
      const mapContainer = document.createElement('div');
      mapContainer.style.width = options.width || '400px';
      mapContainer.style.height = options.height || '300px';
      mapContainer.style.position = 'absolute';
      mapContainer.style.top = '-9999px';
      document.body.appendChild(mapContainer);

      // 2️⃣ Initialize map (temporary center/zoom)
      const map = L.map(mapContainer, {
        center: [0, 0],
        zoom: 2,
        zoomControl: false,
        attributionControl: false,
      });

      // 3️⃣ Add tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
      }).addTo(map);

      // 4️⃣ Add markers and save positions
      const markerList: L.Marker[] = [];
      const polylinePoints: [number, number][] = [];

      markers.forEach((m) => {
        const marker = L.marker([m.lat, m.lng]).addTo(map);
        markerList.push(marker);
        polylinePoints.push([m.lat, m.lng]);
      });

      // 5️⃣ Draw polyline connecting points (if any)
      if (polylinePoints.length > 1) {
        L.polyline(polylinePoints, { color: 'red', weight: 3 }).addTo(map);
      }

      // 6️⃣ Calculate bounds from markers
      if (markerList.length > 0) {
        const group = L.featureGroup(markerList);
        const bounds = group.getBounds();
        map.fitBounds(bounds, { padding: [30, 30] }); // padding to avoid edge clipping
      }

      // 7️⃣ Initialize Screenshoter plugin
      const screenshoter = (
        L as unknown as LeafletWithScreenshoter
      ).simpleMapScreenshoter({
        mimeType: 'image/png',
        hideElementsWithSelectors: ['.leaflet-control-container'],
      });
      screenshoter.addTo(map);

      // 8️⃣ When map is ready -> take screenshot
      map.whenReady(async () => {
        setTimeout(async () => {
          try {
            const blob = await screenshoter.takeScreen('blob');
            resolve(blob);
          } catch (error) {
            reject(error);
          } finally {
            map.remove();
            mapContainer.remove();
          }
        }, 1000);
      });
    } catch (err) {
      reject(err);
    }
  });
}
