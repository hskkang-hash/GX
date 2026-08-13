import React from 'react';

// It is assumed that the project is set up to handle SVG imports as React components (e.g., with SVGR).
import BellLightIcon from '@/assets/images/dashboard/bell-light-icon.svg';
import CalendarLightIcon from '@/assets/images/dashboard/calenar-light-icon.svg';
import DeliveryPointIcon from '@/assets/images/dashboard/daycare_1.svg';
import Drone1Icon from '@/assets/images/dashboard/drone-25kg.svg';
import Drone2Icon from '@/assets/images/dashboard/drone-40kg.svg';
import ItemTypeLightIcon from '@/assets/images/dashboard/item-type-light-icon.svg';
import ListnoteLightIcon from '@/assets/images/dashboard/listnote-light-icon.svg';
import RegionalLightIcon from '@/assets/images/dashboard/regional-light-icon.svg';
import RobotIcon from '@/assets/images/dashboard/robot.svg';
import DeliveryHubIcon from '@/assets/images/dashboard/warehouse_1.svg';
import DockingStationIcon from '@/assets/images/dashboard/warehouse_2.svg';
import WeightLightIcon from '@/assets/images/dashboard/weight-light-icon.svg';

const iconMap: { [key: string]: string } = {
  bell: BellLightIcon,
  calendar: CalendarLightIcon,
  package: ItemTypeLightIcon,
  'clipboard-cancel': ListnoteLightIcon,
  'clipboard-check': ListnoteLightIcon,
  building: RegionalLightIcon,
  weight: WeightLightIcon,
  's-drone': Drone1Icon,
  'm-drone': Drone2Icon,
  robot: RobotIcon,
  'delivery-hub': DeliveryHubIcon,
  'docking-station': DockingStationIcon,
  'delivery-point': DeliveryPointIcon,
};

/**
 * Returns the corresponding icon component based on the icon name.
 * @param iconName - The name of the icon from the panel_config.
 * @returns A React component for the icon, or null if not found.
 */
export const getIcon = (
  iconName?: string,
): React.FC<React.ImgHTMLAttributes<HTMLImageElement>> | null => {
  if (!iconName) {
    return null;
  }
  const iconSrc = iconMap[iconName];
  if (!iconSrc) {
    return null;
  }
  // Return a component that renders an <img> tag
  return (props) => (
    <img
      src={iconSrc}
      alt={`${iconName} icon`}
      style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
      {...props}
    />
  );
};
