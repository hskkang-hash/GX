"""
Partner Authentication Middleware

This middleware handles partner authentication via API keys and sets the request.user
to the partner's proxy_user, allowing partners to use existing APIs without modifications.
"""

import logging
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from partner.models import Partner

logger = logging.getLogger(__name__)


class PartnerAuthMiddleware:
    """
    Middleware to authenticate partners via API key and set request.user to proxy_user
    
    This allows partners to access existing APIs using their API key while maintaining
    compatibility with the existing authentication and authorization system.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Detect and authenticate partner requests
        self._authenticate_partner(request)
        
        response = self.get_response(request)
        return response
    
    def _authenticate_partner(self, request):
        """
        Authenticate partner via API key and set request.user to proxy_user
        
        Args:
            request: Django request object
        """
        # Initialize partner-related attributes
        request.is_partner_request = False
        request.partner = None
        
        # Check for partner API key in headers
        api_key = self._extract_api_key(request)
        
        if not api_key:
            return  # No API key, continue as normal
        
        # Try to authenticate partner
        partner = self._get_partner_by_api_key(api_key)
        
        if not partner:
            logger.warning(f"Invalid API key attempted: {self._mask_api_key(api_key)}")
            return  # Invalid API key, continue as anonymous
        
        # Check if partner is active and not expired
        if not self._is_partner_valid(partner):
            logger.warning(f"Inactive or expired partner attempted access: {partner.code}")
            return  # Inactive/expired partner, continue as anonymous
        
        # Set request attributes for partner authentication
        request.is_partner_request = True
        request.partner = partner
        
        # Magic: Set request.user to partner's proxy_user
        if partner.proxy_user:
            request.user = partner.proxy_user
            self._update_partner_activity(partner)
            logger.info(f"Partner authenticated: {partner.code} -> {partner.proxy_user.username}")
        else:
            logger.error(f"Partner {partner.code} has no proxy_user assigned")
            # Continue as anonymous if no proxy_user
    
    def _extract_api_key(self, request):
        """
        Extract API key from request headers
        
        Args:
            request: Django request object
            
        Returns:
            str or None: API key if found, None otherwise
        """
        # Check X-API-Key header (preferred)
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return api_key.strip()
        
        # Check Authorization header with custom format
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('ApiKey '):
            return auth_header.split(' ', 1)[1].strip()
        
        # Check query parameter (less secure, only for testing)
        if hasattr(request, 'GET'):
            api_key = request.GET.get('api_key')
            if api_key:
                logger.warning("API key passed via query parameter - not recommended for production")
                return api_key.strip()
        
        return None
    
    def _get_partner_by_api_key(self, api_key):
        """
        Get partner by API key
        
        Args:
            api_key: API key to lookup
            
        Returns:
            Partner or None: Partner object if found, None otherwise
        """
        try:
            partner = Partner.objects.select_related(
                'proxy_user', 
                'proxy_user__userprofilelink',
                'proxy_user__userprofilelink__group'
            ).get(
                api_key=api_key,
                is_active=True
            )
            return partner
        except Partner.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching partner by API key: {e}")
            return None
    
    def _is_partner_valid(self, partner):
        """
        Check if partner is valid for authentication
        
        Args:
            partner: Partner object
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if partner is active
        if not partner.is_active:
            return False
        
        # Check if partner has expired
        if partner.expired_at and timezone.now() > partner.expired_at:
            return False
        
        # Check if proxy user is active
        if not partner.proxy_user or not partner.proxy_user.is_active:
            return False
        
        return True
    
    def _update_partner_activity(self, partner):
        """
        Update partner's last activity
        
        Args:
            partner: Partner object
        """
        try:
            # Update proxy user's last login
            partner.proxy_user.last_login = timezone.now()
            partner.proxy_user.save(update_fields=['last_login'])
        except Exception as e:
            logger.error(f"Error updating partner activity: {e}")
    
    def _mask_api_key(self, api_key):
        """
        Mask API key for logging
        
        Args:
            api_key: API key to mask
            
        Returns:
            str: Masked API key
        """
        if not api_key or len(api_key) < 8:
            return '***'
        
        return f"{api_key[:4]}***{api_key[-4:]}"


class PartnerAuthenticationError(Exception):
    """Exception raised for partner authentication errors"""
    pass


class PartnerPermissionError(Exception):
    """Exception raised for partner permission errors"""
    pass
