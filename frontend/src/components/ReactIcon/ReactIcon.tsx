import { IconBaseProps } from 'react-icons';
import * as BsIcons from 'react-icons/bs';
import * as FaIcons from 'react-icons/fa';

const icons = { ...BsIcons, ...FaIcons };

export const ReactIcon = ({
  iconName,
  ...props
}: {
  iconName: string;
} & React.SVGProps<SVGSVGElement>) => {
  const IconComponent = icons[iconName as keyof typeof icons];
  return IconComponent ? <IconComponent {...(props as IconBaseProps)} /> : null;
};
