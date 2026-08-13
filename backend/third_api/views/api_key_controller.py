from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from django.http import HttpRequest
from typing import List, Optional

from core.api.v1.auth import CustomJWTAuth
from third_api.schema import APIKeySchema, APIKeyResponseSchema
from core.role.permission import path_permission

# Import existing API Key Controller and schemas from apikey_account
from core.apikey_account.api import (
    APIKeyController, 
    CreateAPIKeySchema, 
    UpdateAPIKeySchema, 
    BulkDeactivateSchema,
    APIKeyStatsSchema,
    UsageAnalyticsSchema,
    CheckAPIKeyResponseSchema,
    UsageLogsResponseSchema,
    MessageResponseSchema,
    ErrorResponseSchema
)


@api_controller("/api-key-management", tags=["API Key Management"])
class ThirdPartyAPIKeyController(APIKeyController):
    """Controller for API Key management operations - Inherits from existing apikey_account controller"""
    
    @route.post("/keys", response={201: APIKeyResponseSchema, 400: ErrorResponseSchema}, auth=CustomJWTAuth())
    # @path_permission("create", path_override='/api-key-management')
    def create_api_key(self, request, data: CreateAPIKeySchema):
        """
        Create new API Key for current user
        """
        try:
            return super().create_api_key(data)
        except ValidationError as e:
            return 400, {"error": f"Validation error: {str(e)}"}
        except Exception as e:
            return 500, {"error": f"Unexpected error: {str(e)}"}

    @route.get("/keys", response=List[APIKeySchema], auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def list_api_keys(self, request):
        """
        Get list of current user's API Keys
        """
        try:
            return super().list_api_keys()
        except Exception as e:
            return 500, {"error": f"Error retrieving API keys: {str(e)}"}

    @route.get("/get-keys/{api_key_id}", response=APIKeySchema, auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')  # Tạm thời comment out để test
    def get_api_key(self, request, api_key_id: int):
        """
        Get detailed information of an API Key
        """
        print(f"DEBUG: get_api_key called with id={api_key_id}, method={request.method}")
        try:
            # Kiểm tra cách lớp cha định nghĩa phương thức
            print(f"DEBUG: Calling parent method get_api_key")
            result = super().get_api_key(api_key_id)
            print(f"DEBUG: Parent method returned successfully")
            return result
        except Exception as e:
            print(f"DEBUG: Exception in get_api_key: {str(e)}")
            return 500, {"error": f"Error retrieving API key: {str(e)}"}

    @route.patch("/keys/{api_key_id}", response={200: APIKeySchema, 400: ErrorResponseSchema}, auth=CustomJWTAuth())
    # @path_permission("update", path_override='/api-key-management')
    def update_api_key(self, request, api_key_id: int, data: UpdateAPIKeySchema):
        """
        Update API Key information
        """
        try:
            return super().update_api_key(api_key_id, data)
        except ValidationError as e:
            return 400, {"error": f"Validation error: {str(e)}"}
        except Exception as e:
            return 500, {"error": f"Error updating API key: {str(e)}"}

    @route.delete("/keys/{api_key_id}", response=MessageResponseSchema, auth=CustomJWTAuth())
    # @path_permission("delete", path_override='/api-key-management')
    def delete_api_key(self, request, api_key_id: int):
        """
        Deactivate API Key (soft delete)
        """
        try:
            return super().delete_api_key(api_key_id)
        except Exception as e:
            return 500, {"error": f"Error deactivating API key: {str(e)}"}

    @route.post("/keys/{api_key_id}/regenerate", response=APIKeyResponseSchema, auth=CustomJWTAuth())
    # @path_permission("update", path_override='/api-key-management')
    def regenerate_api_key(self, request, api_key_id: int):
        """
        Regenerate new API Key (keep same name and settings)
        """
        try:
            return super().regenerate_api_key(api_key_id)
        except Exception as e:
            return 500, {"error": f"Error regenerating API key: {str(e)}"}

    @route.get("/keys/{api_key_id}/usage-logs", response=UsageLogsResponseSchema, auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def get_usage_logs(self, request, api_key_id: int, page: int = 1, page_size: int = 50):
        """
        Get usage logs of an API Key
        """
        try:
            return super().get_usage_logs(api_key_id, page, page_size)
        except Exception as e:
            return 500, {"error": f"Error retrieving usage logs: {str(e)}"}

    @route.get("/stats", response=APIKeyStatsSchema, auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def get_stats(self, request):
        """
        Get user's API Key statistics
        """
        try:
            return super().get_stats()
        except Exception as e:
            return 500, {"error": f"Error retrieving stats: {str(e)}"}

    @route.get("/analytics", response=UsageAnalyticsSchema, auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def get_analytics(self, request, days: int = 7):
        """
        Get detailed analytics about API key usage
        """
        try:
            return super().get_analytics(days)
        except Exception as e:
            return 500, {"error": f"Error retrieving analytics: {str(e)}"}

    @route.post("/bulk-deactivate", response={200: MessageResponseSchema, 400: ErrorResponseSchema}, auth=CustomJWTAuth())
    # @path_permission("delete", path_override='/api-key-management')
    def bulk_deactivate(self, request, data: BulkDeactivateSchema):
        """
        Deactivate multiple API keys at once
        """
        try:
            return super().bulk_deactivate(data)
        except ValidationError as e:
            return 400, {"error": f"Validation error: {str(e)}"}
        except Exception as e:
            return 500, {"error": f"Error bulk deactivating API keys: {str(e)}"}

    @route.get("/check", response=CheckAPIKeyResponseSchema, auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def check_api_key(self, request):
        """
        Check validity of current API key
        """
        try:
            return super().check_api_key()
        except Exception as e:
            return 500, {"error": f"Error checking API key: {str(e)}"} 

    @route.get("/test-endpoint", auth=CustomJWTAuth())
    def test_endpoint(self, request):
        """
        Simple test endpoint to check routing
        """
        print("DEBUG: test_endpoint called")
        return {"message": "Test endpoint working!"} 