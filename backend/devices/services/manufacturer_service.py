from devices.schemas.schemas_djantic_out import ManufacturerInformationOutSchema
from devices.models import ManufacturerInformation
import datetime
from datetime import date, datetime as dt, timezone as dt_timezone
from django.utils import timezone

class ManufacturerInformationService:
    @staticmethod
    def _convert_utc_to_system_timezone_date(utc_datetime):
        """
        Chuyển đổi UTC datetime string hoặc datetime object sang date trong timezone của hệ thống.
        
        Args:
            utc_datetime: datetime object hoặc string (UTC) hoặc date object
            
        Returns:
            date object trong timezone hệ thống, hoặc None nếu không parse được
        """
        if utc_datetime is None:
            return None
        
        # Nếu đã là date object, trả về luôn
        if isinstance(utc_datetime, date) and not isinstance(utc_datetime, dt):
            return utc_datetime
        
        # Nếu là string, parse thành datetime
        if isinstance(utc_datetime, str):
            try:
                # Thử parse ISO format với timezone
                if 'T' in utc_datetime or '+' in utc_datetime or utc_datetime.endswith('Z'):
                    utc_datetime = dt.fromisoformat(utc_datetime.replace('Z', '+00:00'))
                else:
                    # Nếu chỉ là date string, parse thành date
                    return dt.strptime(utc_datetime, '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                # Fallback: thử parse các format khác
                try:
                    utc_datetime = dt.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
        
        # Nếu là datetime nhưng chưa có timezone, giả định là UTC
        if isinstance(utc_datetime, dt):
            if timezone.is_naive(utc_datetime):
                # Nếu là naive datetime, giả định là UTC
                utc_datetime = timezone.make_aware(utc_datetime, dt_timezone.utc)
            else:
                # Đảm bảo datetime là UTC
                if utc_datetime.tzinfo != dt_timezone.utc:
                    utc_datetime = utc_datetime.astimezone(dt_timezone.utc)
            
            # Chuyển đổi sang timezone của hệ thống
            system_tz = timezone.get_current_timezone()
            system_datetime = utc_datetime.astimezone(system_tz)
            
            # Trả về date trong timezone hệ thống
            return system_datetime.date()
        
        return None

    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin nhà sản xuất"""
        print("MANUFACTURER INFORMATION SERVICE",data)
        try:
            # Thử tìm kiếm trước
            if device:
                manufacturer = ManufacturerInformation._base_manager.get(device=device)
            elif library:
                manufacturer = ManufacturerInformation._base_manager.get(library=library)
            
        except ManufacturerInformation.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            # Đảm bảo production_date là một đối tượng date hợp lệ
            production_date = data.get('production_date', None)
            production_date = ManufacturerInformationService._convert_utc_to_system_timezone_date(production_date)
      
            manufacturer = ManufacturerInformation(
                device=device,
                library=library,
                manufacturer=data.get('manufacturer', None),
                country_of_origin_id=data.get('country_of_origin_id',None),
                model_number=data.get('model_number', None),
                serial_number=data.get('serial_number', None),
                production_date=production_date,
                note=data.get('note', None),
                insurance_type=data.get('insurance_type', None),
                insurance_provider=data.get('insurance_provider', None),
                policy_number=data.get('policy_number', None),
                validity_period_from=data.get('validity_period_from', None),
                validity_period_to=data.get('validity_period_to', None),
                current_status=data.get('current_status', None),
                registration_number=data.get('registration_number', None)
            )

        # Cập nhật các trường
        fields = [
            'manufacturer', 'country_of_origin_id', 'model_number',
            'serial_number', 'note',
            'insurance_type', 'insurance_provider', 'policy_number', 'validity_period_from', 'validity_period_to', 'current_status', 
            'registration_number'
        ]
        
        for field in fields:
            setattr(manufacturer, field, data.get(field,None))
                
        # Xử lý riêng trường production_date - convert từ UTC datetime string sang date trong timezone hệ thống
        if 'production_date' in data:
            manufacturer.production_date = ManufacturerInformationService._convert_utc_to_system_timezone_date(data['production_date'])
        else:
            # Nếu không có trong data, giữ nguyên giá trị hiện tại (không set None)
            pass
        manufacturer.save()
        
        return True, manufacturer

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                manufacturer = device.manufacturer_information
            elif library:
                manufacturer = library.manufacturer_information
            
            data = ManufacturerInformationOutSchema.from_queryset(manufacturer)
            if data.get('insurance_type') or data.get('insurance_provider') or data.get('policy_number') or data.get('validity_period_from') or data.get('validity_period_to') or data.get('current_status'):
                data['insurance_status'] = True
            else:
                data['insurance_status'] = False 
            return data
        except ManufacturerInformation.DoesNotExist:
            return None
