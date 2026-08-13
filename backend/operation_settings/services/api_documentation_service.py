from typing import Dict, List, Any
from operation_settings.constants.api_documentation import (
    DELIVERY_APIS
)


class ApiDocumentationService:
    """Service for managing API documentation"""

    @classmethod
    def get_supported_apis(cls) -> Dict[str, Any]:
        """Get all supported APIs documentation"""
        return {
            "delivery_apis": cls.get_delivery_apis(),
        }

    @classmethod
    def get_delivery_apis(cls) -> List[Dict[str, Any]]:
        """Get delivery APIs documentation"""
        return DELIVERY_APIS




    @classmethod
    def get_api_by_name(cls, api_name: str) -> Dict[str, Any]:
        """Get specific API documentation by name"""
        for api in DELIVERY_APIS:
            if api["name"] == api_name:
                return api
        return {}

    @classmethod
    def get_apis_by_method(cls, method: str) -> List[Dict[str, Any]]:
        """Get APIs filtered by HTTP method"""
        return [api for api in DELIVERY_APIS if api["method"].upper() == method.upper()]

    @classmethod
    def get_api_endpoints_list(cls) -> List[str]:
        """Get list of all API endpoints"""
        return [api["url"] for api in DELIVERY_APIS]

    @classmethod
    def add_custom_api(cls, api_doc: Dict[str, Any]) -> bool:
        """Add custom API documentation (for future extensibility)"""
        try:
            # Validate required fields
            required_fields = ["name", "method", "url", "description", "auth_required"]
            if not all(field in api_doc for field in required_fields):
                return False
            
            # This could be extended to dynamically add APIs
            # For now, just validate the structure
            return True
        except Exception:
            return False

    @classmethod
    def validate_api_structure(cls, api_doc: Dict[str, Any]) -> bool:
        """Validate API documentation structure"""
        required_fields = ["name", "method", "url", "description", "auth_required", "parameters"]
        optional_fields = ["response_example", "error_responses", "workflow_logic"]
        
        # Check required fields
        for field in required_fields:
            if field not in api_doc:
                return False
        
        # Validate parameters structure
        if "parameters" in api_doc:
            if not isinstance(api_doc["parameters"], dict):
                return False
        
        return True 