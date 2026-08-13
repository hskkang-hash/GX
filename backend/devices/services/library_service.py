from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from devices.services.camera_service import CameraService
from devices.schemas.schemas_djantic_out import CameraOutSchema, LibraryOutSchema, PackagingSpecificationOutSchema, ProtocolOutSchema
from devices.models import CameraType, Library, DeviceCamera, DeviceProtocol, Measurement, PackagingSpecification, PackagingSpecificationDevice, Protocol, PackagingOption, PackagingOptionSpecification
from django.contrib.contenttypes.models import ContentType
from core.file_management.models import UserMediaFile, UserMediaFileItem
from safedelete.models import HARD_DELETE
from devices.services.dimensions_service import DimensionsService
from devices.services.propulsion_service import PropulsionSystemService
from devices.services.flight_performance_service import FlightPerformanceService
from devices.services.navigation_service import NavigationControlService
from devices.services.radio_service import RadioCommunicationService
from devices.services.telemetry_service import TelemetryService
from devices.services.sensor_service import SensorSuiteService
from devices.services.packaging_service import PackagingSpecificationService
from devices.services.manufacturer_service import ManufacturerInformationService
from devices.services.insurance_service import InsuranceInformationService
from devices.services.environmental_service import EnvironmentalSpecificationService
from devices.services.safety_service import SafetyFeatureService
from devices.services.cargo_service import CargoCompartmentsService
from core.user.models import UserGroup

