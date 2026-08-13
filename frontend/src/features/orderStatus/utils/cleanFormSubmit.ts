export const cleanFormSubmit = (data: object) => {
  // Remove empty values is null or undefined
  const cleanData = Object.fromEntries(
    Object.entries(data).filter(
      ([, value]) => value !== null && value !== undefined,
    ),
  );
  return cleanData;
};
