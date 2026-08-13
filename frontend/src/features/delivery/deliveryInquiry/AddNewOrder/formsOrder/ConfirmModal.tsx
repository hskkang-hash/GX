import Box from '@mui/material/Box';
import React from 'react';
import { Control, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomBtn, CustomModal } from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import Colors from '@/configs/Colors';

import { IFormData } from './Helper';

interface IConfirmModalProps {
  showNextStepModal: boolean;
  setShowNextStepModal: (show: boolean) => void;
  theme: string;
  control: Control<IFormData>;
  activePayment: boolean;
  proceedToNextStep: () => void;
  getValues: () => IFormData;
  handleAddNewOrder: (data: IFormData) => void;
}

const ConfirmModal = ({
  showNextStepModal,
  setShowNextStepModal,
  theme,
  control,
  activePayment,
  proceedToNextStep,
  getValues,
  handleAddNewOrder,
}: IConfirmModalProps) => {
  const { watch } = useFormContext();
  const { t } = useTranslation();
  return (
    <CustomModal
      size="xl"
      title={t('DECLARATION OF COMPLIANCE FOR SHIPPED GOODS')}
      show={showNextStepModal}
      onHide={() => setShowNextStepModal(false)}
    >
      <Box
        style={{
          width: '100%',
          paddingBottom: '20px',
          color: theme === 'dark' ? Colors.Gray3 : Colors.Gray7,
        }}
      >
        <Box>
          {t(
            'By using our platform and related services, the User hereby agrees to and affirms the following terms. This declaration shall be deemed a legally binding commitment between the User (Sender) and the Platform (Service Provider), acting as an intermediary.',
          )}
        </Box>
        <ol className="p-0 d-flex flex-column gap-2">
          <li style={{ listStyleType: 'none' }}>
            <div
              className="my-2"
              style={{ fontWeight: 'bold' }}
            >
              1.{' '}
              <span>
                {t(
                  'The User hereby agrees to and affirms the following terms.',
                )}
              </span>
            </div>
            <p>
              {t(
                'The Sender affirms that all goods submitted for shipment or trade via the platform are',
              )}
              <b>
                {' '}
                {t(
                  'in full compliance with the laws and regulations of the Republic of Korea,',
                )}
              </b>{' '}
              {t('including but not limited to:')}
            </p>

            <div className={`list-marker ${theme}`}>
              <span>
                <div className="marker"></div>
                {t(
                  'Prohibited substances, narcotics, weapons, explosives, and hazardous materials;',
                )}
              </span>
              <span>
                <div className="marker"></div>
                {t(
                  'Counterfeit goods, pirated items, or those infringing intellectual property rights;',
                )}
              </span>
              <span>
                <div className="marker"></div>
                {t(
                  'Wildlife and wildlife products subject to international or local trade restrictions;',
                )}
              </span>
              <span>
                <div className="marker"></div>
                {t('Forged currency, fraudulent documents, or contraband;')}
              </span>
              <span>
                <div className="marker"></div>
                {t(
                  'Goods restricted under Korean Customs Law, the Food Sanitation Act, the Foreign Trade Act, or other relevant legislation.',
                )}
              </span>
            </div>
          </li>
          <li style={{ listStyleType: 'none' }}>
            <div
              className="my-2"
              style={{ fontWeight: 'bold' }}
            >
              2. <span>{t('Full Legal Responsibility:')}</span>
            </div>
            <p>
              {t(
                'In the event that any goods are found to be in violation of applicable laws, the Sender shall bear sole and full legal responsibility, including potential administrative, civil, or criminal consequences. The platform shall not be held liable under any circumstances for the legality, content, or origin of the goods shipped by the User.',
              )}
            </p>
          </li>
          <li style={{ listStyleType: 'none' }}>
            <div
              className="mb-2"
              style={{ fontWeight: 'bold' }}
            >
              3. <span>{t('Right to Inspection and Refusal of Service:')}</span>
            </div>
            <p>
              {t(
                'The platform reserves the right to refuse shipment or suspend services related to any goods suspected of being illegal. In accordance with Korean law or at the request of competent authorities, goods may be subject to inspection without prior notice.',
              )}
            </p>
          </li>
          <li style={{ listStyleType: 'none' }}>
            <div
              className="mb-2"
              style={{ fontWeight: 'bold' }}
            >
              4. <span>{t('Liability for Damages:')}</span>
            </div>
            <p>
              {t(
                'Should any violation result in damage to the platform’s reputation, financial loss, or legal exposure (either directly or through affiliated third parties), the Sender agrees to indemnify and compensate the platform for all resulting damages and legal expenses.',
              )}
            </p>
          </li>
          <hr />
        </ol>
        <CustomCheckBox
          name="data.agree"
          control={control}
          subLabel={t(
            'I have read, understood, and agree to the Declaration of Compliance for Shipped Goods, and I accept full legal responsibility for all items I send, in accordance with the laws of the Republic of Korea.',
          )}
          position="end"
        />
      </Box>
      <div className="d-flex justify-content-center pb-3">
        <CustomBtn
          type="button"
          color="primary"
          size="lg"
          disabled={!watch('data.agree')}
          style={{ paddingLeft: '97px', paddingRight: '97px' }}
          onClick={() => {
            setShowNextStepModal(false);
            if (activePayment) {
              proceedToNextStep();
            } else {
              const formData = getValues();
              handleAddNewOrder(formData);
            }
          }}
          label={t('Yes')}
        />
      </div>
    </CustomModal>
  );
};

export default React.memo(ConfirmModal);
