import { Waypoint } from '../../SurveyMission/types/surveyMission.types';

export const ConvertCommandInput = (waypoint: Waypoint): object => {
  const values = [
    waypoint?.param_1 || 0,
    waypoint?.param_2 || 0,
    waypoint?.param_3 || 0,
    waypoint?.param_4 || 0,
    waypoint?.latitude,
    waypoint?.longitude,
    waypoint?.altitude || 0,
  ];

  const result = {
    [waypoint?.command?.value]: {
      [waypoint?.command?.label]: values,
    },
  };

  return result;
};

export const ConvertFrameInput = (waypoint: Waypoint): object | null => {
  if (!waypoint?.frame) {
    return null;
  }

  const result = {
    [waypoint?.frame?.value]: waypoint?.frame?.label,
  };

  return result;
};
