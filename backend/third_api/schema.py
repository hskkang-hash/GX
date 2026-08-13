from ninja import Schema, Field
from typing import List, Optional
from datetime import datetime, timedelta



class CreateAPIKeySchema(Schema):
    name: str = Field(..., description="Descriptive name for API key")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Number of days until expiration (optional, max 365 days)")


class APIKeySchema(Schema):
    id: int
    name: str
    prefix: str
    is_active: bool
    user_username: str
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_expired: bool

    @staticmethod
    def resolve_user_username(obj):
        return obj.user.username

    @staticmethod
    def resolve_is_expired(obj):
        return obj.is_expired


class APIKeyResponseSchema(Schema):
    api_key: APIKeySchema
    key: str = Field(..., description="Actual API key (shown only once)")
    message: str = Field(default="API key has been created successfully. Please save this key as it will not be shown again.")


class UpdateAPIKeySchema(Schema):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class APIKeyUsageLogSchema(Schema):
    id: int
    api_key_name: str
    endpoint: str
    method: str
    ip_address: str
    timestamp: datetime
    success: bool
    response_status: Optional[int]

    @staticmethod
    def resolve_api_key_name(obj):
        return obj.api_key.name


class APIKeyStatsSchema(Schema):
    total_keys: int
    active_keys: int
    expired_keys: int
    total_requests_today: int
    successful_requests_today: int
    failed_requests_today: int


class UsageAnalyticsSchema(Schema):
    daily_stats: List[dict]
    endpoint_stats: List[dict]
    apikey_stats: List[dict]
    period_days: int


class BulkDeactivateSchema(Schema):
    api_key_ids: List[int] = Field(..., description="List of API key IDs to deactivate")


class BulkDeactivateResponseSchema(Schema):
    message: str
    deactivated_count: int


class CheckAPIKeyResponseSchema(Schema):
    valid: bool
    api_key: Optional[APIKeySchema] = None
    error: Optional[str] = None


class ErrorResponseSchema(Schema):
    error: str


class MessageResponseSchema(Schema):
    message: str


class UsageLogsResponseSchema(Schema):
    results: List[APIKeyUsageLogSchema]
    count: int
    page: int
    page_size: int
