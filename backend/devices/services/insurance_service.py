from devices.models import InsuranceInformation

class InsuranceInformationService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin bảo hiểm"""
        try:
            # Thử tìm kiếm trước
            if device:
                insurance = InsuranceInformation._base_manager.get(device=device)
            elif library:
                insurance = InsuranceInformation._base_manager.get(library=library)
            
        except InsuranceInformation.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            insurance = InsuranceInformation(
                device=device,
                library=library,
                insurance_status=data.get('insurance_status', False),
                insurance_type=data.get('insurance_type', None),
                insurance_provider=data.get('insurance_provider', None),
                policy_number=data.get('policy_number', None),
                validity_period_from=data.get('validity_period_from', None),
                validity_period_to=data.get('validity_period_to', None),
                current_status=data.get('current_status', None)
            )
            
        # Cập nhật các trường
        fields = [
            'insurance_status', 'insurance_type', 'insurance_provider',
            'policy_number', 'validity_period_from', 'validity_period_to', 'current_status'
        ]
        
        for field in fields:
            if field == 'insurance_status':
                setattr(insurance, field, data.get(field,False))
            else:
                setattr(insurance, field, data.get(field,None))
        insurance.save()
        
        return True, insurance

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                insurance = device.insurance_information
            elif library:
                insurance = library.insurance_information
            
            data = {
                'insurance_status': insurance.insurance_status,
                'insurance_type': insurance.insurance_type,
                'insurance_provider': insurance.insurance_provider,
                'policy_number': insurance.policy_number,
                'validity_period_from': insurance.validity_period_from,
                'validity_period_to': insurance.validity_period_to,
                'current_status': insurance.current_status
            }
                
            return data
        except InsuranceInformation.DoesNotExist:
            return None
