export const fetchFromObject = (obj: any, prop: string): any => {
  if (!obj) return;

  const index = prop.indexOf('.');
  if (index > -1) {
    return fetchFromObject(
      obj[prop.substring(0, index)],
      prop.substring(index + 1),
    );
  }

  return obj[prop];
};

export const isEmptyObject = (obj: any) => {
  return obj && typeof obj === 'object' && Object.keys(obj).length === 0;
};
