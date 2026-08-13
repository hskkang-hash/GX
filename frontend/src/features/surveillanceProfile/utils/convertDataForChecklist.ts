export const convertDataForChecklist = (data: any) => {
  const result: any[] = [];

  data.forEach((entry) => {
    const categoryName = entry.category__name || entry.category || 'Unknown';

    let categoryGroup = result.find((c) => c.name_category === categoryName);

    if (!categoryGroup) {
      categoryGroup = {
        name_category: categoryName,
        item: [],
      };
      result.push(categoryGroup);
    }

    const {
      category__name,
      category__code,
      category__id,
      category,
      ...itemData
    } = entry;
    categoryGroup.item.push(itemData);
  });

  return result;
};
