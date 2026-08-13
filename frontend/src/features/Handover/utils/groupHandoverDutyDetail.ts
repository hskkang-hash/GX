import { HandoverDutyDetailGrouped, HandoverNoticeState } from '../types';

/**
 * Groups handover duty detail items by handover_doc_id
 * @param handoverDutyDetail - Array of handover notice items
 * @returns Array of grouped items with handover_doc_id, data, and date
 */
export const groupHandoverDutyDetail = (
  handoverDutyDetail: HandoverNoticeState[],
): HandoverDutyDetailGrouped[] => {
  const groupedMap = new Map<number, HandoverNoticeState[]>();

  handoverDutyDetail.forEach((item) => {
    const docId = item.handover_doc_id || item.handover_doc__id || 0;
    if (!groupedMap.has(docId)) {
      groupedMap.set(docId, []);
    }
    groupedMap.get(docId)?.push(item);
  });

  return Array.from(groupedMap.entries()).map(
    ([handover_doc_id, data]): HandoverDutyDetailGrouped => {
      const firstItem = data[0];
      const date =
        firstItem?.handover_doc__date_create_shift ||
        (firstItem?.handover_doc as { date_create_shift?: string })
          ?.date_create_shift ||
        '';

      const shiftName = firstItem?.shift_name;

      const dataWithIsEdit = data.map((item) => ({
        ...item,
        is_edit: true,
      }));

      return {
        handover_doc_id,
        shift_name: shiftName || '',
        data: dataWithIsEdit,
        date,
      };
    },
  );
};
