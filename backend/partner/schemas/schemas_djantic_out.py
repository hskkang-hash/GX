from core.common.schema_utils import DynamicSchema
from partner.models import Partner


class PartnerOutSchema(DynamicSchema):
    """
    Partner output schema with security considerations
    
    Excludes sensitive fields like api_key and refresh_token by default
    """
    
    class Meta:
        model = Partner
        exclude = []  # Exclude sensitive fields for security
        depth = 1  # Include related fields


class PartnerDetailOutSchema(DynamicSchema):
    """
    Detailed partner output schema for admin view
    
    Includes more fields and relationships
    """
    
    class Meta:
        model = Partner
