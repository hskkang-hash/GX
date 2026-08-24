from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from stream_monitors.models import StreamMonitor
from common.constant import MESSAGE_ENUM
from devices.services.camera_service import CameraService
from devices.schemas.schemas_djantic_out import CameraOutSchema, DeviceOutSchema, PackagingSpecificationOutSchema, ProtocolOutSchema
from devices.models import CameraType, Device, DeviceCamera, DeviceProtocol, DeviceStatus, Measurement, PackagingSpecification, PackagingSpecificationDevice, Protocol, PackagingOption, PackagingOptionSpecification, Library
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
import os
import requests
from common.external_http import default_timeout
from common.utils import get_gcs_api_headers

class DeviceService:
    @staticmethod
    @transaction.atomic
    def create(data, request):
        try:
            # Validate required fields
            required_fields = ['name', 'serial_number']
            for field in required_fields:
                if not data.get(field):
                    raise ValidationError(f"{field} is required")

            # find available status
            available_status = DeviceStatus.objects.filter(code='available').first()

            # Create the device
            device = Device.objects.create(
                name=data.get('name'),
                serial_number=data.get('serial_number'),
                status=available_status,
                created_by_id=request.user.id,
                active=data.get('active', True),
                main_type_id=data.get('main_type_id'),
                sub_type=data.get('sub_type',None),
                note=data.get('note', None),
                unit_id=data.get('unit_id', None),
                library_id=data.get('library_id', None),
                terminal_id=data.get('terminal_id', None),
                color=data.get('color', None)
            )

            # Create components with error handling
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
                    success, result = service_class.create_or_update(device=device, data=data[component_name])
                    if not success:
                        return HttpResponse(status=400, content=f"Failed to create {component_name}: {result}")

            # Handle many-to-many relationships
            # DeviceProtocol
            if 'device_protocols' in data and data['device_protocols']:
                # protocol_ids = [protocol['id'] for protocol in data['device_protocols'] if 'id' in protocol]
                for protocol_id in data['device_protocols']:
                    DeviceProtocol.objects.create(
                        device=device,
                        protocol_id=protocol_id,
                        enabled=True
                    )

            # PackagingSpecificationDevice
            if 'packaging_options' in data and data['packaging_options']:
                for option_data in data['packaging_options']:
                    # Create packaging option
                    option = PackagingOption.objects.create(
                        name=option_data.get('name', f'Option {option_data.get("order", 1)}'),
                        order=option_data.get('order', 1)
                    )

                    # Link option to device
                    PackagingSpecificationDevice.objects.create(
                        device=device,
                        option=option
                    )

                    # Add specifications to the option
                    if 'specifications' in option_data and option_data['specifications']:
                        for pack_id in option_data['specifications']:
                            PackagingOptionSpecification.objects.create(
                                option=option,
                                package_id=pack_id
                            )

            # SurveillanceSystems
            if 'surveillance_systems' in data and data['surveillance_systems']:
                # surveillance_ids = [system['id'] for system in data['surveillance_systems'] if 'id' in system]
                for system in data['surveillance_systems']:
                    DeviceCamera.objects.create(
                        device=device,
                        camera_id=system,
                        enabled=True
                    )

            return device

        except Exception as e:
            transaction.set_rollback(True)
            raise ValidationError(f"Failed to create device: {str(e)}")

    @staticmethod
    def event_trigger_gcs_fetch_data():
        try:
            # Trigger GCS to fetch data
            # Get the FlightBird URL from environment variable
            flightbird_url = os.environ.get('FLIGHTBRID_URL', 'http://localhost:5000/')
            # Ensure the URL ends with a slash
            if not flightbird_url.endswith('/'):
                flightbird_url += '/'
            # Create the full API endpoint URL with query parameters
            api_url = f"{flightbird_url}api/v1/groups/fetch"
            # Trigger the API
            headers = get_gcs_api_headers()
            response = requests.get(api_url, headers=headers, timeout=default_timeout())
            if response.status_code == 200:
                print(f"Successfully triggered GCS to fetch data")
                return True
            else:
                print(f"Failed to trigger GCS to fetch data: {response.status_code}")
                return False
        except Exception as e:
            print(f"Failed to trigger GCS to fetch data: {str(e)}")
            return False


    @staticmethod
    @transaction.atomic
    def update(device_id, data):
        """Cập nhật thiết bị và thông tin liên quan"""
        device = Device.objects.get(id=device_id)

        # Cập nhật thông tin cơ bản
        for field in ['name', 'status_id', 'active', 'sub_type', 'note', 'unit_id', 'library_id', 'color']:
            if field in data and data[field] is not None:
                setattr(device, field, data.get(field))
            else:
                setattr(device, field, None)

        # Update main_type
        if 'main_type_id' in data and data['main_type_id'] is not None:
            device.main_type_id = data['main_type_id']

        # Update terminal
        if 'terminal_id' in data and data['terminal_id'] is not None:
            device.terminal_id = data['terminal_id']

        device.save()

        # Cập nhật các component liên quan
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
                    service_class.create_or_update(device=device, data=data[component_name])
                else:
                    # Delete component data if empty value is passed
                    service_class.create_or_update(device=device, data={})

        # Delete components that were not in the data
        for component_name, service_class in components_data.items():
            if component_name not in processed_components:
                service_class.create_or_update(device=device, data={})

        # Handle many-to-many relationships
        # DeviceProtocol
        if 'device_protocols' in data and data['device_protocols'] is not None:
            # protocol_ids = [protocol['id'] for protocol in data['device_protocols'] if 'id' in protocol]
            device.device_protocols.all().delete()
            for protocol_id in data['device_protocols']:
                DeviceProtocol.objects.create(
                    device=device,
                    protocol_id=protocol_id,
                    enabled=True
                )

        # PackagingSpecificationDevice
        if 'packaging_options' in data and data['packaging_options'] is not None:
            # packaging_ids = [packaging['id'] for packaging in data['packaging_options'] if 'id' in packaging]
            device.packaging_specification_device.all().delete()

            for option_data in data['packaging_options']:

                # Create packaging option
                option = PackagingOption.objects.create(
                    name=option_data.get('name', f'Option {option_data.get("order", 1)}'),
                    order=option_data.get('order', 1)
                )

                # Link option to device
                PackagingSpecificationDevice.objects.create(
                    device=device,
                    option=option
                )

                # Add specifications to the option
                if 'specifications' in option_data and option_data['specifications']:
                    for pack_id in option_data['specifications']:
                        PackagingOptionSpecification.objects.create(
                            option=option,
                            package_id=pack_id
                        )

        # SurveillanceSystems
        if 'surveillance_systems' in data and data['surveillance_systems'] is not None:
            # surveillance_ids = [system['id'] for system in data['surveillance_systems'] if 'id' in system]
            device.device_cameras.all().delete()
            for system in data['surveillance_systems']:
                DeviceCamera.objects.create(
                    device=device,
                    camera_id=system,
                    enabled=True
                )

        # update stream monitor by device id
        if StreamMonitor.objects.filter(drone=device).exists():
            stream_monitor = StreamMonitor.objects.get(drone=device)
            stream_monitor.name = device.name
            stream_monitor.code = device.unit_id
            stream_monitor.save()
        return device

    @staticmethod
    def get_complete_data(device, user_units=None, edit=False):
        """Lấy thông tin đầy đủ về thiết bị"""
        # Thông tin cơ bản
        result = DeviceOutSchema.from_queryset(device)

        # Add avatar info if exists
        if device.avatar and device.avatar.deleted is None:
            result["avatar_id"] = device.avatar.id
            result["avatar_url"] = device.avatar.file_url

        # Add file attachments if any
        device_content_type = ContentType.objects.get_for_model(device)
        file_attachments = UserMediaFileItem.objects.filter(
            content_type=device_content_type,
            object_id=device.id
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

        # Thêm measurements trực tiếp
        measurements = {}

        if measurements:
            result["measurements"] = measurements

        # Thông tin các thành phần
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
            component_data = service_class.get_data(device=device, user_units=user_units, edit= not edit)
            if component_data:
                result[component_name] = component_data

        # Add many-to-many relationships
        # Device Protocols
        if device.device_protocols.exists():
            protocols = device.device_protocols.all().order_by('created_on').values('protocol_id')

            result["device_protocols"] = [ProtocolOutSchema.from_queryset(Protocol.objects.get(id=protocol['protocol_id'])) for protocol in protocols]





        # Surveillance Systems
        if device.device_cameras.exists():
            cameras = device.device_cameras.all().order_by('id').values('camera_id')
            data = []

            for camera in cameras:
                if CameraType.objects.filter(id=camera['camera_id']).exists():
                    data.append(CameraService.get_data(CameraType.objects.get(id=camera['camera_id']), None, edit=not edit))
            result["surveillance_systems"] = data

        # Cargo compartments
        # cargo_compartments = CargoCompartmentsService.get_all_data(device, user_units)
        # if cargo_compartments:
        #     result["cargo_compartments"] = cargo_compartments

        return result


    @staticmethod
    @transaction.atomic
    def delete(device_ids):
        try:
            ids = device_ids.split(',')
            devices = Device.objects.filter(id__in=ids)

            # Check if any device is currently in use in delivery operations
            from delivery.models import DeliveryOperationItem
            if DeliveryOperationItem.objects.filter(drone_id__in=ids).exists():
                from common.constant import MESSAGE_ENUM
                raise ValidationError(MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED))

            for device in devices:
                # Delete all related measurements (GenericForeignKey requires manual deletion)
                measurements = device.get_all_measurements()
                for measurement in measurements:
                    measurement.delete()

                # Delete OneToOne related objects BEFORE deleting device
                # (Dependency check middleware requires this even with CASCADE)
                try:
                    if hasattr(device, 'dimensions_and_weight') and device.dimensions_and_weight:
                        device.dimensions_and_weight.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'propulsion_system') and device.propulsion_system:
                        device.propulsion_system.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'flight_performance') and device.flight_performance:
                        device.flight_performance.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'navigation_control') and device.navigation_control:
                        device.navigation_control.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'radio_communication') and device.radio_communication:
                        device.radio_communication.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'telemetry') and device.telemetry:
                        device.telemetry.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'sensor_suite') and device.sensor_suite:
                        device.sensor_suite.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'environmental_specification') and device.environmental_specification:
                        device.environmental_specification.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'safety_feature') and device.safety_feature:
                        device.safety_feature.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'manufacturer_information') and device.manufacturer_information:
                        device.manufacturer_information.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                try:
                    if hasattr(device, 'insurance_information') and device.insurance_information:
                        device.insurance_information.delete(force_policy=HARD_DELETE)
                except Exception:
                    pass

                # Delete ManyToMany and reverse ForeignKey relations
                device.packaging_specification_device.all().delete()
                device.cargo_compartments.all().delete()
                device.device_protocols.all().delete()
                device.device_cameras.all().delete()
                device.device_gnss.all().delete()
                StreamMonitor.objects.filter(drone=device).delete()

                # Finally delete the device (after all dependencies are removed)
                device.delete(force_policy=HARD_DELETE)
            return True

        except Device.DoesNotExist:
            return False
        except ValidationError:
            transaction.set_rollback(True)
            raise
        except Exception as e:
            transaction.set_rollback(True)
            raise ValidationError(f"Failed to delete device: {str(e)}")
