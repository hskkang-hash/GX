import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useTheme } from 'rj-core';
import Colors, { textLabel } from '@/configs/Colors';
import { DailyProfileOverview as DailyProfileOverviewType } from '../hooks/useSurveillanceDashboard';
import { Box, IconButton, Tooltip as MuiTooltip } from '@mui/material';
import { LiaLongArrowAltRightSolid } from 'react-icons/lia';
import { CustomRoutes } from '@/services/API';
import PathProfileIcon from '@/assets/images/dashboard/path_profile.svg';
import DailyProfileOverviewSkeleton from './DailyProfileOverviewSkeleton';
import { useConvertDate } from '../../utils/formatDateTime';
import CustomDatePicker from '@/components/Form/CustomDatePicker';

interface DailyProfileOverviewProps {
  data: DailyProfileOverviewType | null;
  isLoading?: boolean;
  onDateChange?: (date: string) => void;
}

const DailyProfileOverview: React.FC<DailyProfileOverviewProps> = ({
  data,
  isLoading = false,
  onDateChange,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const navigate = useNavigate();
  const { dateFormat } = useConvertDate();

  const handleDateChange = (date: string | null) => {
    if (date && onDateChange) {
      onDateChange(date);
    }
  };

  if (isLoading || !data) {
    return (
      <DailyProfileOverviewSkeleton />
    );
  }


  const stats = [
    {
      label: t('Total'),
      value: data.total,
      darkColor: '#293438',
      lightColor: '#ECF8FF',
      mainColor: '#2EB4FFE5',
    },
    {
      label: "image",
      value: PathProfileIcon,
      darkColor: '#2D2E30',
      lightColor: '#F6F7F8',
    },
    {
      label: t('Completed'),
      value: data.completed,
      darkColor: '#3F5848',
      lightColor: '#E4FAEC',
      mainColor: '#0CBA47',
    },
    {
      label: t('Processing'),
      value: data.processing,
      darkColor: '#513D2B',
      lightColor: '#FBEBDD',
      mainColor: '#EB7509',
    },
  ];

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      {/* HEADER */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          flexShrink: 0,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: '1.25rem',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            flex: 1,
            minWidth: '12.5rem',
          }}
        >
          {t('SurveillanceDashboard.Daily Profile Overview')}
        </h3>

        <MuiTooltip
          title={t('SurveillanceDashboard.Go to Profile')}
          arrow
          placement="top"
        >
          <IconButton
            sx={{
              color: textLabel[theme === 'dark' ? 'dark' : 'light'],
              padding: 0,
              minWidth: 0,
              width: 'auto',
              '&:hover': {
                color:
                  theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)',
                transform: 'scale(1.2)',
                transition: 'all 0.4s ease-in-out',
                background: 'transparent',
              },
              '&:active': {
                background: 'transparent',
              },
            }}
            onClick={() => {
              navigate(CustomRoutes.surveyProfile.path);
            }}
          >
            <LiaLongArrowAltRightSolid
              style={{
                fontSize: '1.875rem',
              }}
            />
          </IconButton>
        </MuiTooltip>
      </div >

      <CustomDatePicker
        value={dayjs(data.date)}
        onChange={(date) => handleDateChange(date)}
        format={dateFormat}
      />

      {/* STATS */}
      < div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '1rem',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {
          stats.map((stat) => (
            <Box key={stat.label} >
              {stat.label === "image" ?
                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%',
                  width: '100%',
                }}>
                  <Box sx={{
                    height: '80px',
                    width: '80px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    borderRadius: '50%',
                    background:
                      theme === 'dark'
                        ? stat.darkColor
                        : stat.lightColor,
                  }}>
                    <img src={stat.value} alt={stat.label} />
                  </Box>
                </Box>
                :
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'start',
                  height: '100%',
                  width: '100%',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  borderRadius: '1rem',
                  background:
                    theme === 'dark'
                      ? stat.darkColor
                      : stat.lightColor,
                }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: '600', color: theme === 'dark' ? Colors.White : Colors.Black }}>
                    {stat.label}
                  </span>
                  <span style={{ fontSize: '2rem', fontWeight: '700', color: stat.mainColor }}>
                    {stat.value}
                  </span>
                </Box>
              }
            </Box>
          ))
        }
      </div >
    </div >
  );
};

export default DailyProfileOverview;

