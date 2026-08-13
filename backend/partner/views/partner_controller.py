"""
Partner Controller

This controller provides APIs for partner management:
- Internal users: Create, manage, monitor partners
- Partners can use existing APIs directly via middleware (orders, deliveries, etc.)
"""

from django.db import models
from django.db.models import F, Q, Case, When, BooleanField, Exists, OuterRef
from django.http import HttpRequest
from ninja_extra import api_controller, route
from core.role.permission import path_permission
from core.common.base_response import BaseResponse
from common.pagination import OptimizedPaginator
from core.common.search.dynamic_search import apply_dynamic_filters
from partner.models import Partner
from partner.schemas import (
    PartnerCreateMinimalSchema, 
    PartnerOutSchema, 
    PartnerDetailOutSchema,
    PartnerCreateResponseSchema,
    RefreshTokenSchema,
    ManageRefreshTokenSchema,
    ApiCallbackInSchema,
    PartnerCallbackUpdateSchema,
    PartnerApiKeyUpdateSchema
)
from partner.utils.partner_utils import PartnerUtils
from partner.services.partner_service import PartnerService
from common.constant import MESSAGE_ENUM
from delivery.models import DeliveryOperation
from orders.models import Order
import logging
from core.api.v1.auth import CustomJWTAuth
from django.db import models
from django.db.models import Case, When, BooleanField, IntegerField, ExpressionWrapper, F, Value
from django.db.models.functions import Greatest, Extract
from django.utils import timezone
from datetime import timedelta, datetime
from core.user.models import UserGroup
logger = logging.getLogger(__name__)


