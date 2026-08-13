import dayjs from 'dayjs';
import { useEffect } from 'react';

import ClearIcon from '../../assets/images/ClearIcon';
import SearchIcon from '../../assets/images/SearchIcon';
import UnionIcon from '../../assets/images/UnionIcon';
import '../../assets/styles/SearchCard.scss';
import Colors from '../../configs/Colors';
import CustomBtnIcon from '../buttons/CustomBtnIcon';
import CustomDateTimePicker from '../buttons/CustomDateTimePicker';

const SearchCard = ({
  setRefreshTable = () => {},
  setClearSelectedExpandedRows = () => {},
  handleSearchSetting = () => {},
  handleSearch = () => {},
  clearOption,
  setTimePicker,
  timePicker,
  objSearch,
  setObjSearch,
  noTime = false,
}: {
  setRefreshTable: () => void;
  setClearSelectedExpandedRows: () => void;
  handleSearchSetting: any;
  clearOption: any;
  setTimePicker: any;
  timePicker: any;
  objSearch: any;
  setObjSearch: any;
  handleSearch: any;
  noTime?: boolean;
}) => {
  const timeHelper = [
    { id: 'today', label: 'Today' },
    { id: 'last60min', label: 'Last hour' },
    { id: 'last4hr', label: 'Last 4 hours' },
    { id: 'last12hr', label: 'Last 12 hours' },
    { id: 'last7day', label: 'Last 7 days' },
  ];
  const dateFormat = noTime ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm:ss';

  useEffect(() => {
    if (objSearch?.startDate || objSearch?.endDate) {
      if (objSearch?.startDate) {
        setTimePicker((prev: any) => ({
          ...prev,
          startDate: dayjs(objSearch.startDate).format('DD/MM/YYYY'),
        }));
      }
      if (objSearch?.endDate) {
        setTimePicker((prev: any) => ({
          ...prev,
          endDate: dayjs(objSearch.endDate).format(dateFormat),
        }));
      }
    } else {
      setTimePicker({
        startDate: null,
        endDate: null,
      });
    }

    if (objSearch?.quick_select) {
      setTimePicker({
        quick_select: objSearch?.quick_select,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [objSearch?.startDate, objSearch?.endDate, objSearch?.quick_select]);

  return (
    <div className="flex items-center bg-white dark:bg-secondary rounded-lg">
      <CustomDateTimePicker
        label={'Created Date'}
        timeHelper={timeHelper}
        value={timePicker}
        setData={setTimePicker}
        setObjSearch={setObjSearch}
        setRefreshTable={setRefreshTable}
        setClearSelectedExpandedRows={setClearSelectedExpandedRows}
        noTime={noTime}
        noTitle={true}
      />
      <div className="flex justify-content-end m-0 ml-4 gap-4">
        <CustomBtnIcon
          onClick={handleSearchSetting}
          icon={<SearchIcon color={Colors.Primary} />}
        />
        <CustomBtnIcon
          onClick={handleSearch}
          icon={<UnionIcon color={Colors.Primary} />}
        />
        <CustomBtnIcon
          onClick={() => {
            setTimePicker({ startDate: null, endDate: null });
            clearOption ? clearOption() : setObjSearch({});
            setRefreshTable(true);
          }}
          icon={<ClearIcon color={Colors.Secondary} />}
          isClear
        />
      </div>
    </div>
  );
};

export default SearchCard;
