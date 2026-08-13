import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ReactIcon } from '../../../../../components/ReactIcon/ReactIcon';
import './ReplyBox.scss';

interface ReplyBoxProps {
  onReply: (reply: string) => void;
  cancel?: () => void;
  isRoot?: boolean;
  defaultContent?: string;
  disabled?: boolean;
}

const ReplyBox = ({
  onReply,
  cancel,
  isRoot,
  defaultContent,
  disabled = false,
}: ReplyBoxProps): React.JSX.Element => {
  const { t } = useTranslation();
  const [reply, setReply] = useState<string>(defaultContent || '');
  const [error, setError] = useState<boolean>(false);
  const [isFocused, setIsFocused] = useState<boolean>(false);

  const handleReply = useCallback((): void => {
    if (!reply.trim()) {
      setError(true);
      return;
    }
    onReply(reply);
    setReply('');
    setError(false);
    setIsFocused(false);
  }, [reply, onReply]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleReply();
      }
    },
    [handleReply],
  );

  return (
    <div className={`reply-box ${isRoot ? 'root-reply-box' : ''}`}>
      <div className={`input-wrapper ${isFocused ? 'focused' : ''}`}>
        <textarea
          placeholder={t('handover.Write your comment')}
          className={`form-control ${error ? 'is-invalid' : ''}`}
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          disabled={disabled}
          onKeyDown={handleKeyDown}
        />
        {isFocused && (
          <ReactIcon
            className="send-button"
            color="var(--ga-primary)"
            iconName="BsSend"
            style={{ width: '1.5rem', height: '1.5rem' }}
            onMouseDown={handleReply}
          />
        )}
      </div>
      {error && (
        <div className="invalid-feedback">{t("handover.Comment can't be blank")}</div>
      )}
      {cancel && (
        <div className="reply-box-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={cancel}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};

export default ReplyBox;