@api_controller("/api/partners", tags=["Partners"])
class PartnerController:

    @route.post("/", auth=CustomJWTAuth())
    @path_permission("create", path_override=['/partner'])
    def create_partner(self, request: HttpRequest, data: PartnerCreateMinimalSchema):

        try:
            # Get user's group
            user_group = None
            if data.group:
                user_group = UserGroup.objects.get(id=data.group)
            elif hasattr(request.user, 'userprofilelink') and request.user.userprofilelink:
                user_group = request.user.userprofilelink.group
            else:
                raise Exception("User must belong to a group to create partners")

            
            # Validate data using service
            validation_result = PartnerService.validate_partner_for_creation(
                data.name, user_group, data.expired_days
            )
            
            if not validation_result['success']:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message="Validation failed",
                    errors=validation_result['errors']
                )
            
            # Create partner with proxy user using service
            partner = PartnerService.create_partner_with_proxy(
                name=data.name,
                group=user_group,
                expired_days=data.expired_days,
                created_by_user=request.user,
                api_callback_url=data.api_callback_url,
                request=request,
                service_key=data.service_key
            )
            
            logger.info(f"Partner created: {partner.code} by user {request.user.username}")
            
            # Return partner details with API key for initial setup
            return BaseResponse(
                success=True,
                status_code=201,
                data=PartnerDetailOutSchema.from_queryset(
                    partner),
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_PARTNER_WITH_PROXY_SUCCESS)
            )
            
        except Exception as e:
            logger.error(f"Error creating partner: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to create partner",
                errors=[str(e)]
            )
    @route.put("/{partner_id}/api-key", auth=CustomJWTAuth())
    @path_permission("update", path_override=['/partner'])
    def update_partner_api_key(self, request: HttpRequest, partner_id: int, data: PartnerApiKeyUpdateSchema):
        """
        Update partner API key and related information
        
        Args:
            request: HTTP request object
            partner_id: ID of the partner
            data: PartnerApiKeyUpdateSchema with update data
            
        Returns:
            BaseResponse with updated partner info
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Update API key using service
            result = PartnerService.update_partner_api_key(partner, data)
            
            if not result['success']:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result['error']
                )
            
            logger.info(f"Partner API key updated for {partner.code} by user {request.user.username}")
            
            return BaseResponse(
                success=True,
                data=PartnerDetailOutSchema.from_queryset(result['partner']),
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PARTNER_API_KEY_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error updating partner API key: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PARTNER_API_KEY_FAILED),
                errors=[str(e)]
            )
    @route.get("/", auth=CustomJWTAuth())
    @path_permission("read", path_override=['/partner'])
    def list_partners(
        self, 
        request: HttpRequest, 
        page_size: int = 20, 
        current_page: int = 1,
        sort_obj: object = None
    ):
        
        try:
            partners_queryset = Partner.objects.select_related(
                'proxy_user', 
                'created_by',
                'modified_by',
                'group'
            ).annotate(
                api_user=F('api_key'),
                refresh=F('refresh_token'),
                service=F('service_key'),
                in_use=Case(
                    When(
                        Q(
                            Exists(
                                DeliveryOperation.objects.filter(
                                    Q(created_by=OuterRef('proxy_user')) | Q(modified_by=OuterRef('proxy_user'))
                                )
                            )
                        ) | Q(
                            Exists(
                                Order.objects.filter(
                                    Q(created_by=OuterRef('proxy_user')) | Q(modified_by=OuterRef('proxy_user'))
                                )
                            )
                        ),
                        then=True
                    ),
                    default=False,
                    output_field=BooleanField()
                ),
                # remaining_days: Days until API key expires (simple date arithmetic)  
                remaining_days=Case(
                    When(
                        refresh_token__isnull=True,
                        then=models.expressions.RawSQL(
                            "EXTRACT(day FROM (expired_at::timestamp - NOW()::timestamp))",
                            []
                        )
                    ),
                    default=models.expressions.RawSQL(
                        "EXTRACT(day FROM (refresh_token_expires_at::timestamp - NOW()::timestamp))",
                        []
                    ),
                    output_field=models.IntegerField()
                ),
                # expired: True if expired_at is past or remaining_days < 0
                expired=Case(
                    When(
                        expired_at__isnull=True,
                        then=Value(False)  # No expiry set - never expired
                    ),
                    When(
                        expired_at__lt=timezone.now(),
                        then=Value(True)  # Expired
                    ),
                    default=Value(False),  # Not expired
                    output_field=BooleanField()
                )
            ).distinct().order_by('-created_on')
            
            # Apply dynamic filters for search, filter and sort - handles all filtering automatically
            partners_queryset = apply_dynamic_filters(
                partners_queryset, 
                request, 
                [], 
                request.GET.get('sort_obj', None)
            )
            
            # Pagination
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(partners_queryset, page_size)
            pages = paginator.page(current_page)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PARTNER_MANAGEMENT_LIST_SUCCESS),
                data=PartnerOutSchema.from_queryset(pages.object_list, many=True),
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
            
        except Exception as e:
            logger.error(f"Error listing partners: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to retrieve partners",
                errors=[str(e)]
            )
    
    @route.get("/{partner_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override=['/partner'])
    def get_partner_detail(self, request: HttpRequest, partner_id: int):
        
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.select_related(
                'proxy_user', 'created_by'
            ).annotate(
                api_user=F('api_key'),
                refresh=F('refresh_token'),
                # remaining_days: Days until API key expires
                remaining_days=Case(
                    When(
                        expired_at__isnull=True,
                        then=Value(1)  # No expiry set - infinite days  
                    ),
                    default=models.expressions.RawSQL(
                        "EXTRACT(day FROM (expired_at::timestamp - NOW()::timestamp))",
                        []
                    ),
                    output_field=models.IntegerField()
                ),
                # expired: True if expired_at is past or remaining_days < 0
                expired=Case(
                    When(
                        expired_at__isnull=True,
                        then=Value(False)  # No expiry set - never expired
                    ),
                    When(
                        expired_at__lt=timezone.now(),
                        then=Value(True)  # Expired
                    ),
                    default=Value(False),  # Not expired
                    output_field=BooleanField()
                )
            ).get(id=partner_id)
            
            # Return detailed partner information
            return BaseResponse(
                success=True,
                data=PartnerDetailOutSchema.from_queryset(partner),
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PARTNER_MANAGEMENT_DETAIL_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error getting partner detail: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to retrieve partner",
                errors=[str(e)]
            )
    
    @route.put("/{partner_id}/toggle-status", auth=CustomJWTAuth())
    @path_permission("update", path_override=['/partner'])
    def toggle_partner_status(self, request: HttpRequest, partner_id: int):
        
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.select_related('proxy_user').get(id=partner_id)
            
            # Toggle status
            partner.is_active = not partner.is_active
            partner.save()
            
            # Also toggle proxy user status for consistency
            if partner.proxy_user:
                partner.proxy_user.is_active = partner.is_active
                partner.proxy_user.save()
            
            status_text = "activated" if partner.is_active else "deactivated"
            logger.info(f"Partner {partner.code} {status_text} by user {request.user.username}")
            
            return BaseResponse(
                success=True,
                data={
                    'id': partner.id,
                    'name': partner.name,
                    'code': partner.code,
                    'is_active': partner.is_active,
                },
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.TOGGLE_PARTNER_STATUS_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error toggling partner status: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to update partner status",
                errors=[str(e)]
            )
    
    @route.post("/{partner_id}/regenerate-api-key", auth=CustomJWTAuth())
    @path_permission("update", path_override=['/partner'])
    def regenerate_api_key(self, request: HttpRequest, partner_id: int):
       
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Regenerate API key using service
            result = PartnerService.regenerate_partner_api_key(partner, request, request.user)
            
            if not result['success']:
                return BaseResponse(
                    success=False,
                    status_code=500,
                    message="Failed to regenerate API key",
                    errors=[result['error']]
                )
            
            # Mask old API key for logging
            masked_old_key = f"{result['old_api_key'][:6]}***{result['old_api_key'][-4:]}" if result['old_api_key'] and len(result['old_api_key']) >= 10 else "***"
            logger.warning(
                f"API key regenerated for partner {partner.code} by user {request.user.username}. "
                f"Old key: {masked_old_key}"
            )
            
            return BaseResponse(
                success=True,
                data={
                    'id': partner.id,
                    'name': partner.name,
                    'code': partner.code,
                    'api_key': result['new_api_key'],  # Return new key for setup
                },
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.REGENERATE_PARTNER_API_KEY_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error regenerating API key: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to regenerate API key",
                errors=[str(e)]
            )
    
    
    @route.get("/my-status", auth=CustomJWTAuth())
    def get_my_partner_status(self, request: HttpRequest):
        
        try:
            # Check if this is a partner request
            if not getattr(request, 'is_partner_request', False):
                return BaseResponse(
                    success=False,
                    status_code=403,
                    message="This endpoint is only accessible to partners using API key authentication"
                )
            
            partner = request.partner
            
            # Return partner's own information
            return BaseResponse(
                success=True,
                data=PartnerOutSchema.from_queryset(partner),
                message="Partner status retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error getting partner status: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to retrieve partner status",
                errors=[str(e)]
            )
    
    @route.post("/refresh-token/{partner_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override=['/partner'])
    def manage_refresh_token(self, request: HttpRequest, partner_id: int, data: ManageRefreshTokenSchema):
        """
        Smart refresh token management: refresh if exists and valid, generate if not
        
        Args:
            request: HTTP request object
            partner_id: ID of the partner
            data: ManageRefreshTokenSchema (optional refresh_token)
            
        Returns:
            BaseResponse with refresh token info and action taken
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Use smart refresh token management
            result = PartnerService.manage_refresh_token(partner, data.refresh_token, request, request.user)
            
            if not result['success']:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result['error']
                )
            
            action = result['action']
            action_text = {
                "refreshed": "refreshed",
                "regenerated": "regenerated", 
                "generated": "generated"
            }.get(action, "processed")
            
            logger.info(f"Refresh token {action_text} for partner {partner.code} by user {request.user.username}")
            
            response_data = {
                'id': partner.id,
                'name': partner.name,
                'code': partner.code,
                'action': action,
                'refresh_token': result['refresh_token'],
                'refresh_token_expires_at': result['refresh_token_expires_at'].isoformat(),
                'remaining_days': result['remaining_days'].days,
            }
            
            # Include API key if it was refreshed or regenerated
            if action in ["refreshed", "regenerated"]:
                response_data['api_key'] = result['api_key']
            
            return BaseResponse(
                success=True,
                data=response_data,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GENERATE_PARTNER_REFRESH_TOKEN_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error managing refresh token: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to manage refresh token",
                errors=[str(e)]
            )
    
    @route.delete("/{partner_id}/revoke-refresh-token", auth=CustomJWTAuth())
    @path_permission("update", path_override=['/partner'])
    def revoke_refresh_token(self, request: HttpRequest, partner_id: int):
        """
        Revoke refresh token for partner
        
        Args:
            request: HTTP request object
            partner_id: ID of the partner
            
        Returns:
            BaseResponse with revocation status
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Revoke refresh token
            partner.refresh_token = None
            partner.refresh_token_expires_at = None
            partner.save()
            
            logger.info(f"Refresh token revoked for partner {partner.code} by user {request.user.username}")
            
            return BaseResponse(
                success=True,
                data={
                    'id': partner.id,
                    'name': partner.name,
                    'code': partner.code,
                    'refresh_token_revoked': True,
                },
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.REVOKE_PARTNER_REFRESH_TOKEN_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error revoking refresh token: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to revoke refresh token",
                errors=[str(e)]
            )
    
    @route.put("/{partner_id}/api-callbacks", auth=CustomJWTAuth()  )
    @path_permission("update", path_override=['/partner'])
    def update_api_callbacks(self, request: HttpRequest, partner_id: int, data: PartnerCallbackUpdateSchema):
        """
        Update API callback URLs for partner
        
        Args:
            request: HTTP request object
            partner_id: ID of the partner
            data: Callback update data
            
        Returns:
            BaseResponse with updated callback info
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Update callbacks using service
            result = PartnerService.update_partner_api_callbacks(partner, data.api_callback_url.dict())
            
            if not result['success']:
                return BaseResponse(
                    success=False,
                    status_code=400,
                    message=result['error']
                )
            
            logger.info(f"API callbacks updated for partner {partner.code} by user {request.user.username}")
            
            return BaseResponse(
                success=True,
                data={
                    'id': partner.id,
                    'name': partner.name,
                    'code': partner.code,
                    'api_callback_url': result['api_callback_url'],
                },
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PARTNER_API_CALLBACK_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error updating API callbacks: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to update API callbacks",
                errors=[str(e)]
            )
    
    @route.get("/{partner_id}/copy-api-key", auth=CustomJWTAuth())
    @path_permission("read", path_override=['/partner'])
    def copy_partner_api_key(self, request: HttpRequest, partner_id: int):
        """
        Get partner API key for copy functionality
        
        Args:
            request: HTTP request object
            partner_id: ID of the partner
            
        Returns:
            BaseResponse with API key for copying to clipboard
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner = Partner.objects.get(id=partner_id)
            
            # Log the API key access for security
            logger.warning(
                f"API key accessed for partner {partner.code} by user {request.user.username}. "
                f"IP: {request.META.get('REMOTE_ADDR', 'unknown')}"
            )

            
            return BaseResponse(
                success=True,
                data={"api_key": partner.api_key},
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PARTNER_MANAGEMENT_DETAIL_SUCCESS)
            )
            
        except Partner.DoesNotExist:
            return BaseResponse(
                success=False,
                status_code=404,
                message="Partner not found"
            )
        except Exception as e:
            logger.error(f"Error accessing partner API key: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message="Failed to access API key",
                errors=[str(e)]
            )
    
    @route.delete("/delete/{partner_ids}", auth=CustomJWTAuth())
    @path_permission("delete", path_override=['/partner'])
    def delete_partner(self, request: HttpRequest, partner_ids: str):
        """
        Delete partner
        """
        try:
            # Get partner (BaseModelWithGroup automatically filters by group)
            partner_id_list = partner_ids.split(',')
            partner = Partner.objects.filter(id__in=partner_id_list)
            for p in partner:
                p.proxy_user.delete()
                p.delete()
            return BaseResponse(
                success=True,
                data=None,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            )
        
        except Exception as e:
            logger.error(f"Error deleting partner: {e}")
            return BaseResponse(
                success=False,
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                errors=[str(e)]
            )