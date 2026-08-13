"""
Partner Service

Business logic layer for partner operations.
Handles complex operations involving multiple models and business rules.
"""

from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from core.user.models import CoreUser, UserProfileLink
from core.role.models import Role
from partner.models import Partner
from partner.utils.partner_utils import PartnerUtils
from core.user.models import UserGroup

class PartnerService:
    """
    Service class for partner business logic
    
    Handles complex partner operations that involve business rules,
    multiple model interactions, and transaction management.
    """
    
    @staticmethod
    def validate_partner_for_creation(name: str, user_group, expired_days) -> Dict[str, Any]:
        """
        Validate partner data before creation
        
        Args:
            name: Partner name
            user_group: Creating user's group
            expired_days: Expired days
        Returns:
            Dict: Validation result with success flag and errors
        """
        errors = []
        
        # Validate name
        if not name or not name.strip():
            errors.append("Partner name is required")
        elif len(name.strip()) < 2:
            errors.append("Partner name must be at least 2 characters")
        elif len(name.strip()) > 255:
            errors.append("Partner name must not exceed 255 characters")
        
        # Validate group
        if not user_group:
            errors.append("User must belong to a group to create partners")
        
        # Validate expired days
        if not expired_days:
            errors.append("Expired days is required")
        elif expired_days < 1:
            errors.append("Expired days must be at least 1")
            
        return {
            'success': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def create_proxy_user_for_partner(partner_name: str, group, created_by_user) -> CoreUser:
        """
        Create a proxy CoreUser for partner authentication
        
        This creates a system user that will be used as proxy for partner authentication,
        allowing partners to work with existing BaseModel and permission systems.
        
        Args:
            partner_name: Name of the partner
            group: Group object to assign to the user
            created_by_user: User creating the partner
        Returns:
            CoreUser: Created proxy user
        """
        # Generate unique username using utility function
        base_username = f"{partner_name}"
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        username = f"ms_{group.name}_{timestamp}"
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while CoreUser.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Create proxy user
        proxy_user = CoreUser.objects.create(
            username=username,
            email=f"{username}@partner.system",
            first_name=f"Partner: {partner_name}",
            last_name="(Partner User)",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        
        
        all_role_created_by_user = created_by_user.roles.all()
        if not all_role_created_by_user:
            raise Exception("No roles found for created by user")
        # Assign partner role
        proxy_user.roles.add(*all_role_created_by_user)
        
        # Assign to group if available
        if group and hasattr(proxy_user, 'userprofilelink'):
            try:
                proxy_user.userprofilelink.group = group
                proxy_user.userprofilelink.save()
            except Exception:
                raise Exception("Failed to assign group to proxy user")
        else:
            UserProfileLink.objects.create(
                user=proxy_user,
                name=proxy_user.first_name,
                email=proxy_user.email,
                is_default=True,
                group=group,
            )
        return proxy_user
    
    @staticmethod
    @transaction.atomic
    def create_partner_with_proxy(name: str, group, created_by_user, expired_days, api_callback_url, request=None, service_key=None) -> Partner:
        """
        Create partner with auto-generated data and proxy user
        
        This is the main business logic for partner creation that:
        1. Generates unique partner code and API key
        2. Creates proxy user for authentication
        3. Creates partner record with proper relationships
        4. Assigns to appropriate group
        
        Args:
            name: Partner name
            group: Group object for the partner
            created_by_user: User creating the partner
            expired_days: Expired days
        Returns:
            Partner: Created partner with proxy user
        """
        # Generate unique partner data using utilities
        code = PartnerUtils.generate_partner_code_auto(name,group)
        
        # Generate secure API key with context information
        additional_context = {
            'partner_code': code,
            'action_type': 'create_partner',
            'group_id': group.id if group else None
        }
        api_key = PartnerUtils.generate_api_key_with_prefix(request, created_by_user, additional_context)
        
        # Ensure code uniqueness
        counter = 1
        original_code = code
        while Partner.objects.filter(code=code).exists():
            code = f"{original_code}_{counter:02d}"
            counter += 1
        
        # Ensure API key uniqueness (very unlikely collision)
        while Partner.objects.filter(api_key=api_key).exists():
            api_key = PartnerUtils.generate_api_key_with_prefix(request, created_by_user, additional_context)
        
        # Create proxy user (this handles the complex user creation logic)
        proxy_user = PartnerService.create_proxy_user_for_partner(name, group,created_by_user)
        
        # Create partner with all relationships
        partner = Partner.objects.create(
            name=name,
            code=code,
            api_key=api_key,
            proxy_user=proxy_user,
            is_active=True,
            expired_at=now() + timedelta(days=expired_days),
            api_callback_url=PartnerUtils.get_default_api_callback() if not api_callback_url else api_callback_url,
            group=group,
            expired_days=expired_days,
            service_key=service_key,
        )
        
        return partner
    
    @staticmethod
    @transaction.atomic
    def update_partner_api_key(partner: Partner, data) -> Dict[str, Any]:
        """
        Update partner API key and related information
        
        Args:
            partner: Partner instance to update
            data: PartnerApiKeyUpdateSchema data
            
        Returns:
            Dict: Update result with success status
        """
        try:
            # Validate API key format
            if not PartnerUtils.validate_api_key_format(data.api_key):
                return {
                    'success': False,
                    'error': 'Invalid API key format'
                }
            
            # Check if API key is unique (exclude current partner)
            existing_partner = Partner.objects.filter(
                api_key=data.api_key
            ).exclude(id=partner.id).first()
            
            if existing_partner:
                return {
                    'success': False,
                    'error': 'API key already exists for another partner'
                }
            
            # Handle group update if provided
            target_group = partner.group  # Default to current group
            if data.group:
                try:
                    from core.user.models import UserGroup
                    target_group = UserGroup.objects.get(id=data.group)
                except UserGroup.DoesNotExist:
                    return {
                        'success': False,
                        'error': 'Invalid group ID'
                    }
            
            # Handle code update if provided
            if data.code and data.code != partner.code:
                # Validate code format
                if not PartnerUtils.validate_partner_code(data.code):
                    return {
                        'success': False,
                        'error': 'Invalid partner code format'
                    }
                
                # Check code uniqueness
                existing_code = Partner.objects.filter(
                    code=data.code
                ).exclude(id=partner.id).first()
                
                if existing_code:
                    return {
                        'success': False,
                        'error': 'Partner code already exists'
                    }
                
                partner.code = data.code.upper()
            
            # Handle API callback URL
            normalized_callback = None
            if data.api_callback_url:
                if not PartnerUtils.validate_api_callback_structure(data.api_callback_url):
                    return {
                        'success': False,
                        'error': 'Invalid API callback URL structure'
                    }
                normalized_callback = PartnerUtils.normalize_api_callback(data.api_callback_url)
            if data.service_key:
                partner.service_key = data.service_key
            # Update partner fields
            partner.name = data.name.strip()
            partner.is_active = data.is_active

            partner.group = target_group
            
            # Update expired_at if expired_days is provided and different from current
            if data.expired_days:
                new_expired_at = timezone.now() + timedelta(days=data.expired_days)
                partner.expired_days = data.expired_days
                partner.expired_at = new_expired_at
                partner.refresh_token = None
                partner.refresh_token_expires_at = None
            
            # Update API callback if provided
            if normalized_callback is not None:
                partner.api_callback_url = normalized_callback
            
            # Save partner
            update_fields = ['name', 'api_key', 'is_active', 'group', 'expired_at', 'refresh_token', 'refresh_token_expires_at', 'expired_days']
            if data.service_key:
                update_fields.append('service_key')
            if normalized_callback is not None:
                update_fields.append('api_callback_url')
            if data.code and data.code != partner.code:
                update_fields.append('code')
                
            partner.save(update_fields=update_fields)
            
            # Update proxy user if exists
            if partner.proxy_user:
                partner.proxy_user.is_active = data.is_active
                partner.proxy_user.save(update_fields=['is_active'])
            
            return {
                'success': True,
                'partner': partner
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update partner API key: {str(e)}'
            }
    @staticmethod
    def generate_refresh_token_for_partner(partner: Partner, request=None, user=None) -> Dict[str, Any]:
        """
        Generate refresh token for a partner
        
        Args:
            partner: Partner instance
            
        Returns:
            Dict: Token info with success status
        """
        try:
            # Generate secure refresh token with context information
            additional_context = {
                'partner_id': partner.id,
                'partner_code': partner.code,
                'action_type': 'generate_refresh_token',
                'group_id': partner.group.id if partner.group else None
            }
            new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
            refresh_token_expiry = PartnerUtils.generate_refresh_token_expiry()
            
            # Ensure uniqueness (very unlikely collision)
            while Partner.objects.filter(refresh_token=new_refresh_token).exists():
                new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
            
            # Update partner
            partner.refresh_token = new_refresh_token
            partner.refresh_token_expires_at = refresh_token_expiry
            partner.save(update_fields=['refresh_token', 'refresh_token_expires_at'])
            
            return {
                'success': True,
                'refresh_token': new_refresh_token,
                'expires_at': refresh_token_expiry
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    @transaction.atomic
    def refresh_partner_tokens(refresh_token: str, partner_id: int, request=None, user=None) -> Dict[str, Any]:
        """
        Refresh partner tokens using refresh token
        
        Args:
            refresh_token: Current refresh token
            partner_id: Partner ID
        Returns:
            Dict: New tokens or error info
        """
        try:
            # Validate refresh token format
            if not PartnerUtils.validate_refresh_token_format(refresh_token):
                return {
                    'success': False,
                    'error': 'Invalid refresh token format'
                }
            
            # Get partner by refresh token
            try:
                partner = Partner.objects.get(
                    refresh_token=refresh_token,
                    is_active=True,
                    id=partner_id
                )
            except Partner.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Invalid refresh token'
                }
            
            # Check if refresh token is expired
            if partner.refresh_token_expires_at and PartnerUtils.is_refresh_token_expired(partner.refresh_token_expires_at):
                return {
                    'success': False,
                    'error': 'Refresh token has expired'
                }
            
            # Generate new secure tokens with context information
            additional_context = {
                'partner_id': partner.id,
                'partner_code': partner.code,
                'action_type': 'refresh_partner_tokens',
                'group_id': partner.group.id if partner.group else None
            }
            new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
            new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
            new_refresh_token_expiry = PartnerUtils.generate_refresh_token_expiry()
            
            # Ensure uniqueness
            while Partner.objects.filter(api_key=new_api_key).exists():
                new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
            
            while Partner.objects.filter(refresh_token=new_refresh_token).exists():
                new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
            
            # Update partner with new tokens
            partner.api_key = new_api_key
            partner.refresh_token = new_refresh_token
            partner.refresh_token_expires_at = new_refresh_token_expiry
            partner.save(update_fields=['api_key', 'refresh_token', 'refresh_token_expires_at'])
            
            return {
                'success': True,
                'partner': partner,
                'api_key': new_api_key,
                'refresh_token': new_refresh_token,
                'refresh_token_expires_at': new_refresh_token_expiry
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_partner_api_callbacks(partner: Partner, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update API callback URLs for partner
        
        Args:
            partner: Partner instance
            callback_data: New callback data
            
        Returns:
            Dict: Update result
        """
        try:
            # Validate callback structure using utility
            if not PartnerUtils.validate_api_callback_structure(callback_data):
                return {
                    'success': False,
                    'error': 'Invalid API callback structure'
                }
            
            # Normalize and update callbacks using utility
            partner.api_callback_url = PartnerUtils.normalize_api_callback(callback_data)
            partner.save(update_fields=['api_callback_url'])
            
            return {
                'success': True,
                'api_callback_url': partner.api_callback_url
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def regenerate_partner_api_key(partner: Partner, request=None, user=None) -> Dict[str, Any]:
        """
        Regenerate API key for partner
        
        Args:
            partner: Partner instance
            
        Returns:
            Dict: New API key info
        """
        try:
            # Generate secure API key with context information
            additional_context = {
                'partner_id': partner.id,
                'partner_code': partner.code,
                'action_type': 'regenerate_api_key',
                'group_id': partner.group.id if partner.group else None
            }
            new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
            
            # Ensure uniqueness (very unlikely collision)
            while Partner.objects.filter(api_key=new_api_key).exists():
                new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
            
            # Store old key for logging
            old_api_key = partner.api_key
            
            # Update partner
            partner.api_key = new_api_key
            partner.save(update_fields=['api_key'])
            
            return {
                'success': True,
                'old_api_key': old_api_key,
                'new_api_key': new_api_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    @transaction.atomic
    def manage_refresh_token(partner: Partner, current_refresh_token: str = None, request=None, user=None) -> Dict[str, Any]:
        """
        Smart refresh token management with 3 cases:
        1. refreshed: Has valid refresh token - extend API time, keep API key
        2. regenerated: Has expired refresh token - create new API key and refresh token  
        3. generated: No refresh token - create refresh token, keep API key
        
        Args:
            partner: Partner instance
            current_refresh_token: Current refresh token (optional)
            
        Returns:
            Dict: Token info with success status and action taken
        """
        try:
            # Case 1: Has refresh token and it's still valid
            if (partner.refresh_token and 
                partner.refresh_token_expires_at and 
                not PartnerUtils.is_refresh_token_expired(partner.refresh_token_expires_at)):
                
                # If current_refresh_token provided, validate it matches
                if current_refresh_token and current_refresh_token != partner.refresh_token:
                    return {
                        'success': False,
                        'error': 'Provided refresh token does not match current token'
                    }
                
                # Action: refreshed - Keep API key, extend time, create new refresh token
                additional_context = {
                    'partner_id': partner.id,
                    'partner_code': partner.code,
                    'action_type': 'refresh_token',
                    'group_id': partner.group.id if partner.group else None
                }
                new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                new_refresh_expiry = PartnerUtils.generate_refresh_token_expiry(partner.expired_days if partner.expired_days else 30)
                
                # Ensure refresh token uniqueness
                while Partner.objects.filter(refresh_token=new_refresh_token).exists():
                    new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                
                # Extend API key expiration time based on expired_days
                if partner.expired_days:
                    new_expired_at = timezone.now() + timedelta(days=partner.expired_days if partner.expired_days else 30)
                    partner.expired_at = new_expired_at
                else:
                    new_expired_at = timezone.now() + timedelta(days=30)
                    partner.expired_at = new_expired_at
                    partner.expired_days = 30
                
                # Update partner - keep existing API key
                partner.refresh_token = new_refresh_token
                partner.refresh_token_expires_at = new_refresh_expiry
                partner.save(update_fields=['refresh_token', 'refresh_token_expires_at', 'expired_at', 'expired_days'])
                
                return {
                    'success': True,
                    'action': 'refreshed',
                    'api_key': partner.api_key,  # Keep existing API key
                    'refresh_token': new_refresh_token,
                    'refresh_token_expires_at': new_refresh_expiry,
                    'partner': partner,
                    'remaining_days': new_refresh_expiry - timezone.now()
                }
            
            # Case 2: Has refresh token but it's expired
            elif partner.refresh_token and partner.refresh_token_expires_at and PartnerUtils.is_refresh_token_expired(partner.refresh_token_expires_at):
                
                # Action: regenerated - Create new API key and refresh token
                additional_context = {
                    'partner_id': partner.id,
                    'partner_code': partner.code,
                    'action_type': 'regenerate_expired_tokens',
                    'group_id': partner.group.id if partner.group else None
                }
                new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
                new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                new_refresh_expiry = PartnerUtils.generate_refresh_token_expiry(partner.expired_days if partner.expired_days else 30)
                
                # Ensure uniqueness
                while Partner.objects.filter(api_key=new_api_key).exists():
                    new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
                    
                while Partner.objects.filter(refresh_token=new_refresh_token).exists():
                    new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                
                # Update API key expiration time based on expired_days
                if partner.expired_days:
                    new_expired_at = timezone.now() + timedelta(days=partner.expired_days if partner.expired_days else 30)
                    partner.expired_at = new_expired_at
                else:
                    new_expired_at = timezone.now() + timedelta(days=30)
                    partner.expired_at = new_expired_at
                    partner.expired_days = 30
                # Update partner with new tokens
                partner.api_key = new_api_key
                partner.refresh_token = new_refresh_token
                partner.refresh_token_expires_at = new_refresh_expiry
                partner.save(update_fields=['api_key', 'refresh_token', 'refresh_token_expires_at', 'expired_at', 'expired_days'])
                
                return {
                    'success': True,
                    'action': 'regenerated',
                    'api_key': new_api_key,
                    'refresh_token': new_refresh_token,
                    'refresh_token_expires_at': new_refresh_expiry,
                    'partner': partner,
                    'remaining_days': new_refresh_expiry - timezone.now()
                }
            
            # Case 3: No refresh token - first time generation
            else:
                # Check if API key is still valid or expired
                is_api_key_expired = partner.expired_at and PartnerUtils.is_refresh_token_expired(partner.expired_at)
                
                additional_context = {
                    'partner_id': partner.id,
                    'partner_code': partner.code,
                    'action_type': 'generate_first_refresh_token',
                    'group_id': partner.group.id if partner.group else None
                }
                
                # Generate refresh token for both sub-cases
                new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                refresh_token_expiry = PartnerUtils.generate_refresh_token_expiry(partner.expired_days if partner.expired_days else 30)
                
                # Ensure refresh token uniqueness
                while Partner.objects.filter(refresh_token=new_refresh_token).exists():
                    new_refresh_token = PartnerUtils.generate_secure_refresh_token(request, user, additional_context)
                
                # Case 3a: API key is still valid - keep existing API key, just create refresh token
                if not is_api_key_expired:
                    # Extend API key expiration if needed
                    if partner.expired_days:
                        new_expired_at = timezone.now() + timedelta(days=partner.expired_days)
                        partner.expired_at = new_expired_at
                    
                    # Update partner - keep existing API key
                    partner.refresh_token = new_refresh_token
                    partner.refresh_token_expires_at = refresh_token_expiry
                    partner.save(update_fields=['refresh_token', 'refresh_token_expires_at', 'expired_at'])
                    
                    return {
                        'success': True,
                        'action': 'generated',
                        'api_key': partner.api_key,  # Keep existing API key
                        'refresh_token': new_refresh_token,
                        'refresh_token_expires_at': refresh_token_expiry,
                        'partner': partner,
                        'remaining_days': refresh_token_expiry - timezone.now(),
                        'note': 'API key still valid - kept existing API key'
                    }
                
                # Case 3b: API key is expired - generate new API key AND refresh token
                else:
                    # Generate new API key for expired case
                    additional_context['action_type'] = 'generate_tokens_for_expired_api'
                    new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
                    
                    # Ensure API key uniqueness
                    while Partner.objects.filter(api_key=new_api_key).exists():
                        new_api_key = PartnerUtils.generate_api_key_with_prefix(request, user, additional_context)
                    
                    # Set new expiration time
                    expired_days = partner.expired_days if partner.expired_days else 30
                    new_expired_at = timezone.now() + timedelta(days=expired_days)
                    
                    # Update partner with new API key and refresh token
                    partner.api_key = new_api_key
                    partner.refresh_token = new_refresh_token
                    partner.refresh_token_expires_at = refresh_token_expiry
                    partner.expired_at = new_expired_at
                    partner.expired_days = expired_days
                    partner.save(update_fields=['api_key', 'refresh_token', 'refresh_token_expires_at', 'expired_at', 'expired_days'])
                    
                    return {
                        'success': True,
                        'action': 'generated',
                        'api_key': new_api_key,  # New API key for expired case
                        'refresh_token': new_refresh_token,
                        'refresh_token_expires_at': refresh_token_expiry,
                        'partner': partner,
                        'remaining_days': refresh_token_expiry - timezone.now(),
                        'note': 'API key was expired - generated new API key and refresh token'
                    }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to manage refresh token: {str(e)}'
            }