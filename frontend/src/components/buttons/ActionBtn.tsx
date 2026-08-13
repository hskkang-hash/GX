import { Fragment } from 'react';

import '../../assets/styles/ActionBtn.scss';

/*
USAGE:
    <ActionBtn
      leftButtons={[
        <CustomBtn {...props} />,
      ]}
      rightButtons={[
        <CustomBtn {...props} />,
      ]}
      styles={{
        maxWidth: '50%',
        backgroundColor: '#f0f0f0'
      }}  // optional custom styles for the container
    />

  - `leftButtons` (array): An array of buttons or any React elements to be displayed on the left side.
  - `rightButtons` (array): An array of buttons or any React elements to be displayed on the right side.
  - `styles` (object, optional): Inline styles for customizing the `ActionBtn` container. 
      The default max-width is set to 35%, but this can be overridden.
*/

const ActionBtn = ({
  leftButtons,
  rightButtons,
  middleButtons,
  styles,
}: {
  leftButtons: React.ReactNode[];
  rightButtons: React.ReactNode[];
  middleButtons: React.ReactNode[];
  styles: React.CSSProperties;
}) => {
  return (
    <div
      className={`py-6 gap-6 flex mb-0 justify-center mx-0 my-auto `}
      style={{
        maxWidth: '35%',
        ...styles,
      }}
    >
      {leftButtons && (
        <div className="action-btn flex-1 d-flex">
          {leftButtons.map((button, index) => (
            <Fragment key={index}>{button}</Fragment>
          ))}
        </div>
      )}
      {middleButtons && (
        <div className="action-btn flex-1 d-flex">
          {middleButtons.map((button, index) => (
            <Fragment key={index}>{button}</Fragment>
          ))}
        </div>
      )}
      {rightButtons && (
        <div className="action-btn flex-1">
          {rightButtons.map((button, index) => (
            <Fragment key={index}>{button}</Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActionBtn;
