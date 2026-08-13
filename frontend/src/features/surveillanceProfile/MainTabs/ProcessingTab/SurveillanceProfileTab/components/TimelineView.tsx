import { Box, FormControlLabel, Radio, RadioGroup } from '@mui/material';
import { t } from 'i18next';
import React, {
  useMemo,
  useRef,
  useEffect,
  useState,
  useCallback,
} from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { ToastTopHelper, useTheme, useUserInfo } from 'rj-core';

import CustomDatePicker from '@/components/Form/CustomDatePicker';
import PaginationMultiSelect from '@/components/selects/CustomPaginationSelect';
import Colors from '@/configs/Colors';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';

import {
  parseTimeFromDateTime,
  darkenColor,
  blendWithBackground,
  timeToMinutes,
  getEventPosition,
} from '../utils/TimelineViewHelper';
import {
  EventsTimelineData,
  TimelineViewProps,
  TimelineEvent,
} from './TimelineView.d';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { useConfigSystem } from 'rj-core';
dayjs.extend(utc);
const TimelineView: React.FC<TimelineViewProps> = ({
  viewType,
  onViewTypeChange,
  onSelectedItemsChange,
  selectedDate,
  onDateChange,
  onEventClick,
}) => {
  console.log("selectedDate", selectedDate)
  const [theme] = useTheme();
  const { i18n } = useTranslation();
  const [configSystem] = useConfigSystem();
  const timelineGridRef = useRef<HTMLDivElement>(null);
  const [eventsTimeline, setEventsTimeline] =
    useState<EventsTimelineData | null>(null);
  const { getSurveillanceProfileOptionsAPI, getEventsSurveillanceProfileAPI } =
    useSurveillanceProfile();
  const { convertDateFormatToUTC, dateFormat, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay, timeZoneFormat } = useConvertDate();

  // Transform API data to TimelineEvent format
  const transformEvents = useMemo(() => {
    if (!eventsTimeline || typeof eventsTimeline !== 'object') {
      return [];
    }
    const timelineData = eventsTimeline as EventsTimelineData;
    const transformed: TimelineEvent[] = [];
    if (viewType === 'profile' && timelineData.by_profile) {
      timelineData.by_profile.forEach((profile) => {
        transformed.push({
          id: profile.profile_id,
          startTime: dayjs(profile.start_time).tz(timeZoneFormat).format("HH:mm"),
          endTime: dayjs(profile.end_time).tz(timeZoneFormat).format("HH:mm"),
          profileName: profile.profile_name,
          color: profile.color_code,
          darkColor: darkenColor(profile.color_code),
          status_code: profile.status_code,
        });
      });
    } else if (viewType === 'drone' && timelineData.by_drone) {
      timelineData.by_drone.forEach((drone) => {
        drone.profiles.forEach((profile) => {
          transformed.push({
            id: profile.profile_id,
            startTime: dayjs(profile.start_time).tz(timeZoneFormat).format("HH:mm"),
            endTime: dayjs(profile.end_time).tz(timeZoneFormat).format("HH:mm"),
            profileName: profile.profile_name,
            color: profile.color_code,
            darkColor: darkenColor(profile.color_code),
            itemId: drone.drone_serial,
            status_code: profile.status_code,
          });
        });
      });
    }

    return transformed;
  }, [eventsTimeline, viewType]);

  // Get unique items from events for left sidebar
  const timelineItems = useMemo(() => {
    if (viewType === 'drone') {
      const uniqueItems = new Map<string, string>();
      transformEvents.forEach((event) => {
        if (event.itemId) {
          uniqueItems.set(event.itemId, event.itemId);
        }
      });
      return Array.from(uniqueItems.keys());
    } else {
      const uniqueItems = new Map<string, string>();
      transformEvents.forEach((event) => {
        uniqueItems.set(event.profileName, event.profileName);
      });
      return Array.from(uniqueItems.keys());
    }
  }, [transformEvents, viewType]);


  const timeSlots = useMemo(() => {
    const slots = [];
    for (let i = 0; i < 24; i++) {
      slots.push(i);
    }
    return slots;
  }, []);

  // Calculate position and width for event bars (using fixed 300px per hour)
  const HOUR_WIDTH = 120; // Each hour is 150px wide
  const TOTAL_TIMELINE_WIDTH = 24 * HOUR_WIDTH; // 7200px for 24 hours

  // Helper function to check if two events overlap
  const eventsOverlap = (
    event1: TimelineEvent,
    event2: TimelineEvent,
  ): boolean => {
    const start1 = timeToMinutes(event1.startTime);
    const end1 = timeToMinutes(event1.endTime);
    const start2 = timeToMinutes(event2.startTime);
    const end2 = timeToMinutes(event2.endTime);

    // Events overlap if one starts before the other ends
    return start1 < end2 && start2 < end1;
  };

  // Helper function to assign lanes to overlapping events
  const assignLanesToEvents = (events: TimelineEvent[]): TimelineEvent[] => {
    const eventsWithLanes: TimelineEvent[] = [];
    const lanes: TimelineEvent[][] = []; // Each lane contains events that don't overlap

    events.forEach((event) => {
      // Find the first lane where this event doesn't overlap with any existing event
      let assignedLane = -1;
      for (let laneIndex = 0; laneIndex < lanes.length; laneIndex++) {
        const laneEvents = lanes[laneIndex];
        // Check if event overlaps with any event in this lane
        const hasOverlap = laneEvents.some((laneEvent) =>
          eventsOverlap(event, laneEvent),
        );
        if (!hasOverlap) {
          assignedLane = laneIndex;
          break;
        }
      }

      // If no suitable lane found, create a new one
      if (assignedLane === -1) {
        assignedLane = lanes.length;
        lanes.push([]);
      }

      // Assign lane to event and add to lane
      const eventWithLane = { ...event, lane: assignedLane };
      eventsWithLanes.push(eventWithLane);
      lanes[assignedLane].push(eventWithLane);
    });

    return eventsWithLanes;
  };

  // Helper function to calculate and sort itemEvents for a specific item
  const getItemEvents = useCallback(
    (item: string, events: TimelineEvent[]): TimelineEvent[] => {
      // Filter events for this item
      const filtered = events.filter((event) =>
        viewType === 'drone'
          ? event.itemId === item
          : event.profileName === item,
      );

      // Sort by start time
      const sorted = [...filtered].sort((a, b) => {
        const aMinutes = timeToMinutes(a.startTime);
        const bMinutes = timeToMinutes(b.startTime);
        // If start times are equal, sort by end time
        if (aMinutes === bMinutes) {
          return timeToMinutes(a.endTime) - timeToMinutes(b.endTime);
        }
        return aMinutes - bMinutes;
      });

      // Validate and filter out invalid events
      const validEvents = sorted.filter((event) => {
        const startMinutes = timeToMinutes(event.startTime);
        const endMinutes = timeToMinutes(event.endTime);

        // Event must have valid times
        if (isNaN(startMinutes) || isNaN(endMinutes)) {
          return false;
        }

        // Event should be within 24 hours
        if (startMinutes < 0 || startMinutes >= 1440) {
          return false;
        }

        // End time should be after start time
        if (endMinutes <= startMinutes) {
          return false;
        }

        return true;
      });

      // Assign lanes to overlapping events
      const eventsWithLanes = assignLanesToEvents(validEvents);

      return eventsWithLanes;
    },
    [viewType],
  );

  const [selectedProfiles, setSelectedProfiles] =
    useState<Array<{ label: string; value: string | number }>>([]);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);

  // Calculate total content height for grid lines
  const totalContentHeight = useMemo(() => {
    if (timelineItems.length === 0) return 300; // minimum height

    let totalHeight = 0;
    timelineItems.forEach((item) => {
      const itemEvents = transformEvents.filter((event) =>
        viewType === 'drone'
          ? event.itemId === item
          : event.profileName === item,
      );

      // Assign lanes to calculate max lane
      const lanes: typeof itemEvents[] = [];
      itemEvents.forEach((event) => {
        let assignedLane = -1;
        for (let laneIndex = 0; laneIndex < lanes.length; laneIndex++) {
          const hasOverlap = lanes[laneIndex].some((laneEvent) => {
            const start1 = timeToMinutes(event.startTime);
            const end1 = timeToMinutes(event.endTime);
            const start2 = timeToMinutes(laneEvent.startTime);
            const end2 = timeToMinutes(laneEvent.endTime);
            return start1 < end2 && start2 < end1;
          });
          if (!hasOverlap) {
            assignedLane = laneIndex;
            break;
          }
        }
        if (assignedLane === -1) {
          assignedLane = lanes.length;
          lanes.push([]);
        }
        lanes[assignedLane].push(event);
      });

      const maxLane = lanes.length > 0 ? lanes.length - 1 : 0;
      const eventHeight = 44;
      const eventGap = 4;
      const baseTop = viewType === 'drone' ? 20 : 8;
      const rowHeight = Math.max(60, baseTop + (maxLane + 1) * (eventHeight + eventGap) - eventGap + 8);
      totalHeight += rowHeight;
    });

    return Math.max(totalHeight, 300); // minimum 300px
  }, [timelineItems, transformEvents, viewType]);

  // Load profile options when selectedDate changes
  useEffect(() => {
    if (!selectedDate) return;

    const loadProfileOptions = async () => {
      setSelectedProfiles([]);
      setEventsTimeline({ by_profile: [], by_drone: [] });
      setIsLoadingProfiles(true);

      try {
        const response = await getSurveillanceProfileOptionsAPI()(
          {
            start_time: dayjs(selectedDate).tz(timeZoneFormat).startOf('day').utc().format('YYYY-MM-DDTHH:mm:ss+00:00'),
            end_time: dayjs(selectedDate).tz(timeZoneFormat).endOf('day').utc().format('YYYY-MM-DDTHH:mm:ss+00:00')
          }, '', [], {
          page: 1,
        });

        if (response.options && response.options.length > 0) {
          setSelectedProfiles(response.options);
        }
      } finally {
        setIsLoadingProfiles(false);
      }
    };
    if (configSystem !== undefined) {
      loadProfileOptions();
    }
  }, [selectedDate]);

  // Fetch events when selectedProfiles changes (not when selectedDate changes)
  useEffect(() => {
    if (isLoadingProfiles) return; // Skip while loading profile options
    if (!selectedProfiles || selectedProfiles.length === 0 || !selectedDate) {
      setEventsTimeline({ by_profile: [], by_drone: [] });
      return;
    }

    const selectedProfilesIds = selectedProfiles
      .map((item: { value: string | number }) => item.value)
      .join(',');

    const fetchEvents = async () => {
      const { data, message, success } =
        await getEventsSurveillanceProfileAPI(
          selectedProfilesIds,
          dayjs(selectedDate).tz(timeZoneFormat).startOf('day').utc().format('YYYY-MM-DDTHH:mm:ss+00:00'),
        );

      if (success) {
        setEventsTimeline(data.timeline || { by_profile: [], by_drone: [] });
      } else {
        ToastTopHelper.error(message);
        setEventsTimeline({ by_profile: [], by_drone: [] });
      }
    };

    fetchEvents();
  }, [selectedProfiles, isLoadingProfiles]);



  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '39rem',
        backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
      }}
    >
      {/* Header Controls */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          padding: '0.5rem 0.75rem',
          margin: '1rem',
          borderRadius: '8px',
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
        }}
      >
        {/* View Type Radio Buttons */}
        <RadioGroup
          row
          value={viewType}
          onChange={(e) =>
            onViewTypeChange(e.target.value as 'profile' | 'drone')
          }
        >
          <FormControlLabel
            value="profile"
            control={
              <Radio
                sx={{
                  color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
                  '&.Mui-checked': {
                    color: 'var(--ga-primary)',
                  },
                }}
              />
            }
            label={t('By Profile')}
          />
          <FormControlLabel
            value="drone"
            control={
              <Radio
                sx={{
                  color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
                  '&.Mui-checked': {
                    color: 'var(--ga-primary)',
                  },
                }}
              />
            }
            label={t('By Drone')}
          />
        </RadioGroup>
        <Box sx={{ minWidth: '15rem' }}>
          <PaginationMultiSelect
            key={dayjs(selectedDate).format("YYYY-MM-DD")}
            defaultValue={selectedProfiles as any}
            loadOptions={((search: string, loadedOptions: any, additional: { page: number; page_size?: number }) =>
              getSurveillanceProfileOptionsAPI()(
                {
                  start_time: dayjs(selectedDate).tz(timeZoneFormat).startOf('day').utc().format('YYYY-MM-DDTHH:mm:ss+00:00'),
                  end_time: dayjs(selectedDate).tz(timeZoneFormat).endOf('day').utc().format('YYYY-MM-DDTHH:mm:ss+00:00')
                  // start_time: convertDateToUTCStartOfDay(selectedDate as string),
                  // end_time: convertDateToUTCEndOfDay(selectedDate as string)
                },
                search,
                loadedOptions,
                additional ?? { page: 1 }
              )
            ) as any}
            onChange={(value: any) => {
              setSelectedProfiles(value);
            }}
          />
        </Box>
        <CustomDatePicker
          value={selectedDate}
          onChange={onDateChange}
          format={dateFormat}
          placeholder={t('Select Date')}
        />
      </Box>

      {/* Timeline Content */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          overflowX: 'auto',
          overflowY: 'auto',
          position: 'relative',
          padding: '0 2rem',
        }}
      >
        {/* Fixed background for drone column - extends full visible height */}
        {viewType === 'drone' && (
          <Box
            sx={{
              position: 'absolute',
              left: '2rem',
              top: 0,
              bottom: "10px",
              width: '200px',
              backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
              borderRight: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
              zIndex: 1,
              pointerEvents: 'none',
            }}
          />
        )}
        {/* Timeline Grid */}
        <Box
          ref={timelineGridRef}
          sx={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'auto',
            position: 'relative',
            backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            '&::-webkit-scrollbar': {
              height: '0.5rem',
              cursor: 'pointer',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: theme === 'dark' ? '#4A4A4A' : '#C4C4C4',
              borderRadius: '4px',
              '&:hover': {
                backgroundColor: theme === 'dark' ? '#5A5A5A' : '#A0A0A0',
              },
            },
          }}
        >
          {/* Time Header */}
          <Box
            sx={{
              display: 'flex',
              position: 'sticky',
              top: 0,
              zIndex: 10,
              backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
              width:
                viewType === 'drone'
                  ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                  : `${TOTAL_TIMELINE_WIDTH}px`,
              minWidth:
                viewType === 'drone'
                  ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                  : `${TOTAL_TIMELINE_WIDTH}px`,
            }}
          >
            {/* Empty space for drone ID column (only in drone view) */}
            {viewType === 'drone' && (
              <Box
                sx={{
                  width: '200px',
                  minWidth: '200px',
                  flexShrink: 0,
                  // borderRight: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
                  padding: '0.5rem',
                  textAlign: 'center',
                  color: theme === 'dark' ? '#DDDFE2' : '#2D2E30',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  position: 'sticky',
                  left: 0,
                  zIndex: 12,
                  backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
                }}
              >
                {/* Drone */}
              </Box>
            )}
            {/* Time slots */}
            <Box
              sx={{
                display: 'flex',
                position: 'relative',
                width: `${TOTAL_TIMELINE_WIDTH}px`,
                minWidth: `${TOTAL_TIMELINE_WIDTH}px`,
                height: '2.3rem',
              }}
            >
              {timeSlots.map((hour) => (
                <Box
                  key={hour}
                  sx={{
                    width: `${HOUR_WIDTH}px`,
                    minWidth: `${HOUR_WIDTH}px`,
                    flexShrink: 0,
                    position: 'relative',
                    '&::after': {
                      content: '""',
                      position: 'absolute',
                      left: 0,
                      top: '-1rem',
                      bottom: 0,
                      width: '1px',
                      backgroundColor:
                        theme === 'dark' ? Colors.Gray6 : Colors.Gray4,
                    },
                    '&:last-child::after': {
                      display: 'none',
                    },
                  }}
                >
                  <Box
                    sx={{
                      position: 'absolute',
                      left: "3px",
                      top: '-1rem',
                      transform: 'translateX(-50%)',
                      padding: '1rem',
                      color: theme === 'dark' ? '#DDDFE2' : '#2D2E30',
                      fontSize: '0.875rem',
                      backgroundColor: theme === 'dark' ? '#1A1A1A' : '#ffffff',
                      zIndex: 10,
                    }}
                  >
                    {hour}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>

          {/* Timeline Content Wrapper - contains grid lines and rows */}
          <Box
            sx={{
              position: 'relative',
              minHeight: `${totalContentHeight}px`,
              marginTop: '2rem',
              // marginBottom: '1rem',
              width:
                viewType === 'drone'
                  ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                  : `${TOTAL_TIMELINE_WIDTH}px`,
              minWidth:
                viewType === 'drone'
                  ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                  : `${TOTAL_TIMELINE_WIDTH}px`,
            }}
          >
            {/* Background Grid Lines - kéo dài hết chiều cao */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: viewType === 'drone' ? '200px' : 0,
                height: `${totalContentHeight}px`,
                display: 'flex',
                width: `${TOTAL_TIMELINE_WIDTH}px`,
                minWidth: `${TOTAL_TIMELINE_WIDTH}px`,
                pointerEvents: 'none',
                zIndex: 0,
              }}
            >
              {timeSlots.map((hour) => (
                <Box
                  key={hour}
                  sx={{
                    width: `${HOUR_WIDTH}px`,
                    minWidth: `${HOUR_WIDTH}px`,
                    flexShrink: 0,
                    height: '100%',
                    borderRight: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
                    '&:last-child': {
                      borderRight: 'none',
                    },
                  }}
                />
              ))}
            </Box>

            {/* Timeline Rows */}
            <Box
              sx={{
                position: 'relative',
                zIndex: 1,
              }}
            >
              {timelineItems.map((item, itemIndex) => {
                const itemEvents = getItemEvents(item, transformEvents);
                // Calculate max lane to determine row height
                const maxLane =
                  itemEvents.length > 0
                    ? Math.max(...itemEvents.map((e) => e.lane ?? 0))
                    : 0;
                const eventHeight = 44;
                const eventGap = 4;
                const baseTop = viewType === 'drone' ? 20 : 8;
                const rowHeight =
                  baseTop +
                  (maxLane + 1) * (eventHeight + eventGap) -
                  eventGap +
                  8; // +8 for padding bottom

                return (
                  <Box
                    key={itemIndex}
                    sx={{
                      position: 'relative',
                      minHeight: '60px',
                      height: `${rowHeight}px`,
                      display: 'flex',
                      width:
                        viewType === 'drone'
                          ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                          : `${TOTAL_TIMELINE_WIDTH}px`,
                      minWidth:
                        viewType === 'drone'
                          ? `${200 + TOTAL_TIMELINE_WIDTH}px`
                          : `${TOTAL_TIMELINE_WIDTH}px`,
                    }}
                  >
                    {/* Drone ID column (only in drone view) */}
                    {viewType === 'drone' && (
                      <Box
                        sx={{
                          width: '200px',
                          minWidth: '200px',
                          flexShrink: 0,
                          borderRight: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
                          padding: '0.75rem',
                          display: 'flex',
                          alignItems: 'center',
                          color: theme === 'dark' ? '#DDDFE2' : '#2D2E30',
                          fontSize: '1rem',
                          backgroundColor:
                            theme === 'dark' ? '#1A1A1A' : '#ffffff',
                          zIndex: 9999,
                          fontWeight: 600,
                          position: 'sticky',
                          left: 0,
                        }}
                      >
                        {item}
                      </Box>
                    )}

                    {/* Timeline content area */}
                    <Box
                      sx={{
                        width: `${TOTAL_TIMELINE_WIDTH}px`,
                        minWidth: `${TOTAL_TIMELINE_WIDTH}px`,
                        position: 'relative',
                        minHeight: '60px',
                        height: '100%',
                      }}
                    >
                      {/* Event Bars */}
                      {itemEvents.map((event, eventIndex) => {
                        const position = getEventPosition(
                          event.startTime,
                          event.endTime,
                          HOUR_WIDTH,
                        );
                        const lane = event.lane ?? 0;
                        const eventHeight = 44;
                        const eventGap = 4; // Gap between events in different lanes
                        const topOffset = 8 + lane * (eventHeight + eventGap);
                        const isPendingApproval =
                          event?.status_code == 'pending_approval';

                        return (
                          <Box
                            key={eventIndex}
                            sx={{
                              position: 'absolute',
                              top: `${topOffset}px`,
                              left: position.left,
                              width: position.width,
                              minWidth: '60px',
                              height: `${eventHeight}px`,
                              backgroundColor: blendWithBackground(
                                event.color,
                                '1A',
                                theme === 'dark' ? '#222222' : '#ffffff',
                              ), // Blend với background (1A = 10.2% opacity)
                              borderLeft: `4px solid ${event.color}`,
                              borderRadius: '4px',
                              padding: '0.5rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              cursor: 'pointer',
                              zIndex: 5,
                              boxSizing: 'border-box',
                              '&:hover': {
                                opacity: 0.9,
                                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                              },
                            }}
                          >
                            <Box sx={{ flex: 1, overflow: 'hidden' }}>
                              <Box
                                sx={{
                                  fontSize: '0.75rem',
                                  color: `${event.color}`,
                                  marginBottom: '2px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {event.startTime} - {event.endTime}
                              </Box>
                              <Box
                                sx={{
                                  fontSize: '0.875rem',
                                  fontWeight: 500,
                                  color:
                                    theme === 'dark'
                                      ? isPendingApproval
                                        ? Colors.Gray5
                                        : '#DDDFE2'
                                      : isPendingApproval
                                        ? Colors.Gray5
                                        : '#2D2E30',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {event.profileName}
                              </Box>
                            </Box>
                            <BsEye
                              onClick={() => onEventClick?.(event)}
                              size={16}
                              style={{
                                marginLeft: '8px',
                                color: theme === 'dark' ? '#DDDFE2' : '#2D2E30',
                                flexShrink: 0,
                              }}
                            />
                          </Box>
                        );
                      })}
                    </Box>
                  </Box>
                );
              })}
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default TimelineView;
