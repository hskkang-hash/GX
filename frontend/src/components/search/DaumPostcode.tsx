import { Box, Button } from '@mui/material';
import React from 'react';

import Colors from '@/configs/Colors';

declare global {
  interface Window {
    daum: any;
  }
}

interface DaumPostcodeProps {
  onComplete: (data: any) => void;
  isRequired?: boolean;
  value?: string;
  placeholder?: string;
  label?: string;
}

const DaumPostcode: React.FC<DaumPostcodeProps> = ({
  onComplete,
  isRequired,
  value,
  placeholder,
  label,
}) => {
  const handleClick = () => {
    new window.daum.Postcode({
      oncomplete: function (data: any) {
        // Format the address data
        const fullAddress = data.address;
        const extraAddress = '';

        if (data.addressType === 'R') {
          if (data.bname !== '') {
            extraAddress += data.bname;
          }
          if (data.buildingName !== '') {
            extraAddress +=
              extraAddress !== ''
                ? `, ${data.buildingName}`
                : data.buildingName;
          }
        }

        const formattedData = {
          address_name: fullAddress,
          lat: data.latitude,
          lng: data.longitude,
          province: data.sido,
          district: data.sigungu,
          township: data.bname,
          building_name: data.buildingName,
          address_type: data.addressType,
          zip_code: data.zonecode,
        };

        onComplete(formattedData);
      },
    }).open();
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        <input
          type="text"
          value={value || ''}
          readOnly
          placeholder={placeholder}
          style={{
            flex: 1,
            padding: '8px 12px',
            border: `1px solid ${Colors.Gray4}`,
            borderRadius: '4px',
            fontSize: '14px',
          }}
        />
        <Button
          variant="contained"
          onClick={handleClick}
          sx={{
            minWidth: '120px',
            backgroundColor: Colors.Primary,
            color: Colors.White,
            '&:hover': {
              backgroundColor: Colors.Primary,
              opacity: 0.9,
            },
          }}
        >
          주소 검색
        </Button>
      </Box>
    </Box>
  );
};

export default DaumPostcode;
