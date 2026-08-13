import { useEffect, useMemo, useState } from 'react';

const useBoolean = (initialValue = false) => {
  const [value, setValue] = useState(initialValue);

  const { setTrue, setFalse } = useMemo(
    () => ({
      setTrue: () => setValue(true),
      setFalse: () => setValue(false),
    }),
    [],
  );

  return [value, setTrue, setFalse];
};

export default useBoolean;

export function usePersistedState(key: string, defaultValue: any) {
  const [state, setState] = useState(() => {
    const storedValue = localStorage.getItem(key);
    return storedValue !== null ? JSON.parse(storedValue) : defaultValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(state));
  }, [key, state]);

  return [state, setState];
}
