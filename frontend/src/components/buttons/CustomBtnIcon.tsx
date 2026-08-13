interface CustomBtnIconProps {
  icon: React.ReactNode;
  isClear?: boolean;
  onClick?: () => void;
}
const CustomBtnIcon = ({ icon, isClear, onClick }: CustomBtnIconProps) => {
  return (
    <button
      onClick={onClick}
      className={`h-8 w-8 bg-white rounded-lg border cursor-pointer
        flex justify-center items-center ${isClear ? 'border-ga-gray-4' : 'border-ga-primary'}`}
    >
      {icon}
    </button>
  );
};

export default CustomBtnIcon;
