import TimelineConnector from '@mui/lab/TimelineConnector';
import TimelineContent from '@mui/lab/TimelineContent';
import TimelineDot from '@mui/lab/TimelineDot';
import TimelineItem from '@mui/lab/TimelineItem';
import { styled } from '@mui/material';

import Colors from '@/configs/Colors';

export const CustomTimelineItem = styled(TimelineItem)(({ theme }) => ({
  height: '48px',
  '&:before': {
    flex: 0,
    padding: 0,
  },

  '&:last-child': {
    minHeight: '20px',
    height: '20px',
  },

  '&:last-of-type .MuiTimelineContent-root': {
    marginTop: '0px',
  },

  '&:last-of-type .MuiTimelineConnector-root': {
    display: 'none',
  },
}));

export const CustomTimelineContent = styled(TimelineContent)(({ theme }) => ({
  zIndex: -1,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  gap: '2px',
  marginTop: '-50px',
  minHeight: '0px',
}));

export const CustomTimelineDot = styled(TimelineDot)(({ theme }) => ({
  padding: '2.5px',
  margin: '4px 0',
  backgroundColor:
    theme.palette.mode === 'dark' ? Colors.PrimaryDark : Colors.Primary,
}));

export const CustomTimelineConnector = styled(TimelineConnector)(
  ({ theme }) => ({
    flexGrow: 1,
    width: '1px',
    borderRadius: '50px',
    backgroundColor: Colors.Gray5,
  }),
);
