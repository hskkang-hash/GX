import type { Active, UniqueIdentifier } from '@dnd-kit/core';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import type { ReactNode } from 'react';
import React, { useMemo, useState } from 'react';
import { useTheme } from 'rj-core';

import { DragHandle, SortableItem } from './SortAbleItem/SortableItem';
import { SortableOverlay } from './SortOverlay/SortOverlay';
import './SortableList.scss';

interface BaseItem {
  order: UniqueIdentifier;
}

interface Props<T extends BaseItem> {
  items: T[];
  onChange(
    items: T[],
    activeId: string | number,
    overId: string | number,
  ): void;
  renderItem(item: T): ReactNode;
}

export function SortableList<T extends BaseItem>({
  items,
  onChange,
  renderItem,
}: Props<T>) {
  const [active, setActive] = useState<Active | null>(null);
  const activeItem = useMemo(
    () => items.find((item) => item.order === active?.id),
    [active, items],
  );
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const [theme] = useTheme();

  // Create an array of ids from the items' order property for SortableContext
  const itemIds = useMemo(() => items.map((item) => item.order), [items]);

  return (
    <DndContext
      sensors={sensors}
      onDragStart={({ active }) => {
        setActive(active);
      }}
      onDragEnd={({ active, over }) => {
        if (over && active.id !== over.id) {
          const activeIndex = items.findIndex(
            ({ order }) => order === active.id,
          );

          const activeId = active.id;
          const overId = over.id;

          const overIndex = items.findIndex(({ order }) => order === over.id);

          // Create a new array with moved items
          const newItems = arrayMove(items, activeIndex, overIndex);

          // Update the order property of each item to match its new position
          const updatedItems = newItems.map((item, index) => ({
            ...item,
            order: index + 1,
          }));

          onChange(updatedItems, activeId, overId);
        }
        setActive(null);
      }}
      onDragCancel={() => {
        setActive(null);
      }}
    >
      <SortableContext items={itemIds}>
        <ul
          className={`SortableList ${theme}`}
          role="application"
        >
          {items.map((item) => (
            <React.Fragment key={item.order}>{renderItem(item)}</React.Fragment>
          ))}
        </ul>
      </SortableContext>
      <SortableOverlay>
        {activeItem ? renderItem(activeItem) : null}
      </SortableOverlay>
    </DndContext>
  );
}

SortableList.Item = SortableItem;
SortableList.DragHandle = DragHandle;
