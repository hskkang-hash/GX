export const checkCodeValid = (code: string) => {
  switch (code) {
    case 'KR':
      return 'KR';
    case 'TH':
      return 'TH';
    default:
      return 'KR';
  }
};
