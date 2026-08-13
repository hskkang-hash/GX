"""
Address Service
Utility service for address geocoding and validation using Kakao API
"""

import os
import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class KakaoAddressService:
    """
    Service for address geocoding using Kakao Local API
    Documentation: https://developers.kakao.com/docs/latest/ko/local/dev-guide
    """
    
    @staticmethod
    def geocode_address(address: str) -> Tuple[bool, Optional[Dict]]:
        """
        Geocode address using Kakao Local API search address endpoint.
        
        Args:
            address: Full address string to geocode
            
        Returns:
            Tuple of (success: bool, result: Dict or None)
            
        Example result:
        {
            'full_address': '서울 강남구 테헤란로 427',
            'city_province': '서울특별시',
            'city_county_district': '강남구',
            'ward_town_township': '삼성동',
            'street_address': '테헤란로 427',
            'postal_code': '06159',
            'latitude': 37.5095215,
            'longitude': 127.0638994
        }
        """
        try:
            # Get Kakao API key from environment
            kakao_api_key = os.getenv('KAKAO_API_KEY')
            
            if not kakao_api_key:
                logger.warning('KAKAO_API_KEY environment variable not set. Using fallback method.')
                return False, None
            
            # Kakao Local API endpoint for address search
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            params = {
                'query': address
            }
            
            headers = {
                'Authorization': f'KakaoAK {kakao_api_key}',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                
                if documents:
                    # Get the first (most accurate) result
                    result = documents[0]
                    address_info = result.get('address', {})
                    road_address_info = result.get('road_address', {})
                    
                    # Prefer road address over regular address
                    primary_address = road_address_info if road_address_info else address_info
                    
                    # Parse Korean address format from Kakao API
                    parsed_address = {
                        'full_address': primary_address.get('address_name', address),
                        'city_province': primary_address.get('region_1depth_name'),  # 시/도
                        'city_county_district': primary_address.get('region_2depth_name'),  # 시/군/구
                        'ward_town_township': primary_address.get('region_3depth_name'),  # 동/읍/면
                        'street_address': primary_address.get('address_name', address),
                        'postal_code': None,
                        'latitude': float(result.get('x', 0)) if result.get('x') else None,  # longitude in Kakao
                        'longitude': float(result.get('y', 0)) if result.get('y') else None  # latitude in Kakao
                    }
                    
                    # Note: Kakao API returns x=longitude, y=latitude
                    # We need to swap them for our standard format
                    if parsed_address['latitude'] and parsed_address['longitude']:
                        parsed_address['latitude'], parsed_address['longitude'] = parsed_address['longitude'], parsed_address['latitude']
                    
                    # Try to get postal code from different sources
                    postal_code = (
                        road_address_info.get('zone_no') or 
                        road_address_info.get('postal_code') or
                        address_info.get('zip_code') or 
                        address_info.get('postal_code')
                    )
                    parsed_address['postal_code'] = postal_code
                    
                    # Clean up empty values
                    for key, value in parsed_address.items():
                        if not value or (isinstance(value, str) and value.strip() == ''):
                            parsed_address[key] = None
                    
                    logger.info(f"Successfully geocoded address: {address} -> {parsed_address['full_address']}")
                    return True, parsed_address
                
                else:
                    logger.warning(f'No results found for address: {address}')
                    return False, None
                    
            else:
                logger.error(f'Kakao API request failed: HTTP {response.status_code} - {response.text}')
                if response.status_code == 401:
                    logger.error('Check your KAKAO_API_KEY environment variable')
                return False, None
                
        except requests.RequestException as e:
            logger.error(f'Network error while geocoding address "{address}": {str(e)}')
            return False, None
        except Exception as e:
            logger.error(f'Unexpected error while geocoding address "{address}": {str(e)}')
            return False, None
    
    @staticmethod
    def reverse_geocode(latitude: float, longitude: float) -> Tuple[bool, Optional[Dict]]:
        """
        Reverse geocode coordinates to address using Kakao Local API.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Tuple of (success: bool, result: Dict or None)
        """
        try:
            # Get Kakao API key from environment
            kakao_api_key = os.getenv('KAKAO_API_KEY')
            
            if not kakao_api_key:
                logger.warning('KAKAO_API_KEY environment variable not set.')
                return False, None
            
            # Kakao Local API endpoint for coordinate to address conversion
            url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
            params = {
                'x': longitude,  # longitude
                'y': latitude,  # latitude
                'input_coord': 'WGS84'
            }
            
            headers = {
                'Authorization': f'KakaoAK {kakao_api_key}',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                
                if documents:
                    result = documents[0]
                    address_info = result.get('address', {})
                    road_address_info = result.get('road_address', {})
                    
                    # Prefer road address over regular address
                    primary_address = road_address_info if road_address_info else address_info
                    
                    parsed_address = {
                        'full_address': primary_address.get('address_name', ''),
                        'city_province': primary_address.get('region_1depth_name'),
                        'city_county_district': primary_address.get('region_2depth_name'),
                        'ward_town_township': primary_address.get('region_3depth_name'),
                        'street_address': primary_address.get('address_name', ''),
                        'postal_code': road_address_info.get('zone_no') if road_address_info else None,
                        'latitude': latitude,
                        'longitude': longitude
                    }
                    
                    # Clean up empty values
                    for key, value in parsed_address.items():
                        if not value or (isinstance(value, str) and value.strip() == ''):
                            parsed_address[key] = None
                    
                    logger.info(f"Successfully reverse geocoded coordinates: ({latitude}, {longitude}) -> {parsed_address['full_address']}")
                    return True, parsed_address
                
                else:
                    logger.warning(f'No address found for coordinates: ({latitude}, {longitude})')
                    return False, None
                    
            else:
                logger.error(f'Kakao API reverse geocoding failed: HTTP {response.status_code} - {response.text}')
                return False, None
                
        except Exception as e:
            logger.error(f'Error reverse geocoding coordinates ({latitude}, {longitude}): {str(e)}')
            return False, None

    @staticmethod
    def create_fallback_address(address_string: str, zipcode: str = None) -> Dict:
        """
        Create a fallback address when Kakao API is not available.
        
        Args:
            address_string: Full address string
            zipcode: Optional postal code
            
        Returns:
            Dict with basic address info
        """
        return {
            'full_address': address_string,
            'city_province': None,
            'city_county_district': None,
            'ward_town_township': None,
            'street_address': address_string,
            'postal_code': zipcode,
            'latitude': None,
            'longitude': None
        } 