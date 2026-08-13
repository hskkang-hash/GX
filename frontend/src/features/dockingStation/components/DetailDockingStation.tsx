import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  useConfigGroupSystem,
  useTheme,
} from 'rj-core';

import ErrorImage from '@/assets/images/no-image.png';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { checkCodeValid } from '@/utils/CheckCodeValid';
import { useDebounce } from '@/utils/utils';

import '../styles/DetailDockingStation.scss';

const DetailDockingStation = ({
  initialData,
  onEdit,
  loading,
  breadcrumbItems,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);

  const { getAddressByLatLong, fetchAddressDetail } = useCommonAPI();

  // Apply debounce to form values
  const debouncedLatitude = useDebounce(initialData?.latitude, 800);
  const debouncedLongitude = useDebounce(initialData?.longitude, 800);
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const countryCode = configGroupSystem?.use_map?.country_code || 'KR';
  const isKoreaCountry = checkCodeValid(countryCode?.toUpperCase()) === 'KR';

  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    // Only use Kakao reverse geocoding if we're in Korea
    if (!isKoreaCountry && isSystemUseGoogleMap) {
      console.log('Skipping Kakao reverse geocoding for non-Korea country');
      return;
    }

    try {
      const { data, status } = await getAddressByLatLong(lat, long);
      if (status) {
        // Get zone code from address search
        const addressDetail = await fetchAddressDetail(
          data?.address_name || '',
        );
        console.log('Korea address details fetched:', { data, addressDetail });
      }
    } catch (error) {
      console.error('Error fetching Korea address by lat/long:', error);
    }
  };

  useEffect(() => {
    if (debouncedLatitude && debouncedLongitude) {
      fetchRegionByLatLong(debouncedLatitude, debouncedLongitude);
    }

    if (debouncedLatitude && debouncedLongitude) {
      setMarkerData([
        {
          lat: debouncedLatitude,
          lng: debouncedLongitude,
        },
      ]);
    } else {
      setMarkerData([]);
    }
  }, [debouncedLatitude, debouncedLongitude]);

  return (
    <div id="detail-docking-station">
      <CustomBreadcrumb
        items={breadcrumbItems}
        buttons={[
          <CustomBtn
            key="cancel-btn"
            label={t('Edit')}
            variant="outline"
            color="primary"
            size="md"
            style={{ width: '6rem' }}
            type="button"
            onClick={onEdit}
          />,
        ]}
      />
      <Main>
        <div
          className="detail-docking-station-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: '60fr 40fr',
            gap: '1rem',
            minHeight: '300px',
            alignItems: 'stretch',
            marginBottom: '1rem',
          }}
        >
          <div
            className="map-container"
            style={{ height: '100%', borderRadius: '0.75em' }}
          >
            <Map
              center={
                markerData.length > 0
                  ? { lat: markerData[0].lat, lng: markerData[0].lng }
                  : undefined
              }
              operatingMarkers={markerData.length > 0 ? markerData : []}
              polylines={markerData.length > 0 ? [markerData] : []}
              style={{
                height: '100%',
                minHeight: '300px',
                width: '100%',
                borderRadius: '8px',
              }}
            />
          </div>
          <div
            className="image-container"
            style={{ height: '100%', borderRadius: '0.75em' }}
          >
            <img
              src={
                import.meta.env.VITE_API_URL + initialData?.avatar__file_url ||
                ErrorImage
              }
              alt="image"
              onError={(e: React.SyntheticEvent<HTMLImageElement, Event>) => {
                (e.target as HTMLImageElement).src = ErrorImage;
              }}
              className="detail-infrastructure__image"
              style={{
                width: '100%',
                height: 'auto',
                objectFit: 'cover',
                borderRadius: '8px',
              }}
            />
          </div>
        </div>
        <FormBlock className={`${theme === 'dark' ? 'dark-theme' : ''}`}>
          <div
            className="detail-docking-station-table"
            style={{ padding: 0 }}
          >
            <div
              style={{
                fontWeight: 600,
                fontSize: 18,
                marginBottom: 12,
              }}
            >
              {t('Detailed Information')}
            </div>
            <table
              style={{
                width: '100%',
                borderCollapse: 'separate',
                borderSpacing: 0,
                background: '#fff',
                overflow: 'hidden',
              }}
            >
              <tbody>
                <tr style={{}}>
                  <th
                    style={{
                      fontWeight: 600,
                    }}
                  >
                    {t('Name')}
                  </th>
                  <td>{initialData?.name || '-'}</td>
                  <th>{t('ID')}</th>
                  <td>{initialData?.code || '-'}</td>
                  <th>{t('Type')}</th>
                  <td>{initialData?.docking_station_type__name || '-'}</td>
                  <th>{t('Manager')}</th>
                  <td>{initialData?.manager_name || '-'}</td>
                  <th>{t('Created Date')}</th>
                  <td>{initialData?.created_on || '-'}</td>
                </tr>
                <tr>
                  <th>{t('Latitude')}</th>
                  <td>{initialData?.latitude ?? '-'}</td>
                  <th>{t('Longitude')}</th>
                  <td>{initialData?.longitude ?? '-'}</td>
                  <th>{t('Address')}</th>
                  <td colSpan={5}>{initialData?.address || '-'}</td>
                </tr>
                <tr>
                  <th>{t('URL')}</th>
                  <td colSpan={3}>{initialData?.url || '-'}</td>
                  <th>{t('Manufacturer')}</th>
                  <td>{initialData?.manufacturer || '-'}</td>
                  <th>{t('Year of Manufacture')}</th>
                  <td>{initialData?.year_of_manufacture || '-'}</td>
                  <th>{t('Remarks')}</th>
                  <td>{initialData?.note || '-'}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </FormBlock>
      </Main>
    </div>
  );
};

export default DetailDockingStation;
