from devices.schemas.schemas_djantic_out import PackagingSpecificationOutSchema
from devices.models import PackagingSpecification, Measurement, PackagingOption, PackagingOptionSpecification
from ninja.errors import ValidationError
from common.constant import MESSAGE_ENUM, get_message
from devices.utils import convert_unit

class PackagingSpecificationService:
    @staticmethod
    def _parse_dimensions_to_mm(dimensions_string):
        """Parse dimensions string và chuyển về mm, trả về (length, width, height)"""
        try:
            from devices.utils import process_measurement_string
            temp_obj = type('obj', (object,), {'MEASUREMENT_TYPES': {'dimensions': {'type': 'dimensions', 'default_unit': 'mm'}}})()
            measurement = process_measurement_string(temp_obj, 'dimensions', dimensions_string)
            
            if measurement and measurement.data:
                data = measurement.data
                length = float(data.get('length', 0))
                width = float(data.get('width', 0))
                height = float(data.get('height', 0))
                unit = data.get('unit', 'mm')
                
                # Chuyển đổi về mm (convert_unit tự động check nếu unit giống nhau)
                length = float(convert_unit(length, unit, 'mm'))
                width = float(convert_unit(width, unit, 'mm'))
                height = float(convert_unit(height, unit, 'mm'))
                
                return length, width, height
        except Exception as e:
            pass
        return 0.0, 0.0, 0.0
    
    @staticmethod
    def _parse_weight_to_kg(weight_string):
        """Parse weight string và chuyển về kg"""
        try:
            from devices.utils import process_measurement_string
            temp_obj = type('obj', (object,), {'MEASUREMENT_TYPES': {'max_weight': {'type': 'simple', 'default_unit': 'kg'}}})()
            measurement = process_measurement_string(temp_obj, 'max_weight', weight_string)
            
            if measurement and measurement.data:
                data = measurement.data
                value = float(data.get('value', 0))
                unit = data.get('unit', 'kg')
                
                # Chuyển đổi về kg (convert_unit tự động check nếu unit giống nhau)
                value = float(convert_unit(value, unit, 'kg'))
                
                return value
        except Exception as e:
            pass
        return 0.0

    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin đóng gói"""
        # Chỉ validate khi có data (không phải data rỗng để xóa)
        if data and len(data) > 0:
            # Kiểm tra dimensions và max_weight trước khi khởi tạo
            if 'dimensions' not in data or not data['dimensions']:
                raise ValidationError(get_message(MESSAGE_ENUM.PACKAGING_DIMENSIONS_REQUIRED))
            
            if 'max_weight' not in data or not data['max_weight']:
                raise ValidationError(get_message(MESSAGE_ENUM.PACKAGING_MAX_WEIGHT_REQUIRED))
            
            # Parse dimensions và max_weight của packaging
            pkg_length, pkg_width, pkg_height = PackagingSpecificationService._parse_dimensions_to_mm(data['dimensions'])
            pkg_weight = PackagingSpecificationService._parse_weight_to_kg(data['max_weight'])
            
            if not all([pkg_length > 0, pkg_width > 0, pkg_height > 0]):
                raise ValidationError(get_message(MESSAGE_ENUM.INVALID_PACKAGING_DIMENSIONS_FORMAT))
            
            if pkg_weight <= 0:
                raise ValidationError(get_message(MESSAGE_ENUM.INVALID_PACKAGING_MAX_WEIGHT_FORMAT))
            
            # Kiểm tra với frame_size và payload_capacity của device/library
            target = device if device else library
            if target and hasattr(target, 'dimensions_and_weight') and target.dimensions_and_weight:
                dimensions_weight = target.dimensions_and_weight
                
                # Lấy frame_size từ DimensionsAndWeight
                frame_size_measurement = dimensions_weight.measurements.filter(measurement_type='frame_size').first()
                if frame_size_measurement:
                    frame_data = frame_size_measurement.data
                    frame_length = float(frame_data.get('length', 0))
                    frame_width = float(frame_data.get('width', 0))
                    frame_height = float(frame_data.get('height', 0))
                    frame_unit = frame_data.get('unit', 'mm')
                    
                    # Chuyển về mm (convert_unit tự động check nếu unit giống nhau)
                    frame_length = float(convert_unit(frame_length, frame_unit, 'mm'))
                    frame_width = float(convert_unit(frame_width, frame_unit, 'mm'))
                    frame_height = float(convert_unit(frame_height, frame_unit, 'mm'))
                    
                    # So sánh dimensions: package phải <= frame_size
                    if frame_length > 0 and frame_width > 0 and frame_height > 0:
                        if not (pkg_length <= frame_length and pkg_width <= frame_width and pkg_height <= frame_height):
                            raise ValidationError(get_message(MESSAGE_ENUM.DIMENSION_NOT_FIT))
                
                # Lấy payload_capacity từ DimensionsAndWeight
                payload_measurement = dimensions_weight.measurements.filter(measurement_type='payload_capacity').first()
                if payload_measurement:
                    payload_data = payload_measurement.data
                    payload_value = float(payload_data.get('value', 0))
                    payload_unit = payload_data.get('unit', 'kg')
                    
                    # Chuyển về kg (convert_unit tự động check nếu unit giống nhau)
                    payload_value = float(convert_unit(payload_value, payload_unit, 'kg'))
                    
                    # So sánh weight: max_weight phải <= payload_capacity
                    if payload_value > 0:
                        if pkg_weight > payload_value:
                            raise ValidationError(get_message(MESSAGE_ENUM.INSUFFICIENT_WEIGHT_CAPACITY))
        
        # Sau khi kiểm tra xong, tiến hành tạo hoặc cập nhật
        if device:
            packaging, created = PackagingSpecification._base_manager.get_or_create(device=device, library=library)
        elif library:
            packaging, created = PackagingSpecification._base_manager.get_or_create(library=library, device=device)
        
        # Cập nhật thông tin text
        if 'package_type' in data:
            packaging.package_type = data.get('package_type',None)
        else:
            packaging.package_type = None
        packaging.save()
        
        # Cập nhật measurements
        for field in ['dimensions','max_weight']:
            if field in data and data[field]:
                # Xóa measurement cũ nếu có
                packaging.measurements.filter(measurement_type=field).delete()
                # Tạo measurement mới
                Measurement.create_from_string(packaging, field, data[field])
            else:
                packaging.measurements.filter(measurement_type=field).delete()
        
        return True, packaging

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            # Lấy tất cả package options của device
            if device:
                package_devices = device.packaging_specification_device.all().select_related('option').order_by('option__order')
            elif library:
                package_devices = library.packaging_specification_library.all().select_related('option').order_by('option__order')
            
            if not package_devices.exists():
                return []
                
            result = []
            for pkg_device in package_devices:
                option = pkg_device.option
                option_data = {
                    'id': option.id,
                    'name': option.name,
                    'order': option.order,
                    'created_on': option.created_on,
                    'updated_at': option.modified_on,
                    'specifications': []
                }
                
                # Lấy tất cả specifications của option
                specifications = PackagingOptionSpecification.objects.filter(
                    option=option
                ).select_related('package').order_by('id')
                
                for spec_rel in specifications:
                    spec = spec_rel.package
                    spec_data = {
                        'id': spec.id,
                        'name': spec.name,
                        'code': spec.code,
                        'created_on': spec.created_on,
                        'updated_at': spec.modified_on
                    }
                    
                    # Lấy measurement data
                    for field in ['dimensions', 'max_weight']:
                        measurement = spec.measurements.filter(measurement_type=field).first()
                        if measurement and edit:
                            spec_data[field] = measurement.get_formatted_value(user_units)
                        elif measurement:
                            spec_data[field] = measurement.get_converted_data(user_units)
                    
                    option_data['specifications'].append(spec_data)
                
                result.append(option_data)
                
            return result
        except Exception as e:
            print(f"Error getting packaging options: {str(e)}")
            return []

    @staticmethod
    def get_list_specification_data(specifications, user_units=None):
        """Lấy danh sách tất cả các specification"""
        # Ensure specifications is a QuerySet with prefetched measurements
        if hasattr(specifications, 'prefetch_related'):
            specifications = specifications.prefetch_related('measurements')
        data_list = []
        for package in specifications:
            package_data = PackagingSpecificationOutSchema.from_queryset(package)
            
            # Thêm các trường measurement - sử dụng prefetched data
            package_details = package.name
            for field in ['dimensions', 'max_weight']:
                # Use prefetched measurements if available
                if hasattr(package, '_prefetched_objects_cache') and 'measurements' in package._prefetched_objects_cache:
                    measurements = package._prefetched_objects_cache['measurements']
                    m = next((m for m in measurements if m.measurement_type == field), None)
                else:
                    m = package.measurements.filter(measurement_type=field).first()
                
                if m:
                    package_data[field] = m.get_formatted_value(user_units)
                    package_details += ' - ' + str(m.get_formatted_value(user_units))
            package_data['details'] = package_details
            data_list.append(package_data)
        # data_list =  PackagingSpecificationOutSchema.from_queryset(specifications, many=True)
        
            
        return data_list

    @staticmethod
    def get_single_specification_data(specification_id, edit = True):
        """Lấy thông tin chi tiết của một specification theo ID"""
        try:
            specification = PackagingSpecification.objects.get(id=specification_id)
            
            data = PackagingSpecificationOutSchema.from_queryset(specification)
            
            # Lấy dữ liệu measurements
            dimensions = specification.measurements.filter(measurement_type='dimensions').first()
            if dimensions:
                if not edit:
                    data['dimensions'] = dimensions.get_formatted_value()
                else:
                    data['dimensions'] = dimensions.get_converted_data(None)
            max_weight = specification.measurements.filter(measurement_type='max_weight').first()
            if max_weight:
                if not edit:
                    data['max_weight'] = max_weight.get_formatted_value()
                else:
                    data['max_weight'] = max_weight.get_converted_data(None)
            return True, data
        
        except PackagingSpecification.DoesNotExist:
            return False, None
            
    @staticmethod
    def create_packaging_specification(data_dict):
        """Tạo mới một specification"""
        try:
            # Tạo đối tượng PackagingSpecification
            specification = PackagingSpecification.objects.create(
                name=data_dict.get('name', ''),
                code=data_dict.get('code', ''),
                active=data_dict.get('active', True)
            )
            
            # Xử lý measurements
            if 'dimensions' in data_dict and data_dict['dimensions']:
                # Xóa measurement cũ nếu có (mặc dù là obj mới nhưng vẫn kiểm tra để đảm bảo)
                specification.measurements.filter(measurement_type='dimensions').delete()
                # Tạo measurement mới
                Measurement.create_from_string(specification, 'dimensions', data_dict['dimensions'])
            
            return True, specification
        except Exception as e:
            return False, str(e)
            
    @staticmethod
    def update_packaging_specification(specification_id, data_dict):
        """Cập nhật một specification theo ID"""
        try:
            specification = PackagingSpecification.objects.get(id=specification_id)
            
            # Cập nhật các trường cơ bản
            if 'name' in data_dict and data_dict['name']:
                specification.name = data_dict['name']
            if 'code' in data_dict and data_dict['code']:
                specification.code = data_dict['code']
            specification.save()
            
            # Xử lý measurements
            if 'dimensions' in data_dict and data_dict['dimensions']:
                # Xóa measurement cũ nếu có
                specification.measurements.filter(measurement_type='dimensions').delete()
                # Tạo measurement mới
                Measurement.create_from_string(specification, 'dimensions', data_dict['dimensions'])
            
            return True, specification
        except PackagingSpecification.DoesNotExist:
            return False, "Packaging specification not found"
        except Exception as e:
            return False, str(e)
            
    @staticmethod
    def create_packaging_option(data_dict):
        """Tạo mới một option"""
        try:
            # Tạo đối tượng PackagingOption
            option = PackagingOption.objects.create(
                name=data_dict.get('name', ''),
                order=data_dict.get('order', 1)
            )
            
            # Thêm specifications nếu có
            if 'specifications' in data_dict and data_dict['specifications']:
                specifications = PackagingSpecification.objects.filter(id__in=data_dict['specifications'])
                for spec in specifications:
                    PackagingOptionSpecification.objects.create(
                        option=option,
                        package=spec
                    )
            
            return True, option
        except Exception as e:
            return False, str(e)
            
    @staticmethod
    def update_packaging_option(option_id, data_dict):
        """Cập nhật một option theo ID"""
        try:
            option = PackagingOption.objects.get(id=option_id)
            
            # Cập nhật các trường cơ bản
            if 'name' in data_dict:
                option.name = data_dict['name']
            if 'order' in data_dict:
                option.order = data_dict['order']
            option.save()
            
            # Cập nhật specifications
            if 'specifications' in data_dict:
                # Xóa tất cả specifications hiện tại
                PackagingOptionSpecification.objects.filter(option=option).delete()
                
                # Thêm specifications mới
                if data_dict['specifications']:
                    specifications = PackagingSpecification.objects.filter(id__in=data_dict['specifications'])
                    for spec in specifications:
                        PackagingOptionSpecification.objects.create(
                            option=option,
                            package=spec
                        )
            
            return True, option
        except PackagingOption.DoesNotExist:
            return False, "Packaging option not found"
        except Exception as e:
            return False, str(e)