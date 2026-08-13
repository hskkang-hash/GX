"""
Management command to initialize data for Anyang drone delivery integration.
Creates item types, packages, terminals and other necessary data.

Usage:
    python manage.py init_anyang_data
    python manage.py init_anyang_data --reset
    python manage.py init_anyang_data --with-address
    
For address geocoding (--with-address):
    1. Get Kakao REST API Key from: https://developers.kakao.com/console/app
    2. Set environment variable: export KAKAO_API_KEY="your_api_key_here"
    3. Run with --with-address flag
    
If KAKAO_API_KEY is not set, it will fallback to OpenStreetMap Nominatim API.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import requests
import time

from orders.models import OrderItemType, OrderStatus
from devices.models import PackagingSpecification
from delivery.models import DeliveryStatus
from terminals.models import Terminal, TerminalType
from core.multilanguage.request_handlers import process_multilanguage_request, create_model_with_translations, update_model_with_translations, get_model_with_translations
from core.user.models import CoreUser, UserGroup

class Command(BaseCommand):
    help = 'Initialize data for Anyang drone delivery integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing data before creating new data',
        )
        parser.add_argument(
            '--with-address',
            action='store_true',
            help='Fetch addresses from coordinates using Kakao Local API (requires KAKAO_API_KEY env var)',
        )
        parser.add_argument(
            '--force-postal-code',
            action='store_true',
            help='Use additional API calls to ensure postal code is retrieved for all addresses',
        )
        parser.add_argument(
            '--group',
            type=str,
            help='Group code to use for creating data',
        )
    def get_address_from_coordinates(self, lat, lng):
        """
        Get address from latitude and longitude using Kakao Local API reverse geocoding
        Documentation: https://developers.kakao.com/docs/latest/ko/local/dev-guide#coord-to-address
        """
        try:
            # Kakao Local API endpoint for coordinate to address conversion
            url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
            params = {
                'x': lng,  # longitude
                'y': lat,  # latitude
                'input_coord': 'WGS84'  # Input coordinate system
            }
            
            # You need to set KAKAO_API_KEY in your environment variables
            # Get it from https://developers.kakao.com/console/app
            import os
            kakao_api_key = os.getenv('KAKAO_API_KEY')
            
            if not kakao_api_key:
                self.stdout.write(f'  ⚠ KAKAO_API_KEY environment variable not set. Using fallback method.')
                return 
            
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
                    address = result.get('address', {})
                    road_address = result.get('road_address', {})
                    
                    # Parse Korean address format from Kakao API
                    address_info = {
                        'city_province': address.get('region_1depth_name'),  # 시/도
                        'city_county_district': address.get('region_2depth_name'),  # 시/군/구
                        'ward_town_township': address.get('region_3depth_name'),  # 동/읍/면
                        'street_address': address.get('address_name', ''),
                        'postal_code': None,
                        'full_address': address.get('address_name', '')
                    }
                    
                    # Try to get postal_code from multiple sources (priority order)
                    postal_code = None
                    if road_address:
                        # 1. Road address zone_no (most accurate)
                        postal_code = road_address.get('zone_no') or road_address.get('postal_code')
                        if road_address.get('address_name'):
                            address_info['street_address'] = road_address.get('address_name', '')
                            address_info['full_address'] = road_address.get('address_name', '')
                    
                    if not postal_code:
                        # 2. Regular address zone_no
                        postal_code = address.get('zip_code') or address.get('postal_code')
                    
                    if not postal_code:
                        # 3. Try other postal code fields
                        postal_code = result.get('postal_code') or result.get('zip_code')
                    
                    address_info['postal_code'] = postal_code
                    
                    # Log if postal_code is missing for debugging
                    if not postal_code:
                        self.stdout.write(f'  ⚠ No postal code found for coordinates ({lat}, {lng})')
                        # Debug: print available fields
                        self.stdout.write(f'    Available fields - Address: {list(address.keys())}')
                        if road_address:
                            self.stdout.write(f'    Available fields - Road Address: {list(road_address.keys())}')
                    
                    # Clean up empty values
                    for key, value in address_info.items():
                        if not value or value == ' ':
                            address_info[key] = None
                            
                    return address_info
                else:
                    self.stdout.write(f'  ⚠ No address found for coordinates ({lat}, {lng})')
                    return None
                
            else:
                self.stdout.write(f'  ⚠ Failed to get address for coordinates ({lat}, {lng}): HTTP {response.status_code} {response.text}')
                if response.status_code == 401:
                    self.stdout.write(f'    Check your KAKAO_API_KEY environment variable')
                return None
                
        except requests.RequestException as e:
            self.stdout.write(f'  ⚠ Error fetching address for coordinates ({lat}, {lng}): {str(e)}')
            return None
        except Exception as e:
            self.stdout.write(f'  ⚠ Unexpected error getting address for coordinates ({lat}, {lng}): {str(e)}')
            return None

    def get_address_from_coordinates_fallback(self, lat, lng):
        """
        Fallback method using Nominatim when Kakao API is not available
        """
        try:
            # Nominatim API endpoint (fallback)
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'ko,en'
            }
            
            headers = {
                'User-Agent': 'GuardianX-Anyang-Integration/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                # Parse Korean address format
                address_info = {
                    'city_province': address.get('province') or address.get('state') or address.get('city'),
                    'city_county_district': address.get('city') or address.get('county') or address.get('district'),
                    'ward_town_township': address.get('town') or address.get('village') or address.get('suburb'),
                    'street_address': f"{address.get('road', '')} {address.get('house_number', '')}".strip(),
                    'postal_code': address.get('postcode') or address.get('postal_code'),
                    'full_address': data.get('display_name', '')
                }
                
                # Log if postal_code is missing for debugging
                if not address_info['postal_code']:
                    self.stdout.write(f'  ⚠ No postal code found for coordinates ({lat}, {lng}) using fallback API')
                    self.stdout.write(f'    Available fields: {list(address.keys())}')
                
                # Clean up empty values
                for key, value in address_info.items():
                    if not value or value == ' ':
                        address_info[key] = None
                        
                return address_info
            else:
                return None
                
        except Exception:
            return None

    @transaction.atomic
    def handle(self, *args, **options):
        user = None  # Set current user if needed
        if options.get('group', False):
            user = CoreUser.objects.filter(userprofilelink__group__code=options.get('group')).first()
        else:
            if UserGroup.objects.filter(code='anyang').first():
                user = CoreUser.objects.filter(userprofilelink__group__code='anyang').first()
         
        # Check for API key when using --with-address
        if options.get('with_address', False):
            import os
            if not os.getenv('KAKAO_API_KEY'):
                self.stdout.write(self.style.WARNING('⚠ KAKAO_API_KEY not found in environment variables'))
                self.stdout.write('   Will use OpenStreetMap Nominatim API as fallback')
                self.stdout.write('   For better Korean address results, get API key from:')
                self.stdout.write('   https://developers.kakao.com/console/app')
            else:
                self.stdout.write(self.style.SUCCESS('✓ Using Kakao Local API for address geocoding'))
        
        if options['reset']:
            self.stdout.write('Deleting existing data...')
            OrderItemType.objects.all().delete()

        self.stdout.write('Creating Order Item Types...')
        self.create_order_item_types(user)


        self.stdout.write('Creating Terminals...')
        self.create_terminals(user, options.get('with_address', False))

        self.stdout.write(
            self.style.SUCCESS('Successfully initialized Anyang integration data!')
        )

    def create_order_item_types(self, user):
        """Create item types for Anyang API integration with multilanguage support"""
        item_types_data = [
            {
                'name': {
                    'en': 'Agricultural',
                    'ko': '농산물'
                },
                'code': '1',
            },
            {
                'name': {
                    'en': 'Pet supplies',
                    'ko': '반려동물용품'
                },
                'code': '989',
            },
            {
                'name': {
                    'en': 'Beverages',
                    'ko': '음료'
                },
                'code': '992',
            },
            {
                'name': {
                    'en': 'Food',
                    'ko': '음식'
                },
                'code': '997',
            },
            {
                'name': {
                    'en': 'Cosmetics',
                    'ko': '화장품'
                },
                'code': '16',
            },
            {
                'name': {
                    'en': 'Household',
                    'ko': '생활용품'
                },
                'code': '990',
            },
            {
                'name': {
                    'en': 'Snacks',
                    'ko': '간식'
                },
                'code': '994',
            },
            {
                'name': {
                    'en': 'Others',
                    'ko': '기타'
                },
                'code': '999',
            },
        ]
        for item_data in item_types_data:
            # Check if object exists by code (unique identifier)
            existing_obj = OrderItemType.objects.filter(code=item_data["code"]).first()
            
            if existing_obj:
                # Add created_by and modified_by if not already set
                item_data["created_by"] = user
                item_data["modified_by"] = user
                item_data["is_active"] = True
                update_model_with_translations(existing_obj, item_data)
                self.stdout.write(f'  ✓ Updated item type: {existing_obj.name}')
            else:
                item_data["created_by"] = user
                item_data["modified_by"] = user
                item_data["is_active"] = True
                created_obj = create_model_with_translations(OrderItemType, item_data)
                self.stdout.write(f'  ✓ Created item type: {created_obj.name}')



    def create_terminals(self, user, with_address=False):
        """Create terminals for Anyang drone delivery integration"""
        
        # Get terminal types
        terminal_type = TerminalType.objects.filter(code='DELIVERY_HUB').first()
        docking_station_type = TerminalType.objects.filter(code='DOCKING_STATION').first()
        
        if not terminal_type:
            self.stdout.write(self.style.ERROR('TERMINAL type not found. Please run init_base_device_data.py first'))
            return
            
        if not docking_station_type:
            self.stdout.write(self.style.ERROR('DOCKING_STATION type not found. Please run init_base_device_data.py first'))
            return

        # Base Terminals (TERMINAL type)
        base_terminals_data = [
            {
                'name': 'Anyang Pavilion (안양파빌리온)',
                'code': '41100001000',
                'latitude': 37.419639,
                'longitude': 126.946389,
                'terminal_types': [terminal_type],
                'time_stops': "0 mins",
            },
            {
                'name': 'Hogye Gymnasium (호계체육관)', 
                'code': '41100002000',
                'latitude': 37.380278,
                'longitude': 126.946507,
                'terminal_types': [terminal_type],
                'time_stops': "0 mins",
            },
            {
                'name': 'Public Site (공공공지)', 
                'code': '41100003000',
                'latitude': 37.378611,
                'longitude': 126.905000,
                'terminal_types': [terminal_type],
                'time_stops': "0 mins",
            }
        ]

        # Delivery Points (DOCKING_STATION type)
        delivery_points_data = [
            # Anyang Pavilion delivery points
            {
                'name': 'Bulseongsa (불성사)',
                'code': '41100001001',
                'latitude': 37.432245,
                'longitude': 126.960051,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Yeombulam (염불암)',
                'code': '41100001002', 
                'latitude': 37.428566,
                'longitude': 126.934468,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Sammaksa (삼막사)',
                'code': '41100001003',
                'latitude': 37.434444,
                'longitude': 126.935278,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': '삼막애견공원',
                'code': '41100001004',
                'latitude': 37.428889,
                'longitude': 126.915000,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            # Hogye Sports Park delivery points
            {
                'name': 'Pyeongchon Freedom Park (평촌자유공원)',
                'code': '41100002001',
                'latitude': 37.380833,
                'longitude': 126.962778,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Pyeongchon Central Park (평촌중앙공원)', 
                'code': '41100002002',
                'latitude': 37.390000,
                'longitude': 126.959722,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Hakun Park (학운공원)',
                'code': '41100002003',
                'latitude': 37.398889,
                'longitude': 126.947500,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': '안양종합운동장)',
                'code': '41100002004',
                'latitude': 37.404167,
                'longitude': 126.947778,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },

            # Public Site delivery points
            {
                'name': 'Byeonggogan Citizen Park (병곤시민공원)',
                'code': '41100003001',
                'latitude': 37.384444,
                'longitude': 126.908611,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Samdeok Park (삼덕공원)',
                'code': '41100003002',
                'latitude': 37.398333,
                'longitude': 126.917500,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Chunghun Park (충훈공원)',
                'code': '41100003003',
                'latitude': 37.410556,
                'longitude': 126.901389,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            },
            {
                'name': 'Seoksu Sports Park (석수체육공원)',
                'code': '41100003004',
                'latitude': 37.422500,
                'longitude': 126.901944,
                'terminal_types': [docking_station_type],
                'time_stops': "5 mins",
            }
        ]

        # Create base terminals first
        for terminal_data in base_terminals_data:
            existing_obj = Terminal.objects.filter(code=terminal_data['code']).first()
            
            # Get address from coordinates if requested
            address_info = {}
            if with_address:
                self.stdout.write(f'  🌐 Fetching address for {terminal_data["name"]}...')
                address_info = self.get_address_from_coordinates(
                    terminal_data['latitude'], 
                    terminal_data['longitude']
                ) or {}
                # Add delay to respect API rate limits
                time.sleep(1)
            
            if existing_obj:
                existing_obj.name = terminal_data['name']
                existing_obj.latitude = str(terminal_data['latitude'])
                existing_obj.longitude = str(terminal_data['longitude'])
                existing_obj.active = True
                existing_obj.note = 'Anyang integration - Base terminal'
                
                # Update address fields if available
                if address_info:
                    existing_obj.city_province = address_info.get('city_province')
                    existing_obj.city_county_district = address_info.get('city_county_district')
                    existing_obj.ward_town_township = address_info.get('ward_town_township')
                    existing_obj.street_address = address_info.get('street_address')
                    existing_obj.postal_code = address_info.get('postal_code')
                    if address_info.get('full_address'):
                        existing_obj.address_note = f"Full address: {address_info['full_address']}"
                
                if user:
                    existing_obj.modified_by = user
                    existing_obj.group = user.userprofilelink.group
                
                # Update terminal types
                existing_obj.terminal_types.set(terminal_data['terminal_types'])
                
                existing_obj.set_measurement('time_stops', terminal_data['time_stops'])
                existing_obj.save()
                self.stdout.write(f'  ✓ Updated base terminal: {existing_obj.name}')
            else:
                terminal_info = {
                    'name': terminal_data['name'],
                    'code': terminal_data['code'],
                    'latitude': str(terminal_data['latitude']),
                    'longitude': str(terminal_data['longitude']),
                    'active': True,
                    'note': 'Anyang integration - Base terminal'
                }
                
                # Add address fields if available
                if address_info:
                    terminal_info.update({
                        'city_province': address_info.get('city_province'),
                        'city_county_district': address_info.get('city_county_district'),
                        'ward_town_township': address_info.get('ward_town_township'),
                        'street_address': address_info.get('street_address'),
                        'postal_code': address_info.get('postal_code'),
                    })
                    if address_info.get('full_address'):
                        terminal_info['address_note'] = f"Full address: {address_info['full_address']}"
                
                if user:
                    terminal_info['created_by'] = user
                    terminal_info['modified_by'] = user
                    terminal_info['group'] = user.userprofilelink.group
                terminal = Terminal.objects.create(**terminal_info)
                
                # Set terminal types
                terminal.terminal_types.set(terminal_data['terminal_types'])
                
                measurement_fields = [
                    'time_stops'
                ]
                for field in measurement_fields:
                    if field in terminal_data and terminal_data[field]:
                        terminal.set_measurement(field, terminal_data[field])
                    else:
                        terminal.measurements.filter(measurement_type=field).delete()
                self.stdout.write(f'  ✓ Created base terminal: {terminal.name}')

        # Create delivery points
        for delivery_data in delivery_points_data:
            existing_obj = Terminal.objects.filter(code=delivery_data['code']).first()
            
            # Get address from coordinates if requested
            address_info = {}
            if with_address:
                self.stdout.write(f'  🌐 Fetching address for {delivery_data["name"]}...')
                address_info = self.get_address_from_coordinates(
                    delivery_data['latitude'], 
                    delivery_data['longitude']
                ) or {}
                # Add delay to respect API rate limits
                time.sleep(1)
            
            if existing_obj:
                existing_obj.name = delivery_data['name']
                existing_obj.latitude = str(delivery_data['latitude'])
                existing_obj.longitude = str(delivery_data['longitude'])
                existing_obj.active = True
                existing_obj.note = f'Anyang Delivery point'
                
                # Update address fields if available
                if address_info:
                    existing_obj.city_province = address_info.get('city_province')
                    existing_obj.city_county_district = address_info.get('city_county_district')
                    existing_obj.ward_town_township = address_info.get('ward_town_township')
                    existing_obj.street_address = address_info.get('street_address')
                    existing_obj.postal_code = address_info.get('postal_code')
                    if address_info.get('full_address'):
                        existing_obj.address_note = f"Full address: {address_info['full_address']}"
                
                if user:
                    existing_obj.modified_by = user
                    existing_obj.group = user.userprofilelink.group
                # Update terminal types
                existing_obj.terminal_types.set(delivery_data['terminal_types'])
                
                existing_obj.set_measurement('time_stops', delivery_data['time_stops'])
                existing_obj.save()
                self.stdout.write(f'  ✓ Updated delivery point: {existing_obj.name}')
            else:
                delivery_info = {
                    'name': delivery_data['name'],
                    'code': delivery_data['code'],
                    'latitude': str(delivery_data['latitude']),
                    'longitude': str(delivery_data['longitude']),
                    'active': True,
                    'note': f'Anyang Delivery point'
                }
                
                # Add address fields if available
                if address_info:
                    delivery_info.update({
                        'city_province': address_info.get('city_province'),
                        'city_county_district': address_info.get('city_county_district'),
                        'ward_town_township': address_info.get('ward_town_township'),
                        'street_address': address_info.get('street_address'),
                        'postal_code': address_info.get('postal_code'),
                    })
                    if address_info.get('full_address'):
                        delivery_info['address_note'] = f"Full address: {address_info['full_address']}"
                
                if user:
                    delivery_info['created_by'] = user
                    delivery_info['modified_by'] = user
                    delivery_info['group'] = user.userprofilelink.group
                terminal = Terminal.objects.create(**delivery_info)
                
                # Set terminal types
                terminal.terminal_types.set(delivery_data['terminal_types'])
                
                # Set time_stops measurement
                terminal.set_measurement('time_stops', delivery_data['time_stops'])
                self.stdout.write(f'  ✓ Created delivery point: {terminal.name}')

        self.stdout.write('Terminals created successfully!')
        
        if with_address:
            self.stdout.write('📍 Address information has been fetched and saved for all terminals')
        else:
            self.stdout.write('💡 To include address information, run with --with-address flag')
            self.stdout.write('   Set KAKAO_API_KEY environment variable for best results')
            self.stdout.write('   Get your API key from: https://developers.kakao.com/console/app') 