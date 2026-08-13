import { ConfigProvider, DatePicker } from 'antd';
import dayjs from 'dayjs';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { GoDash } from 'react-icons/go';

import '../../assets/styles/CustomDateTimePicker.scss';

interface CustomDateTimePickerProps {
  label: string;
  timeHelper?: { id: string; label: string }[];
  setObjSearch?: (obj: any) => void;
  value: {
    startDate: string | null;
    endDate: string | null;
    quick_select?: string | null;
  };
  setData: (data: { startDate: string | null; endDate: string | null }) => void;
  noTime?: boolean;
  horizontal?: boolean;
  setClearSelectedExpandedRows?: () => void;
  setRefreshTable?: () => void;
}
const CustomDateTimePicker = ({
  label,
  timeHelper,
  setObjSearch,
  value,
  setData,
  noTime = false,
  horizontal = true,
  noTitle = false,
  setRefreshTable = () => {},
  setClearSelectedExpandedRows = () => {},
}: CustomDateTimePickerProps) => {
  const { t } = useTranslation();
  const dateFormat = noTime ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm:ss';

  useEffect(() => {
    if (value.quick_select) {
      handleTimeSelection(value.quick_select);
    }
  }, [value.quick_select]);

  const handleTimeSelection = (timeRange: string) => {
    const now = new Date();
    let startDate: Date, endDate: Date;
    switch (timeRange) {
      case 'today':
        startDate = new Date(now.setHours(0, 0, 0, 0));
        endDate = new Date(now.setHours(23, 59, 59, 59));
        break;
      case 'last15min':
        startDate = new Date(now.getTime() - 15 * 60 * 1000);
        endDate = now;
        break;
      case 'last30min':
        startDate = new Date(now.getTime() - 30 * 60 * 1000);
        endDate = now;
        break;
      case 'lasthour':
        startDate = new Date(now.getTime() - 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last60min':
        startDate = new Date(now.getTime() - 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last4hr':
        startDate = new Date(now.getTime() - 4 * 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last12hr':
        startDate = new Date(now.getTime() - 12 * 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last24hr':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last3day':
        startDate = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last7day':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        endDate = now;
        break;
      case 'last30day':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        endDate = now;
        break;
      default:
        break;
    }
    setData({
      startDate: dayjs(startDate).format(dateFormat),
      endDate: dayjs(endDate).format(dateFormat),
    });
    setObjSearch((prevState: any) => ({
      ...prevState,
      quick_select: timeRange,
      startDate: dayjs(startDate).format(dateFormat),
      endDate: dayjs(endDate).format(dateFormat),
    }));
    setClearSelectedExpandedRows(true);
  };

  const onChangeStartDate = (startDate: Date) => {
    if (startDate) {
      const utcStartDate = new Date(startDate);
      if (!startDate.hour() && !startDate.minute() && !startDate.second()) {
        utcStartDate.setHours(0, 0, 0, 0);
      }
      setData({
        ...value,
        startDate: dayjs(utcStartDate).format(dateFormat),
      });
    } else {
      setData({
        ...value,
        startDate: null,
      });
    }
  };

  const onChangeEndDate = (endDate: Date) => {
    if (endDate) {
      const localEndDate = new Date(endDate);
      setData({
        ...value,
        endDate: dayjs(localEndDate).format(dateFormat),
      });
    } else {
      setData({
        ...value,
        endDate: null,
      });
    }
  };
  return (
    <div className={` min-h-[48px] ${horizontal ? 'horizontal' : 'vertical'}`}>
      <div className="flex flex-wrap items-center">
        <label className="font-semibold text-base mx-3 text-[#2D2E30]">
          {t(label)}
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <ConfigProvider>
            <DatePicker
              showTime={!noTime}
              className=" date-picker w-fit-content"
              placeholder={t('')}
              format={dateFormat}
              value={value?.startDate && dayjs(value?.startDate)}
              onChange={onChangeStartDate}
            />
            <GoDash />
            <DatePicker
              showTime={!noTime}
              className=" date-picker w-fit-content"
              placeholder={t('')}
              format={dateFormat}
              value={value?.endDate && dayjs(value?.endDate)}
              onChange={onChangeEndDate}
              disabledDate={(current) =>
                current && current.isBefore(dayjs(value?.startDate), 'day')
              }
            />
          </ConfigProvider>
        </div>
      </div>
      {timeHelper ? (
        <div className="flex flex-wrap gap-2">
          {timeHelper.map((time: { id: string; label: string }) => (
            <button
              key={time.id}
              onClick={() => handleTimeSelection(time.id)}
              className="cursor-pointer w-auto bg-[#f2f2f2] text-[#444646] text-sm font-normal px-2 py-1 rounded-full focus:outline-none focus:border focus:border-[0.0625em] focus:border-[var(--ga-primary)]"
            >
              {time.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default CustomDateTimePicker;