class LibraryService:
    @staticmethod
    @transaction.atomic
    def create(data, request):
        # try:
            # Validate required fields
            required_fields = ['name']
            for field in required_fields:
                if not data.get(field):
                    raise ValidationError(f"{field} is required")
            
            # Create the library
            library = Library.objects.create(
                name=data.get('name'),
                status=data.get('status', 'active'),
                created_by_id=request.user.id,
                active=data.get('active', True),
                main_type_id=data.get('main_type_id'),
                sub_type=data.get('sub_type', None),
                note=data.get('note', None)
            )

            # Create components with error handling (similar to device but using library instead)
            components_data = {
                'dimensions': DimensionsService, 
                'propulsion_system': PropulsionSystemService,
                'flight_performance': FlightPerformanceService,
                'navigation_control': NavigationControlService,
                'radio_communication': RadioCommunicationService,
                'telemetry': TelemetryService,
                'sensor_suite': SensorSuiteService,
                'packaging_specification': PackagingSpecificationService,
                'manufacturer_information': ManufacturerInformationService,
                'insurance_information': InsuranceInformationService,
                'environmental_specification': EnvironmentalSpecificationService,
                'safety_feature': SafetyFeatureService,
                'cargo_compartments': CargoCompartmentsService
            }
            
            for component_name, service_class in components_data.items():
                if component_name in data and data[component_name]:
                    success, result = service_class.create_or_update(library=library, data=data[component_name])
                    if not success:
                        return HttpResponse(status=400, content=f"Failed to create {component_name}: {result}")
            
            # Handle many-to-many relationships (similar to device)
            # DeviceProtocol - but for Library (note: may need LibraryProtocol model)
            if 'device_protocols' in data and data['device_protocols']:
                for protocol_id in data['device_protocols']:
                    DeviceProtocol.objects.create(
                        library=library,  # This may need to be changed to library field if separate model is created
                        protocol_id=protocol_id,
                        enabled=True
                    )
            
            # PackagingSpecificationDevice - but for Library
            if 'packaging_options' in data and data['packaging_options']:
                for option_data in data['packaging_options']:
                    option = PackagingOption.objects.create(
                        name=option_data.get('name', f'Option {option_data.get("order", 1)}'),
                        order=option_data.get('order', 1)
                    )
                    
                    PackagingSpecificationDevice.objects.create(
                        library=library,  # This may need to be changed if separate model is created
                        option=option
                    )
                    
                    if 'specifications' in option_data and option_data['specifications']:
                        for pack_id in option_data['specifications']:
                            PackagingOptionSpecification.objects.create(
                                option=option,
                                package_id=pack_id
                            )
            
            # SurveillanceSystems - but for Library
            if 'surveillance_systems' in data and data['surveillance_systems']:
                for system in data['surveillance_systems']:
                    DeviceCamera.objects.create(
                        library=library,  # This may need to be changed if separate model is created
                        camera_id=system,
                        enabled=True
                    )
            return library

        # except Exception as e:
        #     transaction.set_rollback(True)
        #     raise ValidationError(f"Failed to create library: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update(library_id, data):
        """Cập nhật library và thông tin liên quan"""
        library = Library.objects.get(id=library_id)
        
        # Cập nhật thông tin cơ bản
        for field in ['name', 'status', 'active', 'sub_type', 'note']:
            if field in data and data[field] is not None:
                setattr(library, field, data.get(field))
            else:
                setattr(library, field, None)
                
        # Update main_type
        if 'main_type_id' in data and data['main_type_id'] is not None:
            library.main_type_id = data['main_type_id']
            
        library.save()
        
        # Cập nhật các component liên quan (same as device)
        components_data = {
            'dimensions': DimensionsService, 
            'propulsion_system': PropulsionSystemService,
            'flight_performance': FlightPerformanceService,
            'navigation_control': NavigationControlService,
            'radio_communication': RadioCommunicationService,
            'telemetry': TelemetryService,
            'sensor_suite': SensorSuiteService,
            'manufacturer_information': ManufacturerInformationService,
            'insurance_information': InsuranceInformationService,
            'environmental_specification': EnvironmentalSpecificationService,
            'safety_feature': SafetyFeatureService,
            'cargo_compartments': CargoCompartmentsService
        }
        
        processed_components = set()
        
        # Handle components that are in the data
        for component_name, service_class in components_data.items():
            if component_name in data:
                processed_components.add(component_name)
                if data[component_name]:
                    service_class.create_or_update(library=library, data=data[component_name])
                else:
                    service_class.create_or_update(library=library, data={})
        
        # Delete components that were not in the data
        for component_name, service_class in components_data.items():
            if component_name not in processed_components:
                service_class.create_or_update(library=library, data={})
                
        # Handle many-to-many relationships (similar to device)
        if 'device_protocols' in data and data['device_protocols'] is not None:
            library.library_protocols.all().delete()
            for protocol_id in data['device_protocols']:
                DeviceProtocol.objects.create(
                    library=library,  # May need adjustment
                    protocol_id=protocol_id,
                    enabled=True
                )
     
        if 'packaging_options' in data and data['packaging_options'] is not None:
            library.packaging_specification_library.all().delete()
            for option_data in data['packaging_options']:
                option = PackagingOption.objects.create(
                    name=option_data.get('name', f'Option {option_data.get("order", 1)}'),
                    order=option_data.get('order', 1)
                )
                
                PackagingSpecificationDevice.objects.create(
                    library=library,  # May need adjustment
                    option=option
                )
                
                if 'specifications' in option_data and option_data['specifications']:
                    for pack_id in option_data['specifications']:
                        PackagingOptionSpecification.objects.create(
                            option=option,
                            package_id=pack_id
                        )
        
        if 'surveillance_systems' in data and data['surveillance_systems'] is not None:
            library.library_cameras.all().delete()
            for system in data['surveillance_systems']:
                DeviceCamera.objects.create( 
                    library=library,  # May need adjustment
                    camera_id=system,
                    enabled=True
                )
        
        return library
        
    @staticmethod
    def get_complete_data(library, user_units=None, edit=False): 
        """Lấy thông tin đầy đủ về library"""
        # Thông tin cơ bản
        result = LibraryOutSchema.from_queryset(library)
        
        # Add avatar info if exists
        if library.avatar and library.avatar.deleted is None:
            result["avatar_id"] = library.avatar.id
            result["avatar_url"] = library.avatar.file_url
        
        # Add file attachments if any
        library_content_type = ContentType.objects.get_for_model(library)
        file_attachments = UserMediaFileItem.objects.filter(
            content_type=library_content_type,
            object_id=library.id
        ).select_related('user_media_file')
        
        if file_attachments.exists():
            result["file_attachments"] = []
            for attachment in file_attachments:
                result["file_attachments"].append({
                    "id": attachment.user_media_file.id,
                    "file_name": attachment.user_media_file.file_name,
                    "file_url": attachment.user_media_file.file_url,
                    "file_type": attachment.user_media_file.file_type,
                    "file_size": attachment.user_media_file.file_size,
                    "created_on": attachment.user_media_file.created_on
                })
        
        # Thông tin các thành phần (same as device)
        components_data = {
            'dimensions': DimensionsService,
            'propulsion_system': PropulsionSystemService,
            'flight_performance': FlightPerformanceService,
            'navigation_control': NavigationControlService,
            'radio_communication': RadioCommunicationService,
            'telemetry': TelemetryService,
            'sensor_suite': SensorSuiteService,
            'packaging_specification': PackagingSpecificationService,
            'manufacturer_information': ManufacturerInformationService,
            'insurance_information': InsuranceInformationService,
            'environmental_specification': EnvironmentalSpecificationService,
            'safety_feature': SafetyFeatureService,
            'cargo_compartments': CargoCompartmentsService
        }
        
        for component_name, service_class in components_data.items():
            component_data = service_class.get_data(library=library, user_units=user_units, edit=not edit)
            if component_data:
                result[component_name] = component_data
        
        # Add many-to-many relationships (same as device)
        if library.library_protocols.exists():
            protocols = library.library_protocols.all().order_by('created_on').values('protocol_id')
            result["device_protocols"] = [ProtocolOutSchema.from_queryset(Protocol.objects.get(id=protocol['protocol_id'])) for protocol in protocols]
            
        if library.library_cameras.exists():
            cameras = library.library_cameras.all().order_by('id').values('camera_id')
            data = []
            for camera in cameras:
                data.append(CameraService.get_data(CameraType._base_manager.get(id=camera['camera_id']), None, edit=not edit))
            result["surveillance_systems"] = data
            
        
        return result

    @staticmethod
    @transaction.atomic
    def delete(library_id):
        try:
            library = Library.objects.get(id=library_id)
            
            # Delete all related measurements
            measurements = library.get_all_measurements()
            for measurement in measurements:
                measurement.delete()
                
            # Finally delete the library
            library.delete(force_policy=HARD_DELETE)
            return True
            
        except Library.DoesNotExist:
            return False
        except Exception as e:
            transaction.set_rollback(True)
            raise ValidationError(f"Failed to delete library: {str(e)}")

    @staticmethod
    def copy_from_library_to_device(library, device_data):
        """Copy template data from library to create a new device"""
        try:
            # Get complete library data
            library_data = LibraryService.get_complete_data(library)
            
            # Merge library data with device-specific data
            # Device-specific data takes precedence
            merged_data = {}
            
            # Copy all library data except basic fields that should come from device_data
            exclude_fields = ['id', 'name', 'serial_number', 'unit_id', 'created_on', 'updated_at']
            
            for key, value in library_data.items():
                if key not in exclude_fields and key not in device_data:
                    merged_data[key] = value
            
            # Add device-specific data
            merged_data.update(device_data)
            
            return merged_data
            
        except Exception as e:
            raise ValidationError(f"Failed to copy from library: {str(e)}") 