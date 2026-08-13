import { BiCheck, BiX } from 'react-icons/bi';

export const formatEnabled = (item: any) => {
  if (item === true || item === 'active') {
    return <BiCheck style={{ color: '#0CBA47', fontSize: '1.25em' }} />;
  } else if (item === false || item === 'inactive') {
    return <BiX style={{ color: 'red', fontSize: '1.25em' }} />;
  } else {
    return '-';
  }
};

export const formatStatus = (item: string, theme: string, t: any) => {
  if (item === 'delivered' || item === 'shipped') {
    return (
      <span
        className="status-style"
        style={{
          color: '#0CBA47',
          backgroundColor: theme === 'dark' ? '#3F5848' : '#D6F8E2',
        }}
      >
        {t('Delivered')}
      </span>
    );
  } else if (item === 'pending_confirmation') {
    return (
      <span
        className="status-style"
        style={{
          color: '#1D9BE2',
          backgroundColor: theme === 'dark' ? '#3B4C55' : '#E3F5FF',
        }}
      >
        {t('Pending Confirmation')}
      </span>
    );
  } else if (item === 'awaiting_shipment' || item === 'in_transit') {
    return (
      <span
        className="status-style"
        style={{
          color: '#EB7509',
          backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
        }}
      >
        {t('Awaiting Shipment')}
      </span>
    );
  } else if (item === 'cancelled' || item === 'canceled') {
    return (
      <span
        className="status-style"
        style={{
          color: '#EE533D',
          backgroundColor: theme === 'dark' ? '#613B3B' : '#FFEBE8',
        }}
      >
        {t('Cancelled')}
      </span>
    );
  } else if (item === 'pending_processing' || item === 'pending_shipment') {
    return (
      <span
        className="status-style"
        style={{
          color: '#F0C418',
          backgroundColor: theme === 'dark' ? '#4C3E08' : '#FDF5D7',
        }}
      >
        {t('Pending Processing')}
      </span>
    );
  } else if (item === 'awaiting_payment') {
    return (
      <span
        className="status-style"
        style={{
          color: '#683DE2',
          backgroundColor: theme === 'dark' ? '#372B4D' : '#F4E7FF',
        }}
      >
        {t('Awaiting Payment')}
      </span>
    );
  } else if (item === 'returned' || item === 'received') {
    return (
      <span
        className="status-style"
        style={{
          color: '#9C9D9D',
          backgroundColor: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
        }}
      >
        {t('Returned')}
      </span>
    );
  } else if (item === 'arrived') {
    return (
      <span
        className="status-style"
        style={{
          color: '#EB7509',
          backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
        }}
      >
        {t('Arrived')}
      </span>
    );
  } else {
    return (
      <span
        className="status-style"
        style={{
          color: 'red',
          backgroundColor: theme === 'dark' ? '#613B3B' : '#F8E2E2',
        }}
      >
        {t('N/A')}
      </span>
    );
  }
};

export const formatStatusEtri = (item: string, t: any) => {
  let backgroundColor = '#ff0000';
  let color = 'white';
  let label = t('N/A');
  // "Delivery Completed": "배송완료",
  // "Delivery Cancelled": "배송취소",
  // "In Delivery": "배송중",
  // "Waiting for Delivery": "배송대기",
  // "Receipt Completed": "접수완료",
  // "Receipt Cancelled": "접수취소"
  switch (item) {
    case t('etri.Delivery Completed'):
      backgroundColor = '#4caf50';
      color = 'white';
      label = t('etri.Delivery Completed');
      break;

    case t('etri.Delivery Cancelled'):
      backgroundColor = '#f44336';
      color = 'white';
      label = t('etri.Delivery Cancelled');
      break;
    case t('etri.Receipt Cancelled'):
      backgroundColor = '#f44336';
      color = 'white';
      label = t('etri.Receipt Cancelled');
      break;

    case t('etri.In Delivery'):
      backgroundColor = '#ff9800';
      color = 'white';
      label = t('etri.In Delivery');
      break;

    case t('etri.Waiting for Delivery'):
      backgroundColor = '#2196f3';
      color = 'white';
      label = t('etri.Waiting for Delivery');
      break;

    case t('etri.Receipt Completed'):
      backgroundColor = '#ffeb3b';
      color = 'black';
      label = t('etri.Receipt Completed');
      break;

    default:
      backgroundColor = '#9C9D9D';
      color = 'white';
      label = t(item) || t('N/A');
      break;
  }
  return (
    <span
      className="status-style"
      style={{ backgroundColor, color }}
    >
      {label}
    </span>
  );
};

export const formatStatusSurveyMission = (
  item: string,
  name: string,
  t: any,
  theme: string = 'light',
) => {
  switch (item) {
    case 'pending_approval':
      return (
        <span
          className="status-style"
          style={{
            color: '#9C9D9D',
            backgroundColor: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
          }}
        >
          {name}
        </span>
      );
    case 'approved':
      return (
        <span
          className="status-style"
          style={{
            color: '#0CBA47',
            backgroundColor: theme === 'dark' ? '#3F5848' : '#D6F8E2',
          }}
        >
          {name}
        </span>
      );
    case 'rejected':
      return (
        <span
          className="status-style"
          style={{
            color: '#EB7509',
            backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
          }}
        >
          {name}
        </span>
      );
    default:
      return (
        <span
          className="status-style"
          style={{
            color: '#9C9D9D',
            backgroundColor: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
          }}
        >
          {name}
        </span>
      );
  }
};

export const formatIsProcessed = (
  t: any,
  theme: string = 'light',
  item: string,
) => {
  switch (item) {
    case 'Complete':
      return (
        <span
          className="status-style"
          style={{
            color: '#0CBA47',
            backgroundColor: theme === 'dark' ? '#3F5848' : '#D6F8E2',
          }}
        >
          {t('Complete')}
        </span>
      );
    case 'Delete':
      return (
        <span
          className="status-style"
          style={{
            color: '#9C9D9D',
            backgroundColor: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
          }}
        >
          {t('Delete')}
        </span>
      );
    default:
      return 'N/A';
  }
};
