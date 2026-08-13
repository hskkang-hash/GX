import { yupResolver } from '@hookform/resolvers/yup';
import {
  StepConnector,
  stepConnectorClasses,
  StepIconProps,
  styled,
} from '@mui/material';
import Box from '@mui/material/Box';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Stepper from '@mui/material/Stepper';
import * as React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ToastTopHelper,
  ROLE_PERMISSION,
  useTheme,
  useActivePayment,
  ActionBtn,
} from 'rj-core';

import CustomCheckBox from '@/components/Form/CustomCheckBox';
import Colors from '@/configs/Colors';
import ConfirmModal from '@/features/delivery/deliveryInquiry/AddNewOrder/formsOrder/ConfirmModal';
import {
  DEFAULT_FORM_VALUES,
  IFormData,
} from '@/features/delivery/deliveryInquiry/AddNewOrder/formsOrder/Helper';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import {
  addNewOrderSchemaStep0,
  addNewOrderSchemaStep1,
  addNewOrderSchemaStep2,
} from '@/services/schemaForm';
import { convertOrderDataToForm } from '@/utils/addNewOrderDataConvert';

import useAPI from '../hooks/useAPI';
import './AddNewOrder.scss';
import FinishOrder from './formsOrder/FinishOrder';
import PackageInfomation from './formsOrder/PackageInfomation';
import PaymentOrder from './formsOrder/PaymentOrder';
import ShippingInfomation from './formsOrder/ShippingInfomation';

