import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import { v4 as uuid } from 'uuid';

import { ReactIcon } from '@/components/ReactIcon/ReactIcon';

import i18n from '../../../../i18n';
import { useDateTimeFormat } from '../../hooks/useDateFormat';
import { formatDateTime } from '../../utils/dateFormat';
import './NestedComments.scss';
import ReplyBox from './ReplyBox/ReplyBox';

interface CommentData {
  id: string | number;
  parentId?: string | number;
  content: string;
  writer_name?: string;
  userId?: string | number;
  color?: string;
  updated_time: string;
  count_child?: number;
  is_update?: boolean;
  children?: CommentData[];
}

interface TreeData extends Omit<CommentData, 'content' | 'updated_time'> {
  content?: string;
  updated_time?: string;
  children: CommentData[];
}

interface NestedCommentsProps {
  data?: CommentData[];
  commentAdded?: (data: {
    comment_id?: string | number;
    parent_id?: string | number;
    comment: string;
  }) => void;
  onDelete?: (id: string | number) => void;
  paginationSize?: number;
  userId?: string | number;
  loadMoreComment?: (params: { parent_id: string | number }) => void;
  fetchReplies?: (params: unknown) => void;
  showComments: Record<string | number, boolean>;
  setShowComments: React.Dispatch<
    React.SetStateAction<Record<string | number, boolean>>
  >;
  disableComment?: boolean;
  totalPages?: number;
  currentPage?: number;
  onLoadMore?: () => void;
  maxHeight?: string;
}

interface RecurseProps {
  root: TreeData;
  commentAdded: (data: {
    comment_id?: string | number;
    parent_id?: string | number;
    comment: string;
  }) => void;
  getRandomColor: (userId?: string | number) => string;
  userId?: string | number;
  paginationSize: number;
  showComments: Record<string | number, boolean>;
  setShowComments: React.Dispatch<
    React.SetStateAction<Record<string | number, boolean>>
  >;
  loadMoreComment?: (params: { parent_id: string | number }) => void;
  onDelete?: (id: string | number) => void;
  disableComment: boolean;
  theme: string;
  t: (key: string) => string;
  PARENT_ROOT: string;
  totalPages?: number;
  currentPage?: number;
  onLoadMore?: () => void;
  dateFormat: string;
  timeFormat: string;
  timezoneCode: string | null;
}

const PARENT_ROOT = '*';

