import { useMap, useMapsLibrary } from '@vis.gl/react-google-maps';
import { useEffect } from 'react';

type LatLngLiteral = google.maps.LatLngLiteral;

interface PolylineProps {
  path: LatLngLiteral[];
  strokeColor?: string;
  strokeOpacity?: number;
  strokeWeight?: number;
  /* bạn có thể thêm các option khác của google.maps.PolylineOptions nếu muốn */
}

export function Polyline({
  path,
  strokeColor = '#0000FF',
  strokeOpacity = 0.6,
  strokeWeight = 3,
}: PolylineProps) {
  const map = useMap();
  const mapsLib = useMapsLibrary('core'); // lấy namespace google.maps

  useEffect(() => {
    if (!map || !mapsLib) return;

    // Tạo polyline
    const polyline = new google.maps.Polyline({
      map,
      path,
      strokeColor,
      strokeOpacity,
      strokeWeight,
    });

    // Khi path, màu, v.v thay đổi => cập nhật
    return () => {
      // cleanup: xóa polyline khỏi map khi component unmount
      polyline.setMap(null);
    };
  }, [map, mapsLib, path, strokeColor, strokeOpacity, strokeWeight]);

  return null; // vì không render React node nào — polyline vẽ lên map
}
