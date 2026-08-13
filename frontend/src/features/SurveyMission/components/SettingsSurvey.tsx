import { DownOutlined } from '@ant-design/icons';
import { styled } from '@mui/material';
import { Collapse, ConfigProvider } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { FormBlock, useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import CustomCheckBox from '../../../components/Form/CustomCheckBox';
import CustomSlider from '../../../components/Form/CustomSlider';
import UnitInput from '../../../components/Form/UnitInput';

const EO_HORIZONTAL_OVERLAP = 1.187774883;
const EO_VERTICAL_OVERLAP = 0.891851587;
const IR_HORIZONTAL_OVERLAP = 1.374561917;
const IR_VERTICAL_OVERLAP = 1.063418863;

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
}>(({ mode, error }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',

  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
}));

const roundToTwoDecimals = (value: number): number => {
  return Math.round(value * 100) / 100;
};

export const SettingsSurvey = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [isExpanded, setIsExpanded] = useState(true);
  const { control, watch, setValue } = useFormContext();

  const hoverAndCapture = watch('settings.hover_and_capture');
  const captureAltitude = watch('settings.altitude');
  const overlap = watch('settings.overlap');

  const minCaptureAreaHorizontal = useMemo(() => {
    return Math.min(
      captureAltitude * EO_HORIZONTAL_OVERLAP,
      captureAltitude * IR_HORIZONTAL_OVERLAP,
    );
  }, [captureAltitude]);

  const minCaptureAreaVertical = useMemo(() => {
    return Math.min(
      captureAltitude * EO_VERTICAL_OVERLAP,
      captureAltitude * IR_VERTICAL_OVERLAP,
    );
  }, [captureAltitude]);

  const triggerDistance = useMemo(() => {
    return minCaptureAreaVertical * (1 - overlap / 100);
  }, [minCaptureAreaVertical, overlap]);

  const spacing = useMemo(() => {
    return minCaptureAreaHorizontal * (1 - overlap / 100);
  }, [minCaptureAreaHorizontal, overlap]);

  const roundedTriggerDistance = useMemo(
    () => roundToTwoDecimals(triggerDistance),
    [triggerDistance],
  );

  const roundedSpacing = useMemo(() => roundToTwoDecimals(spacing), [spacing]);

  const prevValuesRef = useRef<{
    triggerDistance: number | null;
    spacing: number | null;
  }>({ triggerDistance: null, spacing: null });

  useEffect(() => {
    if (
      captureAltitude &&
      overlap !== undefined &&
      overlap !== null &&
      !isNaN(roundedTriggerDistance) &&
      !isNaN(roundedSpacing)
    ) {
      if (prevValuesRef.current.triggerDistance !== roundedTriggerDistance) {
        setValue('settings.trigger_distance', roundedTriggerDistance);
        prevValuesRef.current.triggerDistance = roundedTriggerDistance;
      }

      if (prevValuesRef.current.spacing !== roundedSpacing) {
        setValue('settings.spacing', roundedSpacing);
        prevValuesRef.current.spacing = roundedSpacing;
      }
    }
  }, [
    captureAltitude,
    overlap,
    roundedTriggerDistance,
    roundedSpacing,
    setValue,
  ]);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const content = useMemo(
    () => (
      <div
        className="d-flex flex-column gap-3"
        style={{
          height: '30rem',
          overflow: 'auto',
        }}
      >
        <CustomCheckBox
          name="settings.hover_and_capture"
          control={control}
          subLabel={t('SurveyMission.Hover and Capture Image')}
        />
        <FormBlock
          style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
        >
          <StyledLabel mode={theme as 'light' | 'dark'}>
            {t('SurveyMission.Takeoff Settings')}
          </StyledLabel>
          <UnitInput
            name="settings.takeoff_altitude"
            label={t('SurveyMission.Takeoff Altitude')}
            placeholder={t('SurveyMission.Takeoff Altitude')}
            unit="m"
            isRequired
          />
          <UnitInput
            name="settings.altitude_separation"
            label={t('SurveyMission.Altitude Separation')}
            placeholder={t('SurveyMission.Altitude Separation')}
            unit="m"
            isRequired
          />
        </FormBlock>
        <FormBlock
          style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
        >
          <StyledLabel mode={theme as 'light' | 'dark'}>
            {t('SurveyMission.Camera Settings')}
          </StyledLabel>
          <UnitInput
            name="settings.altitude"
            label={t('SurveyMission.Capture Altitude')}
            placeholder={t('SurveyMission.Capture Altitude')}
            unit="m"
            isRequired
          />
          {hoverAndCapture && (
            <>
              <UnitInput
                name="settings.overlap"
                label={t('SurveyMission.Overlap')}
                placeholder={t('SurveyMission.Overlap')}
                unit="%"
                isRequired
              />
              <UnitInput
                name="settings.trigger_distance"
                label={t('SurveyMission.Trigger Distance')}
                placeholder={t('SurveyMission.Trigger Distance')}
                unit="m"
                isRequired
              />
              <UnitInput
                name="settings.spacing"
                label={t('SurveyMission.Spacing')}
                placeholder={t('SurveyMission.Spacing')}
                unit="m"
                isRequired
              />
              <CustomSlider
                name="settings.angle"
                label={t('SurveyMission.Angle')}
                control={control}
                min={0}
                max={360}
                step={1}
                unit=""
                required
              />
              <UnitInput
                name="settings.turnaround_distance"
                label={t('SurveyMission.Turnaround Distance')}
                placeholder={t('SurveyMission.Turnaround Distance')}
                unit="m"
                isRequired
              />
            </>
          )}
        </FormBlock>
      </div>
    ),
    [t, control, hoverAndCapture],
  );

  const items = useMemo(
    () => [
      {
        key: '1',
        label: (
          <span style={{ fontWeight: '600' }}>
            {t('SurveyMission.Settings')}
          </span>
        ),
        children: content,
      },
    ],
    [t, content],
  );

  const themeConfig = useMemo(
    () => ({
      components: {
        Collapse: {
          headerBg: theme === 'dark' ? '#2D2E30' : '#ECECEF',
        },
      },
      token: {
        colorText: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      },
    }),
    [theme],
  );

  const collapseStyle = useMemo(
    () => ({
      width: '18rem',
      padding: 'unset',
      maxWidth: '90vw',
      position: 'absolute' as const,
      bottom: 8,
      right: 8,
      opacity: 0.96,
      boxShadow:
        theme === 'dark'
          ? '0 4px 12px rgba(0, 0, 0, 0.8)'
          : '0 4px 12px rgba(0, 0, 0, 0.15)',
      borderRadius: '8px',
      zIndex: 500,
    }),
    [theme],
  );

  const expandIcon = useCallback(
    ({ isActive }: { isActive?: boolean }) => (
      <DownOutlined rotate={isActive ? 0 : -180} />
    ),
    [],
  );

  return (
    <ConfigProvider theme={themeConfig}>
      <Collapse
        style={collapseStyle}
        bordered={false}
        accordion
        expandIconPosition="end"
        expandIcon={expandIcon}
        onChange={handleToggleExpand}
        activeKey={isExpanded ? ['1'] : []}
        items={items}
      />
    </ConfigProvider>
  );
};
