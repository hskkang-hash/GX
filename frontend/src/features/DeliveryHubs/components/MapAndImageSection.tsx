import React from 'react';

import ErrorImage from '@/assets/images/no-image.png';
import { Map } from '@/components/maps';

import { Marker } from '../types/IDeliveryHubs';

interface MapAndImageSectionProps {
  markerData?: Marker[];
  img_hub?: string | null;
}

const MapAndImageSection = ({
  markerData = [],
  img_hub = '',
}: MapAndImageSectionProps) => {
  return (
    <div className="row">
      {/* // col 7 3 */}
      <div className="col-7 pe-2">
        <Map
          center={
            markerData.length > 0
              ? { lat: markerData[0].lat, lng: markerData[0].lng }
              : undefined
          }
          operatingMarkers={markerData.length > 0 ? markerData : []}
          polylines={markerData.length > 0 ? [markerData] : []}
          style={{ height: '25rem' }}
        />
      </div>
      <div className="col-5 ps-2">
        <img
          src={img_hub || ErrorImage}
          alt="Delivery Hub"
          className="img-fluid"
          style={{
            height: '25rem',
            width: '100%',
            objectFit: 'cover',
            borderRadius: '8px',
          }}
        />
      </div>
    </div>
  );
};

export default React.memo(MapAndImageSection);
