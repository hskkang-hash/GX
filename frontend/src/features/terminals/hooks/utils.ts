interface KakaoAddressData {
  building_name?: string;
  main_building_no?: string;
  sub_building_no?: string;
  road_name?: string;
}

interface AddressParts {
  city_province: string;
  city_county_district: string;
  ward_town_township?: string;
  street_address: string;
}

export const formatKoreanStreetAddress = (data?: KakaoAddressData): string => {
  const { road_name, main_building_no, sub_building_no, building_name } = data;

  const buildingNo = sub_building_no?.trim()
    ? `${main_building_no}-${sub_building_no}`
    : main_building_no;

  const addressParts = [road_name, buildingNo, building_name].filter(Boolean);
  const fullAddress = addressParts.join(' ');

  return fullAddress;
};

export const formatFullAddressFromFields = ({
  city_province,
  city_county_district,
  ward_town_township,
  street_address,
}: AddressParts): string => {
  return [
    city_province,
    city_county_district,
    ward_town_township,
    street_address,
  ]
    .filter(Boolean)
    .join(' ');
};

export const formatFullAddressFromFieldsGoogle = ({
  city_province,
  city_county_district,
  ward_town_township,
  street_address,
}: AddressParts): string => {
  return [
    street_address,
    ward_town_township,
    city_county_district,
    city_province,
  ]
    .filter(Boolean)
    .join(', ');
};

export const formatFullAddressFromFields2 = ({
  city_province,
  city_county_district,
  ward_town_township,
  street_address,
}: AddressParts): string => {
  return [
    city_province,
    city_county_district,
    ward_town_township,
    street_address,
  ]
    .filter(Boolean)
    .join(', ');
};
