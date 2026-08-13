import React, { useState, useEffect, useRef } from 'react';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';

import './styles/Truncate.scss';

const safeSubstring = (content: string, maxLengthContent?: number) => {
  if (!content) return '';
  if (maxLengthContent && content.length > maxLengthContent) {
    return content.substring(0, maxLengthContent) + '...';
  }
  return content;
};

interface TruncateProps {
  content: any;
  tooltipContent?: any;
  maxLengthContent?: number;
}

const Truncate: React.FC<TruncateProps> = ({
  content,
  tooltipContent,
  maxLengthContent,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [isOverflow, setIsOverflow] = useState(false);
  const spanRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const checkOverflow = () => {
      if (spanRef.current) {
        setIsOverflow(
          spanRef.current.scrollWidth > spanRef.current.clientWidth,
        );
      }
    };

    checkOverflow();
    const resizeObserver = new ResizeObserver(checkOverflow);
    if (spanRef.current) {
      resizeObserver.observe(spanRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, [content]);

  const handleMouseEnter = () => setShowTooltip(true);
  const handleMouseLeave = () => setShowTooltip(false);

  return (
    <OverlayTrigger
      placement="auto"
      show={showTooltip}
      delay={{
        show: 250,
        hide: 400,
      }}
      overlay={
        <Tooltip
          id="truncate-tooltip"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <div>{tooltipContent || content}</div>
        </Tooltip>
      }
    >
      <span
        ref={spanRef}
        className={!maxLengthContent ? 'truncate-ellipsis' : ''}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {maxLengthContent ? safeSubstring(content, maxLengthContent) : content}
      </span>
    </OverlayTrigger>
  );
};

export default Truncate;
