import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { Container, CustomBreadcrumb, CustomBtn, Main } from 'rj-core';

import { CustomRoutes } from '@/services/API';

import DetailInfoSection from '../components/DetailInfoSection';
import MapAndImageSection from '../components/MapAndImageSection';
import { useDeliveryHubs } from '../hooks/useDeliveryHubs';
import { useDeliveryHubsStore } from '../store';

export const DetailDeliveryHubs = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { deliveryHubDetail, setDeliveryHub } = useDeliveryHubsStore();
  const { getDetailDeliveryHubsAPI } = useDeliveryHubs();

  console.log('Delivery Hub Detail:', deliveryHubDetail, id);

  useEffect(() => {
    if (deliveryHubDetail === null && id) {
      getDetailDeliveryHubsAPI(Number(id)).then((response) => {
        if (response.success) {
          setDeliveryHub(response.data);
        } else {
          navigate(CustomRoutes.deliveryHubs.path);
        }
      });
    }
  }, [id]);

  return (
    <Container>
      <CustomBreadcrumb
        items={[
          { url: CustomRoutes.deliveryHubs.path },
          { text: 'Detailed Information' },
        ]}
        buttons={[
          <CustomBtn
            variant="outline"
            color="primary"
            label={t('Edit')}
            size="md"
            onClick={() =>
              navigate(
                CustomRoutes.deliveryHubs.subRoutes.editDeliveryHubs.path.replace(
                  ':id',
                  id || '',
                ),
              )
            }
          />,
        ]}
      />
      <Main>
        <div className="d-flex flex-column gap-3">
          <MapAndImageSection
            markerData={[
              {
                lat: deliveryHubDetail?.latitude || 0,
                lng: deliveryHubDetail?.longitude || 0,
              },
            ]}
            img_hub={
              deliveryHubDetail?.avatar__file_url
                ? import.meta.env.VITE_API_URL +
                  deliveryHubDetail?.avatar__file_url
                : null
            }
          />
          <DetailInfoSection
            detailRows={[
              [
                {
                  label: t('Name'),
                  value: deliveryHubDetail?.name || '-',
                  colSpan: 1,
                },
                {
                  label: t('hubs-ID'),
                  value: deliveryHubDetail?.code || '-',
                  colSpan: 1,
                },
                {
                  label: t('Type'),
                  value: deliveryHubDetail?.terminal_base_type || '-',
                  colSpan: 1,
                },
                {
                  label: t('Manager'),
                  value: deliveryHubDetail?.manager_name || '-',
                  colSpan: 1,
                },
                {
                  label: t('Created Date'),
                  value: deliveryHubDetail?.created_on || '-',
                  colSpan: 1,
                },
              ],
              [
                {
                  label: t('Latitude'),
                  value: deliveryHubDetail?.latitude || '-',
                  colSpan: 1,
                },
                {
                  label: t('Longitude'),
                  value: deliveryHubDetail?.longitude || '-',
                  colSpan: 1,
                },
                {
                  label: t('Address'),
                  value:
                    deliveryHubDetail?.full_address ||
                    deliveryHubDetail?.address ||
                    '-',
                  colSpan: 3,
                },
                {
                  label: t('Postal Code'),
                  value: deliveryHubDetail?.postal_code || '-',
                  colSpan: 1,
                },
              ],
              [
                {
                  label: t('URL'),
                  value: deliveryHubDetail?.url || '-',
                  colSpan: 3,
                },
                {
                  label: t('Remarks'),
                  value: deliveryHubDetail?.note || '-',
                  colSpan: 5,
                },
              ],
            ]}
          />
        </div>
      </Main>
    </Container>
  );
};
