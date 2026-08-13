const FormBlock = ({
  children,
  className = '',
  ...props
}: {
  children: React.ReactNode;
  className?: string;
  props?: any;
}) => {
  const theme = useTheme();
  return (
    <div
      className={`p-4 rounded-xl bg-white ${className} `}
      {...props}
    >
      <form className="flex flex-col gap-4">{children}</form>
    </div>
  );
};

export default FormBlock;