export default function FormAddNewOrder() {
  const { id } = useParams();
  const [theme, _] = useTheme();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { getDetailOrder, createNewOrder } = useAPI();
  const [detailOrder, setDetailOrder] = useState<any>(null);
  const [showNextStepModal, setShowNextStepModal] = useState(false);
  const [orderAfterSubmit, setOrderAfterSubmit] = useState<any>(null);
  const [activeStep, setActiveStep] = React.useState(0);
  const [skipped, setSkipped] = React.useState(new Set<number>());
  const [isCurrentStepValid, setIsCurrentStepValid] = useState(false);
  const [clickSave, setClickSave] = useState(false);
  const activePayment = useActivePayment();

  const formSteps = [
    <ShippingInfomation />,
    <PackageInfomation />,
    ...(activePayment ? [<PaymentOrder />] : []),
    <FinishOrder />,
  ];

  const initialData = detailOrder ? convertOrderDataToForm(detailOrder) : null;

  const methods = useForm<IFormData>({
    defaultValues: initialData ? initialData : DEFAULT_FORM_VALUES,
    resolver: yupResolver(
      (activeStep === 0
        ? addNewOrderSchemaStep0(t)
        : activeStep === 1
          ? addNewOrderSchemaStep1(t)
          : activeStep === 2 && activePayment
            ? addNewOrderSchemaStep2(t)
            : addNewOrderSchemaStep0(t)) as any,
    ) as any,
    mode: 'all',
  });

  const {
    handleSubmit,
    setValue,
    reset,
    control,
    getValues,
    watch,
    clearErrors,
    formState: { isDirty, errors },
  } = methods;

  const watchedValues = watch();
  const agreePolicy = watch('data.agree');
  console.log('form_inquiry_errors', errors);
  console.log('form_inquiry_watch', watch());

  useEffect(() => {
    if (id) {
      (async () => {
        const { success, message, data } = await getDetailOrder(Number(id));
        if (success) {
          setDetailOrder(data);
        }
        if (!success) {
          ToastTopHelper.error(message);
        }
      })();
    }
  }, [id]);


  //validate field follow step by manual check to active next button
  const validateCurrentStep = useCallback(() => {
    const currentData = getValues();
    switch (activeStep) {
      case 0:
        return validateShippingStep(currentData);
      case 1:
        return validatePackageStep(currentData);
      case 2:
        if (activePayment) {
          return validatePaymentStep(currentData);
        }
        return false;
      default:
        return false;
    }
  }, [activeStep, watchedValues]);

  //validate field shema yup follow step
  const validateStepFields = async (stepIndex: number): Promise<boolean> => {
    let schema;
    switch (stepIndex) {
      case 0:
        schema = addNewOrderSchemaStep0(t);
        break;
      case 1:
        schema = addNewOrderSchemaStep1(t);
        break;
      case 2:
        if (activePayment) {
          schema = addNewOrderSchemaStep2(t);
        } else {
          return true;
        }
        break;
      default:
        return true;
    }

    try {
      const currentData = getValues();

      await schema.validate(currentData, { abortEarly: false });
      return true;
    } catch (error) {
      return false;
    }
  };

  // Function to find first step with errors
  const findFirstStepWithErrors = async (): Promise<number> => {
    // Check step 0 (Shipping) first
    const step0Valid = await validateStepFields(0);
    if (!step0Valid) {
      return 0;
    }

    // Check step 1 (Package)
    const step1Valid = await validateStepFields(1);
    if (!step1Valid) {
      return 1;
    }

    // Check step 2 (Payment) if activePayment is true
    if (activePayment) {
      const step2Valid = await validateStepFields(2);
      if (!step2Valid) {
        return 2;
      }
    }

    return -1;
  };

  // Function to validate steps sequentially
  const validateStepsSequentially = async (): Promise<{
    isValid: boolean;
    firstInvalidStep: number;
  }> => {
    // Step 1: Validate Shipping step 0
    const step0Valid = await validateStepFields(0);
    if (!step0Valid) {
      return { isValid: false, firstInvalidStep: 0 };
    }

    // Step 2: Validate Package step 1
    const step1Valid = await validateStepFields(1);
    if (!step1Valid) {
      return { isValid: false, firstInvalidStep: 1 };
    }

    // Step 3: Validate Payment step 2 if activePayment is true
    if (activePayment) {
      const step2Valid = await validateStepFields(2);
      if (!step2Valid) {
        return { isValid: false, firstInvalidStep: 2 };
      }
    }

    // All steps are valid
    return { isValid: true, firstInvalidStep: -1 };
  };

  // Validate Step 0
  const validateShippingStep = (data: any) => {
    const sender = data.data?.sender;
    const recipient = data.data?.recipient;
    const deliveryOption = data.data?.delivery_option;
    const deliveryLocationId = data.data?.delivery_location_id;
    const fullAddress = data.data?.recipient?.full_address;
    console.log('fullAddress', fullAddress);

    if (!sender?.name?.trim() || !sender?.phone_number?.trim()) {
      return false;
    }
    if (!sender?.location_id?.value) {
      return false;
    }
    if (!recipient?.name?.trim() || !recipient?.phone_number?.trim()) {
      return false;
    }
    if (!recipient?.full_address) {
      return false;
    }
    if (
      deliveryOption === 'collect_at_location' &&
      !deliveryLocationId?.value
    ) {
      return false;
    }
    return true;
  };

  // Validate Step 1
  const validatePackageStep = (data: any) => {
    const packages = data.data?.package;
    if (!packages || packages.length === 0) {
      return false;
    }
    for (const pkg of packages) {
      if (
        pkg?.package_weight?.value === null ||
        pkg?.package_weight?.value === undefined ||
        pkg.package_weight.value < 0
      ) {
        return false;
      }
      const dimensions = pkg?.dimensions;
      if (
        !dimensions?.length?.value ||
        dimensions.length.value <= 0 ||
        !dimensions?.width?.value ||
        dimensions.width.value <= 0 ||
        !dimensions?.height?.value ||
        dimensions.height.value <= 0
      ) {
        return false;
      }
      if (!pkg?.item_type?.value) {
        return false;
      }
      if (!pkg?.packaging?.value) {
        return false;
      }
    }
    return true;
  };

  // Validate Step 2
  const validatePaymentStep = (data: any) => {
    const payment = data.data?.payment;
    const agree = data.data?.agree;
    if (!payment) {
      return false;
    }
    if (!agree) {
      return false;
    }
    return true;
  };

  const handleAddNewOrder = useCallback(
    async (orderData: any) => {
      const validationResult = await validateStepsSequentially();
      if (!validationResult.isValid) {
        setActiveStep(0);
        return;
      }

      const { success, message, data } = await createNewOrder(orderData);
      setClickSave(true);
      if (success) {
        setOrderAfterSubmit(data);
        setValue('data.orderAfterSubmit', data);
        ToastTopHelper.success(message);
        if (activePayment) {
          proceedToNextStep();
        } else {
          setActiveStep(activePayment ? 3 : 2);
        }
      } else {
        ToastTopHelper.error(message);
      }
    },
    [activePayment, createNewOrder],
  ); // eslint-disable-line react-hooks/exhaustive-deps

  const onError = async (errors: Record<string, any>) => {
    console.log('onError', errors);
    const firstStepWithErrors = await findFirstStepWithErrors();
    if (firstStepWithErrors == 0) {
      setActiveStep(firstStepWithErrors);
    } else if (firstStepWithErrors == 1) {
      setActiveStep(1);
    }
  };

  const isStepSkipped = (step: number) => {
    return skipped.has(step);
  };

  const handleNext = async () => {
    const currentStepValid = await validateStepFields(activeStep);
    if (!currentStepValid) {
      return;
    }

    if (activeStep === 1) {
      setShowNextStepModal(true);
    } else {
      proceedToNextStep();
    }
  };

  const proceedToNextStep = useCallback(() => {
    if (activeStep >= (activePayment ? 3 : 2)) return;
    let newSkipped = skipped;
    if (isStepSkipped(activeStep)) {
      newSkipped = new Set(newSkipped.values());
      newSkipped.delete(activeStep);
    }
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    setSkipped(newSkipped);
  }, [activeStep, activePayment, skipped, isStepSkipped]);

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const CustomStepIcon = (props: StepIconProps) => {
    const { active, completed, icon } = props;
    return (
      <div
        style={{
          backgroundColor: active
            ? theme === 'dark'
              ? Colors.PrimaryDark
              : Colors.Primary
            : completed
              ? 'transparent'
              : 'transparent',
          border: `1px solid ${active || completed
            ? theme === 'dark'
              ? Colors.PrimaryDark
              : Colors.Primary
            : theme === 'dark'
              ? '#444646'
              : '#DDDFE2'
            }`,
          color: active
            ? '#fff'
            : completed
              ? theme === 'dark'
                ? Colors.PrimaryDark
                : Colors.Primary
              : '#9C9D9D',
          width: 24,
          height: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '50%',
          fontWeight: active || completed ? '600' : '400',
        }}
      >
        {icon}
      </div>
    );
  };

  // Custom Connector
  const CustomConnector = styled(StepConnector)(({ }) => ({
    [`&.${stepConnectorClasses.alternativeLabel}`]: {
      top: 12,
    },
    [`& .${stepConnectorClasses.line}`]: {
      height: 1,
      border: 0,
      backgroundColor: theme === 'dark' ? '#444646' : '#DDDFE2',
      borderRadius: 1,
    },
    [`&.${stepConnectorClasses.active} .${stepConnectorClasses.line}`]: {
      backgroundColor: Colors.Primary,
    },
    [`&.${stepConnectorClasses.completed} .${stepConnectorClasses.line}`]: {
      backgroundColor: Colors.Primary,
    },
  }));

  const steps = [
    'Shipping Information',
    'Package Information',
    ...(activePayment ? ['Payment'] : []),
    'Finish',
  ];

  useEffect(() => {
    const isValid = validateCurrentStep();
    setIsCurrentStepValid(isValid);
  }, [validateCurrentStep, watchedValues]);

  useEffect(() => {
    if (activeStep === 1 && agreePolicy === true) {
      setValue('data.agree', false);
      methods.trigger('data.agree');
    }
  }, [activeStep]);

  useEffect(() => {
    if (detailOrder && initialData) {
      reset(initialData);
    }
  }, [detailOrder, reset]);

  const { showModal, setShowModal, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => { },
      onError,
      onCancel: async () => {
        const validationResult = await validateStepsSequentially();
        if (!validationResult?.isValid) {
          setActiveStep(validationResult.firstInvalidStep);
          setShowModal(false);
        } else {
          navigate(CustomRoutes.deliveryInquiry.path);
        }
      },
      handleSubmit,
    });

  // Custom handler for modal save that doesn't proceed with navigation
  const handleModalSave = async () => {
    try {
      const firstStepWithErrors = await findFirstStepWithErrors();

      if (firstStepWithErrors !== -1) {
        setActiveStep(firstStepWithErrors);
        setShowModal(false);
        methods.trigger();
        return;
      }

      setActiveStep(1);
      setShowModal(false);
      reset(getValues(), {
        keepDirty: true,
        keepValues: true,
      });
    } catch (error) {
      console.error('Error in handleModalSave:', error);
    }
  };

  useEffect(() => {
    if (watch('data.delivery_option') === 'delivery_to_door') {
      clearErrors('data.delivery_location_id');
    }
  }, [watch('data.delivery_option'), clearErrors]);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleAddNewOrder, onError)}
        className={`form-add-new-packaging ${theme}`}
      >
        <CustomBreadcrumb
          items={[
            {
              url: CustomRoutes.deliveryInquiry.path,
              // text: t('Delivery Inquiry'),
            },
            { text: t('Add New Order') },
          ]}
          buttons={[
            activeStep >= (activePayment ? 3 : 2) ? (
              <div style={{ height: '31px' }}></div>
            ) : (
              <React.Fragment key="step">
                {activeStep == 0 && (
                  <CustomBtn
                    label={t('Cancel')}
                    variant="outline"
                    color="secondary"
                    size="md"
                    style={{ width: '6rem' }}
                    type="button"
                    onClick={() => navigate(CustomRoutes.deliveryInquiry.path)}
                  />
                )}
                {activeStep > 0 && (
                  <CustomBtn
                    label={t('Back')}
                    variant="outline"
                    color="primary"
                    size="md"
                    style={{ width: '6rem' }}
                    type="button"
                    onClick={handleBack}
                  />
                )}
                <CustomBtn
                  label={
                    activeStep == (activePayment ? 2 : 1)
                      ? t('Confirm')
                      : t('Next')
                  }
                  variant="contained"
                  color="primary"
                  size="md"
                  style={{ width: '6rem' }}
                  type={activeStep == 2 && activePayment ? 'submit' : 'button'}
                  onClick={
                    activeStep == 2 && activePayment
                      ? handleSubmit(handleAddNewOrder, onError)
                      : handleNext
                  }
                  disabled={!isCurrentStepValid}
                  actionType={ROLE_PERMISSION.CREATE}
                />
              </React.Fragment>
            ),
          ]}
        />
        <Main>
          <Box sx={{ width: '100%', marginBottom: '16px' }}>
            <Stepper
              activeStep={activeStep}
              alternativeLabel
              connector={<CustomConnector />}
            >
              {steps.map((label, index) => {
                const isActive = activeStep === index;
                const isCompleted = index < activeStep;
                const color =
                  theme === 'dark' ? Colors.PrimaryDark : Colors.Primary;
                return (
                  <Step key={label}>
                    <StepLabel
                      StepIconComponent={CustomStepIcon}
                      sx={{
                        '& .MuiStepLabel-label': {
                          marginTop: '0px',
                          fontSize: '14px',
                          mt: '6px',
                          fontWeight: isActive ? '600' : '400',
                          color: isActive || isCompleted ? color : '#9C9D9D',
                        },
                        '& .MuiStepLabel-label.Mui-active': {
                          color: isActive || isCompleted ? color : '#9C9D9D',
                        },
                        '& .MuiStepLabel-label.MuiStepLabel-alternativeLabel ':
                        {
                          marginTop: '6px',
                        },
                      }}
                    >
                      {t(label)}
                    </StepLabel>
                  </Step>
                );
              })}
            </Stepper>
          </Box>
          {formSteps[activeStep]}
          <ConfirmModal
            showNextStepModal={showNextStepModal}
            setShowNextStepModal={setShowNextStepModal}
            theme={theme}
            control={control}
            activePayment={activePayment}
            proceedToNextStep={proceedToNextStep}
            getValues={getValues}
            handleAddNewOrder={handleAddNewOrder}
          />
          <CustomModal
            title={t('Save changes')}
            show={showModal}
            onHide={() => setShowModal(false)}
          >
            <div style={{ width: '25rem' }}>
              {t(
                'Your unsaved changes will be lost. Do you want to save changes before leaving?',
              )}
            </div>
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  key="modal-save-btn"
                  type="submit"
                  color="primary"
                  size="lg"
                  actionType={ROLE_PERMISSION.UPDATE}
                  onClick={handleModalSave}
                  label={t('Save')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  key="modal-cancel-btn"
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="lg"
                  onClick={handleModalCancel}
                  label={t('Cancel')}
                />,
              ]}
            />
          </CustomModal>
        </Main>
      </form>
    </FormProvider>
  );
}
