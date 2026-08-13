from devices.models import CargoCompartments, Measurement
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class CargoCompartmentsService:
    
    @staticmethod
    @transaction.atomic
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin ngăn chứa hàng"""
        compartment_id = data.get('id')
        compartment = None
        if compartment_id:
            # Cập nhật ngăn chứa đã tồn tại
            if device:
                compartment = CargoCompartments._base_manager.get(id=compartment_id, device=device)
            elif library:
                compartment = CargoCompartments._base_manager.get(id=compartment_id, library=library)
        elif device and device.cargo_compartments.exists():
            compartment = device.cargo_compartments.first()
            compartment = CargoCompartments(device=device, 
                                            compartment_number = data.get('compartment_number',None), 
                                            name = data.get('name', None), 
                                            secure_locking = data.get('secure_locking', None), 
                                            quick_release = data.get('quick_release', None), 
                                            temperature_control = data.get('temperature_control', None), 
                                            status = data.get('status', None))
            device.cargo_compartments.all().exclude(id=compartment.id).delete()
        elif library and library.cargo_compartments.exists():
            compartment = library.cargo_compartments.first()
            compartment = CargoCompartments(library=library, 
                                            compartment_number = data.get('compartment_number',None), 
                                            name = data.get('name', None), 
                                            secure_locking = data.get('secure_locking', None), 
                                            quick_release = data.get('quick_release', None), 
                                            temperature_control = data.get('temperature_control', None), 
                                            status = data.get('status', None))
            library.cargo_compartments.all().exclude(id=compartment.id).delete()
        else:
            # Tạo mới
            if device:
                compartment = CargoCompartments(device=device, 
                                            compartment_number = data.get('compartment_number',None), 
                                            name = data.get('name', None), 
                                            secure_locking = data.get('secure_locking', None), 
                                            quick_release = data.get('quick_release', None), 
                                            temperature_control = data.get('temperature_control', None), 
                                            status = data.get('status', None))
            elif library:
                compartment = CargoCompartments(library=library, 
                                            compartment_number = data.get('compartment_number',None), 
                                            name = data.get('name', None), 
                                            secure_locking = data.get('secure_locking', None), 
                                            quick_release = data.get('quick_release', None), 
                                            temperature_control = data.get('temperature_control', None), 
                                            status = data.get('status', None))
        compartment.save()

        # Cập nhật measurements
        for field in ['dimensions', 'weight_capacity']:
            if field in data and data[field]:
                compartment.measurements.filter(measurement_type=field).delete()
                Measurement.create_from_string(compartment, field, data[field])
            else:
                compartment.measurements.filter(measurement_type=field).delete()
        return True, compartment

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """
        Lấy thông tin hiển thị của một ngăn chứa
        Args:
            device (Device): Thiết bị
            user_units (str, optional): Đơn vị của người dùng. Defaults to None.
            edit (bool, optional): True nếu muốn hiển thị dữ liệu có thể chỉnh sửa. Defaults to False.

        Returns:
            dict: Thông tin hiển thị của ngăn chứa
        """
        if device:
            compartment = device.cargo_compartments.first()
        elif library:
            compartment = library.cargo_compartments.first()
        if not compartment:
            return None
        data = {
            'id': compartment.id,
            'compartment_number': compartment.compartment_number,
            'name': compartment.name,
            'secure_locking': compartment.secure_locking,
            'quick_release': compartment.quick_release,
            'temperature_control': compartment.temperature_control,
            'status': compartment.status
        }
        
        # Lấy dữ liệu từ measurements
        for field in ['dimensions', 'weight_capacity', 'max_weight', 'temperature_range', 'humidity_range']:
            m = compartment.measurements.filter(measurement_type=field).first()
            if m and edit:
                data[field] = m.get_formatted_value(user_units)
            elif m:
                data[field] = m.get_converted_data(user_units)
                
        return data
    
    @staticmethod
    def get_all_data(device, user_units=None):
        """Lấy thông tin của tất cả ngăn chứa của thiết bị"""
        compartments = device.cargo_compartments.all()
        
        if not compartments:
            return None
            
        result = []
        for compartment in compartments:
            result.append(CargoCompartmentsService.get_data(compartment, user_units))
            
        return result
    
    @staticmethod
    def delete(compartment_id):
        """Xóa ngăn chứa"""
        try:
            compartment = CargoCompartments.objects.get(id=compartment_id)
            compartment.delete()
            return True
        except CargoCompartments.DoesNotExist:
            return False
