import { DroneSensorStatusType } from '../MainTabs/ProcessingTab/components/DroneSensorStatus';

export const checkStatusAllDrone = (
  status: string,
  droneSensorStatus: DroneSensorStatusType[],
) => {
  return droneSensorStatus.every((item) => item.situation === status);
};
