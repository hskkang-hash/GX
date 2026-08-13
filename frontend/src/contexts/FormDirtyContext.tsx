import {
  createContext,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from 'react';

interface FormSubmitHandler {
  submit: () => Promise<boolean>;
  triggerValidation: () => Promise<boolean>;
}

interface FormDirtyContextType {
  isDirty: boolean;
  setDirty: (dirty: boolean) => void;
  registerSubmitHandler: (handler: FormSubmitHandler) => void;
  unregisterSubmitHandler: () => void;
  triggerSubmit: () => Promise<boolean>;
  triggerValidation: () => Promise<boolean>;
}

const FormDirtyContext = createContext<FormDirtyContextType | undefined>(
  undefined,
);

export const FormDirtyProvider = ({ children }: { children: ReactNode }) => {
  const [isDirty, setIsDirty] = useState(false);
  const submitHandlerRef = useRef<FormSubmitHandler | null>(null);

  const setDirty = (dirty: boolean): void => {
    setIsDirty(dirty);
  };

  const registerSubmitHandler = (handler: FormSubmitHandler): void => {
    submitHandlerRef.current = handler;
  };

  const unregisterSubmitHandler = (): void => {
    submitHandlerRef.current = null;
  };

  const triggerSubmit = async (): Promise<boolean> => {
    if (submitHandlerRef.current) {
      return await submitHandlerRef.current.submit();
    }
    return false;
  };

  const triggerValidation = async (): Promise<boolean> => {
    if (submitHandlerRef.current) {
      return await submitHandlerRef.current.triggerValidation();
    }
    return false;
  };

  return (
    <FormDirtyContext.Provider
      value={{
        isDirty,
        setDirty,
        registerSubmitHandler,
        unregisterSubmitHandler,
        triggerSubmit,
        triggerValidation,
      }}
    >
      {children}
    </FormDirtyContext.Provider>
  );
};

export const useFormDirtyContext = (): FormDirtyContextType => {
  const context = useContext(FormDirtyContext);
  if (context === undefined) {
    throw new Error(
      'useFormDirtyContext must be used within a FormDirtyProvider',
    );
  }
  return context;
};
