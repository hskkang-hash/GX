type ParsedAddress = {
  province: string | null;
  district: string | null;
  township: string | null;
  street_address: string | null;
};

export const parseGoogleAddress = (place: any): ParsedAddress => {
  const components = place.address_components || [];

  const getComponent = (type: string) =>
    components.find((c: any) => c.types?.includes(type))?.long_name || null;

  // Province / District / Township
  const province = getComponent('administrative_area_level_1');
  const district = getComponent('sublocality_level_1'); // เขต (Khet)
  const township = getComponent('sublocality_level_2'); // แขวง (Khwaeng)

  // Lấy street_number + route
  const street_number = getComponent('street_number');
  const route = getComponent('route');
  const street_address =
    street_number && route
      ? `${street_number} ${route}`
      : street_number || route || null;

  return {
    province,
    district,
    township,
    street_address,
    zonecode: place.postal_code,
    lat: place.lat,
    lng: place.lng,
  };
};
