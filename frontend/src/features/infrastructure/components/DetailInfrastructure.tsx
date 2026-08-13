import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  useTheme,
} from 'rj-core';

import ErrorImage from '@/assets/images/no-image.png';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import API, { endpoint } from '@/services/API';
import { useDebounce } from '@/utils/utils';

import '../styles/DetailInfrastructure.scss';

// Define types for form data and select options
interface SelectOption {
  value: string;
  label: string;
}

const DetailInfrastructure = ({
  initialData,
  onEdit,
  loading,
  breadcrumbItems,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { getOptionsByModel } = useCommonAPI();
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);

  const getInfastructureType = async () => {
    const response = await API.get(endpoint.getDataForSelectInput, {
      params: {
        model_name: 'terminalType',
        multi_language: true,
        search_term: '',
        page_number: 1,
        page_size: 10,
        distinct: true,
        search_field: '',
      },
    });
    const infrastructureType = response.data?.find(
      (item: any) => item?.code === 'INFRASTRUCTURE',
    );
    console.log('infrastructureType', infrastructureType);
    return infrastructureType
      ? {
          value: infrastructureType?.id,
          label: infrastructureType?.name,
        }
      : null;
  };

  const { getAddressByLatLongSafe, fetchAddressDetail } = useCommonAPI();

  // Apply debounce to form values
  const debouncedLatitude = useDebounce(initialData?.latitude, 800);
  const debouncedLongitude = useDebounce(initialData?.longitude, 800);

  const fetchRegionByLatLong = async (lat: number, long: number) => {
    if (!lat || !long) return;

    const { data, status } = await getAddressByLatLongSafe(lat, long);
    // Get zone code from address search
    const addressDetail = await fetchAddressDetail(data?.address_name || '');
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
    <div id="detail-infrastructure">
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
          className="detail-infrastructure-grid"
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
            className="detail-infrastructure-table"
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
                  <th>{t('Major Category')}</th>
                  <td>{initialData?.terminal_purpose || '-'}</td>
                  <th>{t('Subcategory')}</th>
                  <td>{initialData?.infrastructure_type__name || '-'}</td>
                  <th>{t('Manufacturer')}</th>
                  <td>{initialData?.manufacturer || '-'}</td>
                  <th>{t('Year of Manufacture')}</th>
                  <td>{initialData?.year_of_manufacture || '-'}</td>
                </tr>
                <tr>
                  <th>{t('Latitude')}</th>
                  <td>{initialData?.latitude ?? '-'}</td>
                  <th>{t('Longitude')}</th>
                  <td>{initialData?.longitude ?? '-'}</td>
                  <th>{t('Purpose')}</th>
                  <td>{initialData?.purpose_type || '-'}</td>
                  <th>{t('Manager')}</th>
                  <td>{initialData?.manager_name || '-'}</td>
                  <th>{t('Created Date')}</th>
                  <td>{initialData?.created_on || '-'}</td>
                </tr>
                <tr>
                  <th>{t('URL')}</th>
                  <td colSpan={3}>{initialData?.url || '-'}</td>
                  <th>{t('Remarks')}</th>
                  <td colSpan={5}>{initialData?.note || '-'}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </FormBlock>
      </Main>
    </div>
  );
};

export default DetailInfrastructure;