const NestedComments = ({
  data = [],
  commentAdded = () => {},
  onDelete = () => {},
  paginationSize = 2,
  userId,
  loadMoreComment,
  showComments,
  setShowComments,
  disableComment = false,
  totalPages = 0,
  currentPage = 1,
  onLoadMore,
  maxHeight = 'auto',
}: NestedCommentsProps): React.JSX.Element => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();
  const [treeData, setTreeData] = useState<TreeData>({
    children: [],
    id: PARENT_ROOT,
  });
  const [mapColors, setMapColors] = useState<Record<string | number, string>>(
    {},
  );

  const getRandomColor = useCallback(
    (userId?: string | number): string => {
      if (userId !== undefined && mapColors[userId]) {
        return mapColors[userId];
      }

      let color = '#';
      for (let i = 0; i < 6; i++) {
        color += Math.floor(Math.random() * 10);
      }

      if (userId !== undefined) {
        setMapColors((prev) => ({ ...prev, [userId]: color }));
      }

      return color;
    },
    [mapColors],
  );

  const createTree = useCallback(
    (dataImport: CommentData[]): CommentData[] => {
      const mapRelations = new Map<string | number, CommentData[]>();
      const rootElements: CommentData[] = [];

      dataImport.forEach((comment) => {
        if (!comment.parentId) {
          rootElements.push(comment);
        } else {
          if (!mapRelations.has(comment.parentId)) {
            mapRelations.set(comment.parentId, []);
          }
          mapRelations.get(comment.parentId)?.push(comment);
        }
      });

      const buildTree = (comments: CommentData[]): CommentData[] => {
        return comments.map((comment) => {
          let children: CommentData[] = [];
          if (mapRelations.has(comment.id)) {
            children = buildTree(mapRelations.get(comment.id) || []);
          }
          if (
            showComments[comment.id] === undefined &&
            comment?.count_child &&
            comment.count_child > 0
          ) {
            setShowComments((prev) => ({ ...prev, [comment.id]: false }));
          }
          return {
            ...comment,
            color:
              comment.color !== undefined
                ? comment.color
                : getRandomColor(comment.userId),
            children: children,
          };
        });
      };

      return buildTree(rootElements);
    },
    [getRandomColor, showComments, setShowComments],
  );

  const treeDataMemo = useMemo(() => {
    return {
      children: createTree(data),
      id: PARENT_ROOT,
    };
  }, [data, createTree]);

  useEffect(() => {
    setTreeData(treeDataMemo);
  }, [treeDataMemo]);

  const Recurse = ({
    root,
    commentAdded,
    getRandomColor,
    userId,
    paginationSize,
    showComments,
    setShowComments,
    loadMoreComment,
    onDelete,
    disableComment,
    theme,
    t,
    PARENT_ROOT,
    totalPages = 0,
    currentPage = 1,
    onLoadMore,
    dateFormat,
    timeFormat,
    timezoneCode,
  }: RecurseProps): React.JSX.Element => {
    const [showTextBox, setShowTextBox] = useState<boolean>(false);
    const [showEditBox, setShowEditBox] = useState<boolean>(false);

    const cancel = useCallback((): void => {
      setShowTextBox(false);
      setShowEditBox(false);
    }, []);

    const onReply = useCallback(
      (reply: string, comment_id?: string | number): void => {
        const unique_id = uuid();
        const small_id = unique_id.slice(0, 8);
        root.children.unshift({
          id: small_id,
          content: reply,
          updated_time: new Date().toISOString(),
          color: getRandomColor(userId),
          count_child: 0,
          children: [],
        });

        setShowComments((prev) => ({ ...prev, [root.id]: true }));
        setShowTextBox(false);
        commentAdded(
          comment_id
            ? { comment_id: comment_id, comment: reply }
            : root.id !== PARENT_ROOT
              ? {
                  parent_id: root.id,
                  comment: reply,
                }
              : { comment: reply },
        );
      },
      [
        root,
        getRandomColor,
        userId,
        setShowComments,
        commentAdded,
        PARENT_ROOT,
      ],
    );

    const isRoot = root.id === PARENT_ROOT;
    const isDark = theme === 'dark';
    const iconColor = useMemo(
      () => (showTextBox ? '#1D9BE2' : isDark ? 'white' : '#9C9D9D'),
      [showTextBox, isDark],
    );
    const shouldShowChildren = (showComments && root) || isRoot;
    const hasHiddenReplies =
      !showComments[root.id] &&
      !isRoot &&
      root.count_child &&
      root.count_child > 0;
    const isOwnComment =
      userId !== undefined &&
      root.userId !== undefined &&
      Number(userId) === Number(root.userId);
    const showLoadMoreButton =
      isRoot && totalPages > 1 && currentPage < totalPages && onLoadMore;

    return (
      <div
        className={`comment-thread ${isRoot ? 'root' : ''} 
        text-${isDark ? 'white' : 'black'}`}
        data-bs-theme={isDark ? 'dark' : 'light'}
      >
        {isRoot && !disableComment && (
          <>
            <div
              className="fw-bold mb-2"
              id="text-comment"
            >
              {t('handover.Comment')}
            </div>
            <ReplyBox
              onReply={onReply}
              isRoot={true}
            />
          </>
        )}

        <div
          className={`${!isRoot ? 'comment-reply' : ''} ${
            !root.parentId ? 'comment-lv1' : ''
          }`}
          style={{ overflowY: 'scroll', maxHeight: maxHeight }}
        >
          {!isRoot && (
            <div className="comment">
              <div className="comment-header">
                <div className="d-flex">
                  {root.parentId && (
                    <ReactIcon
                      color={isDark ? 'white' : 'black'}
                      style={{
                        marginRight: '0.25rem',
                        width: '1.25rem',
                        height: '1.25rem',
                      }}
                      iconName="BsArrowReturnRight"
                    />
                  )}
                  <div
                    className={`comment-body flex-grow-1 ${isDark ? 'dark' : ''}`}
                  >
                    <div className="comment-writer">{root.writer_name}</div>
                    {showEditBox && !disableComment ? (
                      <div className="reply-box-container">
                        <ReplyBox
                          defaultContent={root.content}
                          onReply={(reply) => onReply(reply, root.id)}
                          cancel={cancel}
                        />
                      </div>
                    ) : (
                      <div
                        className="comment-content mt-2"
                        style={{ whiteSpace: 'pre' }}
                      >
                        <span>{root.content}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="comment-footer">
                <div className="comment-time">
                  {root.updated_time
                    ? formatDateTime(
                        root.updated_time,
                        dateFormat,
                        timeFormat,
                        i18n.language,
                        timezoneCode,
                      )
                    : ''}
                </div>
                {!disableComment && (
                  <div className="comment-action">
                    {isOwnComment && (
                      <>
                        <ReactIcon
                          color={iconColor}
                          style={{
                            cursor: 'pointer',
                            width: '1.25rem',
                            height: '1.25rem',
                          }}
                          iconName="BsTrash"
                          onClick={() => onDelete?.(root.id)}
                        />
                        <ReactIcon
                          color={iconColor}
                          style={{
                            cursor: 'pointer',
                            width: '1.25rem',
                            height: '1.25rem',
                            margin: '0 0.75rem',
                          }}
                          iconName="BsPencil"
                          onClick={() => setShowEditBox(true)}
                        />
                      </>
                    )}
                    <ReactIcon
                      color={iconColor}
                      style={{
                        cursor: 'pointer',
                        width: '1.5rem',
                        height: '1.5rem',
                      }}
                      iconName="BsReply"
                      onClick={() => setShowTextBox(!showTextBox)}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {showTextBox && !disableComment && (
            <div className="reply-box-container">
              <ReplyBox
                onReply={onReply}
                cancel={cancel}
              />
            </div>
          )}

          {shouldShowChildren &&
            root.children.map((ele) => (
              <div key={ele.id}>
                <Recurse
                  root={ele as TreeData}
                  commentAdded={commentAdded}
                  getRandomColor={getRandomColor}
                  userId={userId}
                  paginationSize={paginationSize}
                  showComments={showComments}
                  setShowComments={setShowComments}
                  loadMoreComment={loadMoreComment}
                  onDelete={onDelete}
                  disableComment={disableComment}
                  theme={theme}
                  t={t}
                  PARENT_ROOT={PARENT_ROOT}
                  totalPages={totalPages}
                  currentPage={currentPage}
                  onLoadMore={onLoadMore}
                  dateFormat={dateFormat}
                  timeFormat={timeFormat}
                  timezoneCode={timezoneCode}
                />
              </div>
            ))}

          {hasHiddenReplies && (
            <button
              type="button"
              className="view-replies-button"
              onClick={() => {
                loadMoreComment?.({ parent_id: root.id });
                setShowComments((prev) => ({ ...prev, [root.id]: true }));
              }}
            >
              {t('handover.View more replies')}
              {' . '}
              {root.count_child} {t('handover.replies')}
            </button>
          )}

          {showLoadMoreButton && (
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <button
                type="button"
                className="show-more-button"
                onClick={onLoadMore}
              >
                {t('Load More')}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      <Recurse
        root={treeData}
        commentAdded={commentAdded}
        getRandomColor={getRandomColor}
        userId={userId}
        paginationSize={paginationSize}
        showComments={showComments}
        setShowComments={setShowComments}
        loadMoreComment={loadMoreComment}
        onDelete={onDelete}
        disableComment={disableComment}
        theme={theme}
        t={t}
        PARENT_ROOT={PARENT_ROOT}
        totalPages={totalPages}
        currentPage={currentPage}
        onLoadMore={onLoadMore}
        dateFormat={dateFormat}
        timeFormat={timeFormat}
        timezoneCode={timezoneCode}
      />
    </div>
  );
};

export default NestedComments;
